"""
Implementierung der PFR-Approximate-Value-Formeln. Alle "magischen" Zahlen
kommen aus config.AVConfig - nichts ist hier hart codiert, damit sich jede
Konstante ueber die UI/Config anpassen laesst.

Jede compute_*-Funktion nimmt vor-aggregierte Tabellen (siehe aggregate.py)
und gibt eine DataFrame mit Spalten [player_id, player_name, team, av, component]
zurueck. compute_season_av() fasst alles zu einer Gesamt-Rangliste zusammen.
"""

from __future__ import annotations

import pandas as pd

from .aggregate import (
    DL_POSITIONS,
    FRONT_SEVEN_POSITIONS,
    OLINE_POSITIONS,
    SECONDARY_POSITIONS,
    points_per_drive,
)
from .config import AVConfig


def _weighted_league_avg_offense(team_offense: pd.DataFrame) -> float:
    tot_num = (7 * (team_offense["rush_td"] + team_offense["pass_td"]) + 3 * team_offense["fg_made"]).sum()
    tot_den = (team_offense["rush_td"] + team_offense["pass_td"] + team_offense["turnovers"]
               + team_offense["punts"] + team_offense["fga"]).sum()
    return tot_num / tot_den if tot_den else 0.0


def _weighted_league_avg_defense(team_defense: pd.DataFrame) -> float:
    tot_num = (7 * (team_defense["rush_td_allowed"] + team_defense["pass_td_allowed"])
               + 3 * team_defense["fg_allowed"]).sum()
    tot_den = (team_defense["rush_td_allowed"] + team_defense["pass_td_allowed"] + team_defense["turnovers_forced"]
               + team_defense["punts_forced"] + team_defense["fga_faced"]).sum()
    return tot_num / tot_den if tot_den else 0.0


def team_offense_points(cfg: AVConfig, team_offense: pd.DataFrame) -> pd.Series:
    lg_avg = _weighted_league_avg_offense(team_offense)
    pts = team_offense.apply(
        lambda r: points_per_drive(r.rush_td, r.pass_td, r.fg_made, r.turnovers, r.punts, r.fga), axis=1
    )
    if lg_avg == 0:
        return pd.Series(0.0, index=team_offense["team"])
    return pd.Series((cfg.offense_pool_scale * pts / lg_avg).values, index=team_offense["team"])


def team_defense_points(cfg: AVConfig, team_defense: pd.DataFrame) -> pd.Series:
    lg_avg = _weighted_league_avg_defense(team_defense)
    pts_allowed = team_defense.apply(
        lambda r: points_per_drive(r.rush_td_allowed, r.pass_td_allowed, r.fg_allowed,
                                    r.turnovers_forced, r.punts_forced, r.fga_faced), axis=1
    )
    m = pts_allowed / lg_avg if lg_avg else pts_allowed * 0.0
    m = m.replace(0, 1e-9)  # Division durch 0 vermeiden (Team ohne erlaubte Punkte)
    result = cfg.offense_pool_scale * (1 + 2 * m - m ** 2) / (2 * m)
    return pd.Series(result.values, index=team_defense["team"])


# ---------------------------------------------------------------------------
# Offensive Line
# ---------------------------------------------------------------------------

def compute_oline_av(cfg: AVConfig, oline_games: pd.DataFrame, team_off_pts: pd.Series,
                      all_pro: dict | None = None) -> pd.DataFrame:
    all_pro = all_pro or {}
    df = oline_games[oline_games["position"].isin(OLINE_POSITIONS)].copy()
    if df.empty:
        return pd.DataFrame(columns=["player_id", "player_name", "team", "av", "component"])

    pos_mult = {
        "T": cfg.pos_multiplier_tackle,
        "G": cfg.pos_multiplier_guard_center,
        "C": cfg.pos_multiplier_guard_center,
        "FB": cfg.pos_multiplier_fullback,
        "TE": cfg.pos_multiplier_tight_end,
        "OL": cfg.pos_multiplier_guard_center,  # generischer Fallback, siehe aggregate.build_position_refinement
    }
    ap_mult = {"1st": cfg.all_pro_multiplier_1st, "2nd": cfg.all_pro_multiplier_2nd, "pb": cfg.all_pro_multiplier_pro_bowl}

    def indiv_points(row):
        base = row.games_played + cfg.games_started_weight_oline * row.games_started * pos_mult[row.position]
        mult = 1.0
        if cfg.enable_all_pro_bonus and row.position in ("T", "G", "C"):
            level = all_pro.get(row.player_id)
            mult = ap_mult.get(level, 1.0)
        return base * mult

    df["individual_points"] = df.apply(indiv_points, axis=1)
    df["team_pool"] = df["team"].map(lambda t: cfg.o_line_pool_share * team_off_pts.get(t, 0.0))
    team_sum = df.groupby("team")["individual_points"].transform("sum").replace(0, pd.NA)
    df["av"] = (df["individual_points"] / team_sum * df["team_pool"]).fillna(0.0)

    out = df.rename(columns={"player": "player_name"})
    out["component"] = "o_line"
    return out[["player_id", "player_name", "team", "av", "component"]]


# ---------------------------------------------------------------------------
# Skill Positions (Rusher / Passer / Receiver)
# ---------------------------------------------------------------------------

def compute_skill_av(cfg: AVConfig, offense_stats: dict[str, pd.DataFrame], team_off_pts: pd.Series,
                      oline_team_pool: dict[str, float], roster_positions: dict[str, str],
                      lg_rb_ypc: float, lg_ay_a: float) -> pd.DataFrame:
    rushers, passers, receivers = offense_stats["rushers"], offense_stats["passers"], offense_stats["receivers"]
    rows = []

    for team, team_off in team_off_pts.items():
        team_rush = rushers[rushers["team"] == team]
        team_pass = passers[passers["team"] == team]
        team_recv = receivers[receivers["team"] == team]

        team_rush_yds = team_rush["rushing_yards"].sum()
        team_pass_yds = team_pass["passing_yards"].sum()
        team_recv_yds = team_recv["receiving_yards"].sum()
        team_total_yds = team_rush_yds + team_pass_yds

        o_line_pool = oline_team_pool.get(team, 0.0)
        skill_pool = team_off - o_line_pool

        ratio = (team_rush_yds / team_total_yds) if team_total_yds else 0.0
        rusher_pool = skill_pool * cfg.rusher_pool_base_share * (ratio / cfg.rusher_pool_reference_ratio if cfg.rusher_pool_reference_ratio else 0)
        remainder = skill_pool - rusher_pool
        passer_pool = remainder * cfg.passer_share_of_remainder
        receiver_pool = remainder * cfg.receiver_share_of_remainder

        for _, r in team_rush.iterrows():
            av = (r.rushing_yards / team_rush_yds * rusher_pool) if team_rush_yds else 0.0
            if r.carries >= cfg.rb_min_carries_for_efficiency and roster_positions.get(r.player_id) == "RB":
                ypc = r.rushing_yards / r.carries if r.carries else 0.0
                diff = ypc - lg_rb_ypc
                av += (cfg.rb_efficiency_bonus_mult if diff >= 0 else cfg.rb_efficiency_penalty_mult) * diff
            rows.append({"player_id": r.player_id, "player_name": r.player_name, "team": team, "av": av, "component": "rusher"})

        for _, r in team_pass.iterrows():
            av = (r.passing_yards / team_pass_yds * passer_pool) if team_pass_yds else 0.0
            if r.attempts >= cfg.qb_min_attempts_for_efficiency:
                diff = r.ay_a - lg_ay_a
                av += (cfg.qb_efficiency_bonus_mult if diff >= 0 else cfg.qb_efficiency_penalty_mult) * diff
            rows.append({"player_id": r.player_id, "player_name": r.player_name, "team": team, "av": av, "component": "passer"})

        for _, r in team_recv.iterrows():
            av = (r.receiving_yards / team_recv_yds * receiver_pool) if team_recv_yds else 0.0
            rows.append({"player_id": r.player_id, "player_name": r.player_name, "team": team, "av": av, "component": "receiver"})

    return pd.DataFrame(rows, columns=["player_id", "player_name", "team", "av", "component"])


# ---------------------------------------------------------------------------
# Defense
# ---------------------------------------------------------------------------

def compute_defense_av(cfg: AVConfig, season: int, defense_games: pd.DataFrame, defense_stats: pd.DataFrame,
                        team_def_pts: pd.Series, all_pro: dict | None = None) -> pd.DataFrame:
    all_pro = all_pro or {}
    df = defense_games[defense_games["position"].isin(FRONT_SEVEN_POSITIONS | SECONDARY_POSITIONS)].copy()
    if df.empty:
        return pd.DataFrame(columns=["player_id", "player_name", "team", "av", "component"])

    df = df.merge(defense_stats, on="player_id", how="left", suffixes=("", "_stat"))
    for c in ["sacks", "fumble_recoveries", "interceptions", "defensive_tds", "solo_tackles", "assist_tackles"]:
        df[c] = df[c].fillna(0.0)

    ap_level = {"1st": cfg.all_pro_level_1st, "2nd": cfg.all_pro_level_2nd, "pb": cfg.all_pro_level_pro_bowl}
    year_mult = (cfg.year_constant_post_sack_era if season >= cfg.sack_era_start_year else cfg.year_constant_pre_sack_era)

    def tkl_const(pos):
        if season < cfg.tackle_constant_start_year:
            return 0.0
        if pos in DL_POSITIONS:
            return cfg.tackle_constant_dl
        if pos == "LB":
            return cfg.tackle_constant_lb
        return cfg.tackle_constant_db

    def indiv_points(row, team_games):
        tackles = row.solo_tackles + cfg.assist_tackle_weight * row.assist_tackles
        base = (row.games_played + cfg.games_started_weight_defense * row.games_started
                + cfg.sack_weight * row.sacks
                + cfg.fumble_recovery_weight * row.fumble_recoveries
                + cfg.interception_weight * row.interceptions
                + cfg.defensive_td_weight * row.defensive_tds
                + tkl_const(row.position) * tackles)
        bonus = 0.0
        if cfg.enable_all_pro_bonus:
            level = all_pro.get(row.player_id)
            if level:
                games = team_games.get(row.team, cfg.full_season_games)
                bonus = ap_level.get(level, 0.0) * year_mult * (games / cfg.full_season_games)
        return base + bonus

    team_games = df.groupby("team")["games_played"].max().to_dict()
    df["individual_points"] = df.apply(lambda r: indiv_points(r, team_games), axis=1)
    df["group"] = df["position"].map(lambda p: "front_seven" if p in FRONT_SEVEN_POSITIONS else "secondary")

    def pool_for(team, group):
        share = cfg.front_seven_share if group == "front_seven" else cfg.secondary_share
        return share * team_def_pts.get(team, 0.0)

    df["team_pool"] = df.apply(lambda r: pool_for(r.team, r.group), axis=1)
    grp_sum = df.groupby(["team", "group"])["individual_points"].transform("sum").replace(0, pd.NA)
    df["av"] = (df["individual_points"] / grp_sum * df["team_pool"]).fillna(0.0)

    out = df.copy()
    out["player_name"] = out["player_name"].fillna(out["player"])
    out["component"] = "defense"
    return out[["player_id", "player_name", "team", "av", "component"]]


# ---------------------------------------------------------------------------
# Special Teams
# ---------------------------------------------------------------------------

def compute_kicker_av(cfg: AVConfig, kicking: pd.DataFrame, team_games: pd.DataFrame) -> pd.DataFrame:
    if kicking.empty:
        return pd.DataFrame(columns=["player_id", "player_name", "team", "av", "component"])
    df = kicking.copy()
    bands = ["1", "2", "3", "4", "5"]

    def lg_pct(made_col, att_col):
        m, a = df[made_col].sum(), df[att_col].sum()
        return m / a if a else 0.0

    lg_xp_pct = lg_pct("xpm", "xpa")
    lg_fg_pct = {b: lg_pct(f"fgm{b}", f"fga{b}") for b in bands}
    lg_fg_pct_u = lg_pct("fgm_u", "fga_u")

    def paa(row):
        total = row.xpm - row.xpa * lg_xp_pct
        for b in bands:
            total += 3 * (row[f"fgm{b}"] - row[f"fga{b}"] * lg_fg_pct[b])
        total += 3 * (row["fgm_u"] - row["fga_u"] * lg_fg_pct_u)
        return total

    df["paa_total"] = df.apply(paa, axis=1)
    df["k_playing_time"] = df["xpa"] + cfg.kicker_playing_time_fga_weight * (
        df[[f"fga{b}" for b in bands]].sum(axis=1) + df["fga_u"]
    )
    team_pt = df.groupby("team")["k_playing_time"].transform("sum").replace(0, pd.NA)
    df["pct_team_playing_time"] = (df["k_playing_time"] / team_pt).fillna(0.0)
    tg = df["team"].map(lambda t: team_games.set_index("team")["games"].get(t, cfg.full_season_games))
    df["avg_av"] = (cfg.kicker_baseline_av_per_16 / cfg.full_season_games) * tg * df["pct_team_playing_time"]
    df["raw_av"] = df["avg_av"] + df["paa_total"] / cfg.kicker_paa_divisor
    df["av"] = cfg.full_season_games * (df["raw_av"] / tg.replace(0, pd.NA)).fillna(0.0)

    df["component"] = "kicker"
    return df[["player_id", "player_name", "team", "av", "component"]]


def compute_punter_av(cfg: AVConfig, punting: pd.DataFrame, team_games: pd.DataFrame) -> pd.DataFrame:
    if punting.empty:
        return pd.DataFrame(columns=["player_id", "player_name", "team", "av", "component"])
    df = punting.copy()
    df["adj_punt_ypa"] = (df["punt_yds"] - cfg.punt_block_penalty_yards * df["punt_blocked"]) / (
        df["punt"] + df["punt_blocked"]
    ).replace(0, pd.NA)

    weight = df["punt"] + df["punt_blocked"]
    lg_adj_punt_ypa = (df["adj_punt_ypa"] * weight).sum() / weight.sum() if weight.sum() else 0.0

    df["adj_punt_yds_above_avg"] = weight * (df["adj_punt_ypa"] - lg_adj_punt_ypa)

    team_pt = df.groupby("team")[["punt", "punt_blocked"]].transform("sum")
    df["pct_team_playing_time"] = (weight / (team_pt["punt"] + team_pt["punt_blocked"]).replace(0, pd.NA)).fillna(0.0)

    tg = df["team"].map(lambda t: team_games.set_index("team")["games"].get(t, cfg.full_season_games))
    df["avg_av"] = (cfg.punter_baseline_av_per_16 / cfg.full_season_games) * tg * df["pct_team_playing_time"]
    df["raw_av"] = df["avg_av"] + df["adj_punt_yds_above_avg"].fillna(0.0) / cfg.punter_yards_divisor
    df["av"] = cfg.full_season_games * (df["raw_av"] / tg.replace(0, pd.NA)).fillna(0.0)

    df["component"] = "punter"
    return df[["player_id", "player_name", "team", "av", "component"]]


def compute_return_av(cfg: AVConfig, returns: pd.DataFrame) -> pd.DataFrame:
    if returns.empty:
        return pd.DataFrame(columns=["player_id", "player_name", "team", "av", "component"])
    df = returns.copy()
    df["av"] = df["return_tds"] * cfg.return_td_av
    df["component"] = "return"
    return df[["player_id", "player_name", "team", "av", "component"]]


# ---------------------------------------------------------------------------
# Orchestrierung
# ---------------------------------------------------------------------------

def combine_season_av(*component_tables: pd.DataFrame) -> pd.DataFrame:
    """player_id + team ist der eindeutige Schluessel - NICHT player_name
    mit einbeziehen: pbp liefert fuer dieselbe Person je nach Play-Typ-Spalte
    (rusher_player_name vs. receiver_player_name etc.) manchmal leicht
    unterschiedlich abgekuerzte Namen (z.B. 'T.Dell' vs. 'N.Dell'), was sonst
    faelschlich zwei Zeilen fuer denselben Spieler erzeugen wuerde."""
    all_rows = pd.concat([t for t in component_tables if not t.empty], ignore_index=True)
    all_rows = all_rows.sort_values(
        "player_name", key=lambda s: s.str.len(), ascending=False
    )
    names = all_rows.groupby(["player_id", "team"])["player_name"].first()
    totals = all_rows.groupby(["player_id", "team"], as_index=False)["av"].sum()
    totals["player_name"] = totals.apply(lambda r: names[(r.player_id, r.team)], axis=1)
    totals = totals[["player_id", "player_name", "team", "av"]]
    return totals.sort_values("av", ascending=False).reset_index(drop=True)
