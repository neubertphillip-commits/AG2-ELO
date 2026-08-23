"""
Hochrechnung der laufenden Saison auf einen vollen Spielplan.

Ansatz: alle kumulativen Zaehl-Groessen (Yards, TDs, Sacks, Tackles,
Games Started, FG-/XP-Versuche, Punt-Yards, ...) werden je Team mit dem
Pace-Faktor  (geplante Saison-Spiele / bisher gespielte Spiele)  hochskaliert,
danach laeuft exakt dieselbe av_engine-Formel wie fuer eine abgeschlossene
Saison. Reine Rate-Groessen (Yards/Attempt, Punkte/Drive, PAA) aendern sich
dabei nicht, weil Zaehler und Nenner gleichermassen skaliert werden - nur die
Team-Pools und die Spielanteile (Games Started, Playing-Time-Shares) werden
dadurch realistischer fuer eine laufende Saison.
"""

from __future__ import annotations

import pandas as pd

from . import aggregate as agg
from . import av_engine as eng
from . import data_source as ds
from .config import AVConfig
from .pipeline import _id_crosswalk, _position_refinement, _roster_positions_all

_COUNT_COLS_BY_TABLE = {
    "team_off": ["rush_td", "pass_td", "fg_made", "fga", "punts", "interceptions_thrown", "fumbles_lost", "turnovers"],
    "team_def": ["rush_td_allowed", "pass_td_allowed", "fg_allowed", "fga_faced", "punts_forced",
                 "interceptions_forced", "fumbles_forced_lost", "turnovers_forced"],
    "games": ["games_played", "games_started"],
    "rushers": ["carries", "rushing_yards"],
    "passers": ["attempts", "passing_yards", "passing_tds", "interceptions"],
    "receivers": ["receptions", "receiving_yards"],
    "defense": ["sacks", "fumble_recoveries", "interceptions", "defensive_tds", "tackles"],
    "kicking": ["xpm", "xpa", "fgm1", "fga1", "fgm2", "fga2", "fgm3", "fga3", "fgm4", "fga4", "fgm5", "fga5",
                "fgm_u", "fga_u"],
    "punting": ["punt", "punt_blocked", "punt_yds"],
    "returns": ["return_tds"],
}


def _pace_factor(team_games_now: pd.DataFrame, full_games: int) -> dict[str, float]:
    return {
        row.team: (full_games / row.games if row.games else 1.0)
        for row in team_games_now.itertuples()
    }


def _scale(df: pd.DataFrame, cols: list[str], pace: dict[str, float]) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    factor = out["team"].map(pace).fillna(1.0)
    for c in cols:
        if c in out.columns:
            out[c] = out[c] * factor
    return out


def build_projected_season_av(cfg: AVConfig, season: int, through_week: int) -> pd.DataFrame:
    """AV-Rangliste, hochgerechnet auf eine volle Saison, basierend auf dem
    Tempo (Pace) durch Woche `through_week`."""
    pbp_special = ds.get_pbp_special([season])
    weekly = ds.get_weekly_data([season])
    weekly_def = ds.get_weekly_def([season])
    snaps = ds.get_snap_counts([season])
    schedules = ds.get_schedules([season])

    pfr_to_gsis = _id_crosswalk()
    roster_positions = _roster_positions_all()
    pos_refine = _position_refinement(season)

    team_games_now = agg.team_games_played(schedules, season, through_week)
    team_games_full = agg.team_games_played(schedules, season, through_week=None)
    pace = _pace_factor(team_games_now, cfg.full_season_games)
    # Fuer die av_engine-Formeln (die selbst mit team_games arbeiten, z.B.
    # Kicker/Punter) wird bereits der volle Saison-Spielplan uebergeben.
    team_games_for_engine = team_games_full.rename(columns={"games": "games"})

    team_off_in = _scale(agg.team_offense_inputs(weekly, pbp_special, season, through_week), _COUNT_COLS_BY_TABLE["team_off"], pace)
    team_def_in = _scale(agg.team_defense_inputs(weekly, pbp_special, season, through_week), _COUNT_COLS_BY_TABLE["team_def"], pace)
    team_off_pts = eng.team_offense_points(cfg, team_off_in)
    team_def_pts = eng.team_defense_points(cfg, team_def_in)

    full_games_map = team_games_full.set_index("team")["games"].to_dict()

    def _scaled_games(pfr_to_gsis_arg):
        raw = agg.games_played_started(snaps, season, through_week, cfg.games_started_snap_threshold,
                                        pfr_to_gsis_arg, position_refinement=pos_refine)
        scaled = _scale(raw, _COUNT_COLS_BY_TABLE["games"], pace)
        cap = scaled["team"].map(full_games_map).fillna(cfg.full_season_games)
        scaled["games_started"] = scaled["games_started"].clip(upper=cap)
        scaled["games_played"] = scaled["games_played"].clip(upper=cap)
        return scaled

    oline_games_scaled = _scaled_games(None)
    defense_games_scaled = _scaled_games(pfr_to_gsis)

    oline_pool_by_team = {t: cfg.o_line_pool_share * v for t, v in team_off_pts.items()}
    oline_av = eng.compute_oline_av(cfg, oline_games_scaled, team_off_pts, all_pro=None)

    offense_stats_raw = agg.player_offense_stats(weekly, season, through_week)
    offense_stats = {
        "rushers": _scale(offense_stats_raw["rushers"], _COUNT_COLS_BY_TABLE["rushers"], pace),
        "passers": _scale(offense_stats_raw["passers"], _COUNT_COLS_BY_TABLE["passers"], pace),
        "receivers": _scale(offense_stats_raw["receivers"], _COUNT_COLS_BY_TABLE["receivers"], pace),
    }
    if not offense_stats["passers"].empty:
        offense_stats["passers"]["ay_a"] = (
            offense_stats["passers"]["passing_yards"]
            + 20 * offense_stats["passers"]["passing_tds"]
            - 45 * offense_stats["passers"]["interceptions"]
        ) / offense_stats["passers"]["attempts"].replace(0, pd.NA)

    lg_rb_ypc = agg.league_rb_ypc(offense_stats["rushers"], roster_positions)
    lg_ay_a = agg.league_ay_a(offense_stats["passers"], cfg.qb_min_attempts_for_efficiency)
    skill_av = eng.compute_skill_av(cfg, offense_stats, team_off_pts, oline_pool_by_team, roster_positions, lg_rb_ypc, lg_ay_a)

    defense_stats = _scale(
        agg.player_defense_stats(weekly_def, pbp_special, season, pfr_to_gsis, through_week),
        _COUNT_COLS_BY_TABLE["defense"], pace,
    )
    defense_av = eng.compute_defense_av(cfg, season, defense_games_scaled, defense_stats, team_def_pts, all_pro=None)

    kicking = _scale(agg.player_kicking_stats(pbp_special, season, through_week), _COUNT_COLS_BY_TABLE["kicking"], pace)
    punting = _scale(agg.player_punting_stats(pbp_special, season, through_week), _COUNT_COLS_BY_TABLE["punting"], pace)
    returns = _scale(agg.player_return_tds(pbp_special, season, through_week), _COUNT_COLS_BY_TABLE["returns"], pace)

    kicker_av = eng.compute_kicker_av(cfg, kicking, team_games_for_engine)
    punter_av = eng.compute_punter_av(cfg, punting, team_games_for_engine)
    return_av = eng.compute_return_av(cfg, returns)

    return eng.combine_season_av(oline_av, skill_av, defense_av, kicker_av, punter_av, return_av)
