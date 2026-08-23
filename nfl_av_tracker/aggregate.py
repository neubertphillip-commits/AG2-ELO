"""
Baut aus den rohen nflverse-Tabellen (play-by-play, snap counts, rosters) die
Aggregat-Tabellen, die av_engine.py fuer die PFR-AV-Formeln braucht.

Jede Funktion kann optional auf einen Wochenbereich (through_week) begrenzt
werden - das ist die Grundlage fuer den "laufende Saison"-Tracker und die
Hochrechnung (projection.py).
"""

from __future__ import annotations

import pandas as pd

OLINE_POSITIONS = {"T", "G", "C", "FB", "TE", "OL"}  # "OL" = generischer Fallback (siehe refine_positions)
FRONT_SEVEN_POSITIONS = {"DE", "DT", "NT", "LB", "DL"}  # "DL" = generischer Fallback
SECONDARY_POSITIONS = {"CB", "FS", "SS", "DB"}  # "DB" ist bereits der generische Fallback
DL_POSITIONS = {"DE", "DT", "NT", "DL"}
_SPECIFIC_OLINE = {"T", "G", "C"}
_SPECIFIC_DL = {"DE", "DT", "NT"}


def _filter_week(df: pd.DataFrame, season: int, through_week: int | None) -> pd.DataFrame:
    out = df[df["season"] == season]
    if through_week is not None:
        out = out[out["week"] <= through_week]
    return out


# ---------------------------------------------------------------------------
# Team-Pools (Offense/Defense-Punkte pro Drive, PFR-Definition)
# ---------------------------------------------------------------------------

def team_offense_inputs(pbp: pd.DataFrame, season: int, through_week: int | None = None) -> pd.DataFrame:
    """Team-level Zaehler fuer offense-points-per-drive, gruppiert nach posteam."""
    df = _filter_week(pbp, season, through_week).copy()
    df = df[df["posteam"].notna()]
    df["_fg_made"] = (df["field_goal_result"] == "made").astype(int)

    g = df.groupby("posteam")
    out = pd.DataFrame({
        "rush_td": g["rush_touchdown"].sum(),
        "pass_td": g["pass_touchdown"].sum(),
        "fg_made": g["_fg_made"].sum(),
        "fga": g["field_goal_attempt"].sum(),
        "punts": g["punt_attempt"].sum(),
        "interceptions_thrown": g["interception"].sum(),
        "fumbles_lost": g["fumble_lost"].sum(),
    }).fillna(0)
    out["turnovers"] = out["interceptions_thrown"] + out["fumbles_lost"]
    out.index.name = "team"
    return out.reset_index()


def team_defense_inputs(pbp: pd.DataFrame, season: int, through_week: int | None = None) -> pd.DataFrame:
    """Dieselben Zaehler, aber aus Sicht der Defense (was das Team zulaesst),
    gruppiert nach defteam."""
    df = _filter_week(pbp, season, through_week).copy()
    df = df[df["defteam"].notna()]
    df["_fg_made"] = (df["field_goal_result"] == "made").astype(int)

    g = df.groupby("defteam")
    out = pd.DataFrame({
        "rush_td_allowed": g["rush_touchdown"].sum(),
        "pass_td_allowed": g["pass_touchdown"].sum(),
        "fg_allowed": g["_fg_made"].sum(),
        "fga_faced": g["field_goal_attempt"].sum(),
        "punts_forced": g["punt_attempt"].sum(),
        "interceptions_forced": g["interception"].sum(),
        "fumbles_forced_lost": g["fumble_lost"].sum(),
    }).fillna(0)
    out["turnovers_forced"] = out["interceptions_forced"] + out["fumbles_forced_lost"]
    out.index.name = "team"
    return out.reset_index()


def points_per_drive(rush_td, pass_td, fg_made, turnovers, punts, fga) -> float:
    """PFR-Definition: 'Drives' werden ueber die Anzahl an Serien-Enden
    approximiert (TD, FG-Versuch, Turnover, Punt)."""
    denom = rush_td + pass_td + turnovers + punts + fga
    if denom <= 0:
        return 0.0
    return (7 * (rush_td + pass_td) + 3 * fg_made) / denom


# ---------------------------------------------------------------------------
# Games played / "Games Started" (approximiert ueber Snap-%, siehe README)
# ---------------------------------------------------------------------------

def build_position_refinement(rosters: pd.DataFrame) -> dict[tuple[str, str], str]:
    """In neueren Saisons liefert snap_counts oft nur generische Codes
    ('OL', 'DL', 'DB') statt der konkreten Position. import_seasonal_rosters
    fuehrt in 'depth_chart_position' meist noch die spezifische Position
    (T/G/C bzw. DE/DT/NT). Liefert (Spielername, Team) -> spezifische
    Position, wo verfuegbar und plausibel.

    Schluessel ist (Name, Team) statt einer ID: 'pfr_id' fehlt in den
    Roster-Daten bei ca. 30% der Spieler (v.a. juengere/neuere), gerade bei
    Linemen oft genau die, die wir hier auffuellen wollen. (Name, Team) ist
    innerhalb einer Saison kollisionsfrei."""
    valid = _SPECIFIC_OLINE | _SPECIFIC_DL
    df = rosters.dropna(subset=["player_name", "team", "depth_chart_position"])
    df = df[df["depth_chart_position"].isin(valid)]
    return {(n, t): p for n, t, p in zip(df["player_name"], df["team"], df["depth_chart_position"])}


def games_played_started(
    snaps: pd.DataFrame, season: int, through_week: int | None, start_threshold: float,
    pfr_to_gsis: dict[str, str] | None = None, season_type: str = "REG",
    position_refinement: dict[tuple[str, str], str] | None = None,
) -> pd.DataFrame:
    """Games played/started je Spieler (Snap-% als Start-Proxy, siehe README).

    pfr_to_gsis=None (Default) -> player_id bleibt die PFR-ID. Das wird fuer
    die Offensive Line gebraucht, weil die ffverse/nfl_data_py-ID-Crosswalk
    (import_ids) Linemen kaum abdeckt (sie sind fantasy-irrelevant).
    Fuer die Defense wird die Crosswalk uebergeben, weil dort gsis_id
    gebraucht wird, um mit den PBP-Individualstats (sacks/INTs/tackles) zu
    joinen - dort ist die Abdeckung >99%.
    """
    df = snaps[snaps["season"] == season].copy()
    if "game_type" in df.columns:
        df = df[df["game_type"] == season_type]
    if through_week is not None:
        df = df[df["week"] <= through_week]

    df["snap_pct"] = df[["offense_pct", "defense_pct", "st_pct"]].max(axis=1)
    df["started"] = df["snap_pct"] >= start_threshold

    if position_refinement:
        generic = {"OL", "DL"}
        refined = pd.Series(
            list(zip(df["player"], df["team"])), index=df.index
        ).map(position_refinement)
        df["position"] = df["position"].where(~df["position"].isin(generic) | refined.isna(), refined)

    g = df.groupby(["pfr_player_id", "player", "team", "position"])
    out = g.agg(
        games_played=("game_id", "nunique"),
        games_started=("started", "sum"),
    ).reset_index()

    if pfr_to_gsis is None:
        out["player_id"] = out["pfr_player_id"]
    else:
        out["player_id"] = out["pfr_player_id"].map(pfr_to_gsis)
        out = out.dropna(subset=["player_id"])
    return out


# ---------------------------------------------------------------------------
# Offense: Rusher / Passer / Receiver
# ---------------------------------------------------------------------------

def player_offense_stats(pbp: pd.DataFrame, season: int, through_week: int | None = None) -> dict[str, pd.DataFrame]:
    df = _filter_week(pbp, season, through_week)

    rush = df[df["rush_attempt"] == 1].dropna(subset=["rusher_player_id"])
    rushers = rush.groupby(["rusher_player_id", "rusher_player_name", "posteam"]).agg(
        carries=("rush_attempt", "sum"),
        rushing_yards=("rushing_yards", "sum"),
    ).reset_index().rename(columns={
        "rusher_player_id": "player_id", "rusher_player_name": "player_name", "posteam": "team",
    })

    passers = df[df["pass_attempt"] == 1].dropna(subset=["passer_player_id"])
    passer_stats = passers.groupby(["passer_player_id", "passer_player_name", "posteam"]).agg(
        attempts=("pass_attempt", "sum"),
        passing_yards=("passing_yards", "sum"),
        passing_tds=("pass_touchdown", "sum"),
        interceptions=("interception", "sum"),
    ).reset_index().rename(columns={
        "passer_player_id": "player_id", "passer_player_name": "player_name", "posteam": "team",
    })
    passer_stats["ay_a"] = (
        passer_stats["passing_yards"]
        + 20 * passer_stats["passing_tds"]
        - 45 * passer_stats["interceptions"]
    ) / passer_stats["attempts"].replace(0, pd.NA)

    recv = df[df["complete_pass"] == 1].dropna(subset=["receiver_player_id"])
    receivers = recv.groupby(["receiver_player_id", "receiver_player_name", "posteam"]).agg(
        receptions=("complete_pass", "sum"),
        receiving_yards=("receiving_yards", "sum"),
    ).reset_index().rename(columns={
        "receiver_player_id": "player_id", "receiver_player_name": "player_name", "posteam": "team",
    })

    return {"rushers": rushers, "passers": passer_stats, "receivers": receivers}


def league_rb_ypc(rushers: pd.DataFrame, roster_positions: dict[str, str]) -> float:
    rb = rushers[rushers["player_id"].map(roster_positions).eq("RB")]
    total_yards = rb["rushing_yards"].sum()
    total_carries = rb["carries"].sum()
    return total_yards / total_carries if total_carries else 0.0


def league_ay_a(passers: pd.DataFrame, min_attempts: int) -> float:
    qualifying = passers[passers["attempts"] >= min_attempts]
    total_ay = (
        qualifying["passing_yards"] + 20 * qualifying["passing_tds"] - 45 * qualifying["interceptions"]
    ).sum()
    total_att = qualifying["attempts"].sum()
    return total_ay / total_att if total_att else 0.0


# ---------------------------------------------------------------------------
# Defense (Front Seven / Secondary)
# ---------------------------------------------------------------------------

def player_defense_stats(pbp: pd.DataFrame, season: int, through_week: int | None = None) -> pd.DataFrame:
    df = _filter_week(pbp, season, through_week)
    counts: dict[str, dict[str, float]] = {}

    def bump(pid, name, team, field, amount=1.0):
        if pd.isna(pid):
            return
        rec = counts.setdefault(pid, {"player_name": name, "team": team, "sacks": 0.0,
                                       "fumble_recoveries": 0.0, "interceptions": 0.0,
                                       "defensive_tds": 0.0, "solo_tackles": 0.0,
                                       "assist_tackles": 0.0})
        rec[field] += amount

    for _, r in df[df["sack"] == 1].iterrows():
        bump(r.get("sack_player_id"), r.get("sack_player_name"), r.get("defteam"), "sacks", 1.0)
        for i in (1, 2):
            hid, hname = r.get(f"half_sack_{i}_player_id"), r.get(f"half_sack_{i}_player_name")
            if pd.notna(hid):
                bump(hid, hname, r.get("defteam"), "sacks", 0.5)

    for _, r in df[df["interception"] == 1].iterrows():
        bump(r.get("interception_player_id"), r.get("interception_player_name"), r.get("defteam"), "interceptions", 1.0)
        if r.get("touchdown") == 1 and r.get("return_touchdown") == 1:
            bump(r.get("interception_player_id"), r.get("interception_player_name"), r.get("defteam"), "defensive_tds", 1.0)

    fum = df[(df["fumble_recovery_1_team"].notna()) | (df["fumble_recovery_2_team"].notna())]
    for _, r in fum.iterrows():
        for i in (1, 2):
            fid, fname, fteam = r.get(f"fumble_recovery_{i}_player_id"), r.get(f"fumble_recovery_{i}_player_name"), r.get(f"fumble_recovery_{i}_team")
            if pd.notna(fid) and fteam == r.get("defteam"):
                bump(fid, fname, fteam, "fumble_recoveries", 1.0)
                if r.get("touchdown") == 1 and r.get("return_touchdown") == 1:
                    bump(fid, fname, fteam, "defensive_tds", 1.0)

    tkl = df[(df["solo_tackle"] == 1) | (df["tackle_with_assist"] == 1) | (df["assist_tackle"] == 1)]
    for _, r in tkl.iterrows():
        for i in (1, 2):
            sid, sname = r.get(f"solo_tackle_{i}_player_id"), r.get(f"solo_tackle_{i}_player_name")
            if pd.notna(sid):
                bump(sid, sname, r.get("defteam"), "solo_tackles", 1.0)
            twid, twname, twteam = r.get(f"tackle_with_assist_{i}_player_id"), r.get(f"tackle_with_assist_{i}_player_name"), r.get(f"tackle_with_assist_{i}_team")
            if pd.notna(twid) and twteam == r.get("defteam"):
                bump(twid, twname, twteam, "solo_tackles", 1.0)
        for i in (1, 2, 3, 4):
            aid, aname = r.get(f"assist_tackle_{i}_player_id"), r.get(f"assist_tackle_{i}_player_name")
            if pd.notna(aid):
                bump(aid, aname, r.get("defteam"), "assist_tackles", 1.0)  # Gewichtung erfolgt in av_engine (config.assist_tackle_weight)

    out = pd.DataFrame.from_dict(counts, orient="index").reset_index().rename(columns={"index": "player_id"})
    return out


# ---------------------------------------------------------------------------
# Kicking / Punting
# ---------------------------------------------------------------------------

_FG_BANDS = [(0, 19, "1"), (20, 29, "2"), (30, 39, "3"), (40, 49, "4"), (50, 999, "5")]


def player_kicking_stats(pbp: pd.DataFrame, season: int, through_week: int | None = None) -> pd.DataFrame:
    df = _filter_week(pbp, season, through_week)
    fg = df[df["field_goal_attempt"] == 1].dropna(subset=["kicker_player_id"]).copy()
    xp = df[df["extra_point_attempt"] == 1].dropna(subset=["kicker_player_id"]).copy()

    rows: dict[str, dict] = {}

    def rec(pid, name, team):
        return rows.setdefault(pid, {
            "player_name": name, "team": team,
            "xpm": 0, "xpa": 0,
            **{f"fgm{b}": 0 for _, _, b in _FG_BANDS}, **{f"fga{b}": 0 for _, _, b in _FG_BANDS},
            "fgm_u": 0, "fga_u": 0,
        })

    for _, r in xp.iterrows():
        d = rec(r["kicker_player_id"], r.get("kicker_player_name"), r.get("posteam"))
        d["xpa"] += 1
        if r.get("extra_point_result") == "good":
            d["xpm"] += 1

    for _, r in fg.iterrows():
        d = rec(r["kicker_player_id"], r.get("kicker_player_name"), r.get("posteam"))
        dist = r.get("kick_distance")
        made = r.get("field_goal_result") == "made"
        band = None
        if pd.notna(dist):
            for lo, hi, b in _FG_BANDS:
                if lo <= dist <= hi:
                    band = b
                    break
        if band:
            d[f"fga{band}"] += 1
            if made:
                d[f"fgm{band}"] += 1
        else:
            d["fga_u"] += 1
            if made:
                d["fgm_u"] += 1

    out = pd.DataFrame.from_dict(rows, orient="index").reset_index().rename(columns={"index": "player_id"})
    return out


def player_punting_stats(pbp: pd.DataFrame, season: int, through_week: int | None = None) -> pd.DataFrame:
    df = _filter_week(pbp, season, through_week)
    punts = df[df["punt_attempt"] == 1].dropna(subset=["punter_player_id"])

    out = punts.groupby(["punter_player_id", "punter_player_name", "posteam"]).agg(
        punt=("punt_attempt", "sum"),
        punt_blocked=("punt_blocked", "sum"),
        punt_yds=("kick_distance", "sum"),
    ).reset_index().rename(columns={
        "punter_player_id": "player_id", "punter_player_name": "player_name", "posteam": "team",
    })
    return out


def player_return_tds(pbp: pd.DataFrame, season: int, through_week: int | None = None) -> pd.DataFrame:
    df = _filter_week(pbp, season, through_week)
    rets = df[(df["return_touchdown"] == 1) & (df["play_type"].isin(["punt", "kickoff"]))]
    rows = []
    for _, r in rets.iterrows():
        pid = r.get("punt_returner_player_id") if r.get("play_type") == "punt" else r.get("kickoff_returner_player_id")
        name = r.get("punt_returner_player_name") if r.get("play_type") == "punt" else r.get("kickoff_returner_player_name")
        if pd.notna(pid):
            rows.append({"player_id": pid, "player_name": name, "team": r.get("posteam"), "return_tds": 1})
    if not rows:
        return pd.DataFrame(columns=["player_id", "player_name", "team", "return_tds"])
    out = pd.DataFrame(rows).groupby(["player_id", "player_name", "team"]).sum().reset_index()
    return out


def team_games_played(schedules: pd.DataFrame, season: int, through_week: int | None = None) -> pd.DataFrame:
    df = schedules[schedules["season"] == season]
    if through_week is not None:
        df = df[df["week"] <= through_week]
    df = df[df["result"].notna()]  # nur tatsaechlich gespielte Spiele zaehlen
    home = df[["home_team"]].rename(columns={"home_team": "team"})
    away = df[["away_team"]].rename(columns={"away_team": "team"})
    both = pd.concat([home, away])
    return both.groupby("team").size().reset_index(name="games")
