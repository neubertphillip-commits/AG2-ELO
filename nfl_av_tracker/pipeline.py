"""
Verbindet data_source (Rohdaten) -> aggregate (Boxscore-Tabellen) ->
av_engine (PFR-Formeln) zu einer einzigen Funktion pro Saison/Wochenstand.

Fuer abgeschlossene Saisons (through_week=None UND die Saison ist laut
Spielplan fertig) wird das Ergebnis in der SQLite-DB gecached (siehe db.py):
gleiche Config -> reiner DB-Read statt Neuberechnung. Fuer die laufende
Saison oder einen expliziten Wochenstand (through_week gesetzt) wird immer
frisch gerechnet, weil sich diese Werte per Definition noch aendern.
"""

from __future__ import annotations

from functools import lru_cache

import pandas as pd

from . import aggregate as agg
from . import av_engine as eng
from . import data_source as ds
from . import db
from .config import AVConfig


@lru_cache(maxsize=1)
def _id_crosswalk() -> dict[str, str]:
    ids = db.load_ids()
    ids = ids.dropna(subset=["pfr_id", "gsis_id"])
    return dict(zip(ids["pfr_id"], ids["gsis_id"]))


@lru_cache(maxsize=1)
def _roster_positions_all() -> dict[str, str]:
    ids = db.load_ids()
    ids = ids.dropna(subset=["gsis_id", "position"])
    return dict(zip(ids["gsis_id"], ids["position"]))


@lru_cache(maxsize=None)
def _position_refinement(season: int) -> dict[str, str]:
    rosters = ds.get_seasonal_rosters([season])
    return agg.build_position_refinement(rosters)


def _compute_season_av(cfg: AVConfig, season: int, through_week: int | None,
                        all_pro: dict | None) -> pd.DataFrame:
    """Rechnet die AV-Formeln fuer eine Saison/einen Wochenstand tatsaechlich
    durch (keine Cache-Logik hier - siehe build_season_av)."""
    pbp = ds.get_pbp_data([season])
    snaps = ds.get_snap_counts([season])
    schedules = ds.get_schedules([season])

    pfr_to_gsis = _id_crosswalk()
    roster_positions = _roster_positions_all()
    pos_refine = _position_refinement(season)

    team_off_in = agg.team_offense_inputs(pbp, season, through_week)
    team_def_in = agg.team_defense_inputs(pbp, season, through_week)
    team_off_pts = eng.team_offense_points(cfg, team_off_in)
    team_def_pts = eng.team_defense_points(cfg, team_def_in)

    oline_games = agg.games_played_started(snaps, season, through_week, cfg.games_started_snap_threshold,
                                            position_refinement=pos_refine)
    defense_games = agg.games_played_started(snaps, season, through_week, cfg.games_started_snap_threshold,
                                              pfr_to_gsis, position_refinement=pos_refine)

    oline_pool_by_team = {t: cfg.o_line_pool_share * v for t, v in team_off_pts.items()}
    oline_av = eng.compute_oline_av(cfg, oline_games, team_off_pts, all_pro)

    offense_stats = agg.player_offense_stats(pbp, season, through_week)
    lg_rb_ypc = agg.league_rb_ypc(offense_stats["rushers"], roster_positions)
    lg_ay_a = agg.league_ay_a(offense_stats["passers"], cfg.qb_min_attempts_for_efficiency)
    skill_av = eng.compute_skill_av(cfg, offense_stats, team_off_pts, oline_pool_by_team, roster_positions, lg_rb_ypc, lg_ay_a)

    defense_stats = agg.player_defense_stats(pbp, season, through_week)
    defense_av = eng.compute_defense_av(cfg, season, defense_games, defense_stats, team_def_pts, all_pro)

    team_games = agg.team_games_played(schedules, season, through_week)
    kicking = agg.player_kicking_stats(pbp, season, through_week)
    punting = agg.player_punting_stats(pbp, season, through_week)
    returns = agg.player_return_tds(pbp, season, through_week)

    kicker_av = eng.compute_kicker_av(cfg, kicking, team_games)
    punter_av = eng.compute_punter_av(cfg, punting, team_games)
    return_av = eng.compute_return_av(cfg, returns)

    return eng.combine_season_av(oline_av, skill_av, defense_av, kicker_av, punter_av, return_av)


def build_season_av(cfg: AVConfig, season: int, through_week: int | None = None,
                     all_pro: dict | None = None, force_recompute: bool = False) -> pd.DataFrame:
    """Vollstaendige AV-Rangliste fuer eine Saison (optional bis inkl. through_week).

    Abgeschlossene Saisons (through_week=None, Spielplan komplett) werden
    unter dem aktuellen Config-Hash aus der DB gelesen, falls schon einmal
    berechnet - sonst berechnet und fuer naechste Male gespeichert. Ein
    Wochenstand (through_week gesetzt) wird nie gecached, da er sich noch
    aendert.
    """
    use_cache = through_week is None and all_pro is None and not force_recompute
    chash = db.config_hash(cfg) if use_cache else None

    if use_cache:
        schedules = ds.get_schedules([season])
        if db.is_season_final(schedules, season):
            cached = db.get_cached_av(chash, season)
            if cached is not None:
                return cached

    result = _compute_season_av(cfg, season, through_week, all_pro)

    if use_cache:
        schedules = ds.get_schedules([season])
        if db.is_season_final(schedules, season):
            db.store_av(chash, season, result)

    return result


def build_multi_season_av(cfg: AVConfig, seasons: list[int]) -> pd.DataFrame:
    """AV je Spieler UND Saison, fuer Career-/Weighted-Career-Berechnungen."""
    frames = []
    for s in seasons:
        df = build_season_av(cfg, s)
        df["season"] = s
        frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(
        columns=["player_id", "player_name", "team", "av", "season"]
    )


def warm_historical_cache(cfg: AVConfig, seasons: list[int], force: bool = False) -> pd.DataFrame:
    """Rechnet & speichert AV fuer mehrere vergangene Saisons in einem Rutsch
    (fuer den 'einmal alles laden'-Anwendungsfall). Ueberspringt Saisons, die
    unter diesem Config-Hash schon gecached sind, ausser force=True."""
    chash = db.config_hash(cfg)
    rows = []
    for s in seasons:
        schedules = ds.get_schedules([s])
        if not db.is_season_final(schedules, s):
            rows.append({"season": s, "status": "uebersprungen (noch nicht abgeschlossen)"})
            continue
        if not force and db.get_cached_av(chash, s) is not None:
            rows.append({"season": s, "status": "bereits gecached"})
            continue
        result = _compute_season_av(cfg, s, None, None)
        db.store_av(chash, s, result)
        rows.append({"season": s, "status": f"berechnet ({len(result)} Spieler)"})
    return pd.DataFrame(rows)
