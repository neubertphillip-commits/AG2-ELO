"""
SQLite-Persistenz fuer den NFL-AV-Tracker.

Zwei Arten von Daten werden dauerhaft in einer einzigen DB-Datei gehalten
(`nfl_av_tracker/data_cache/tracker.db`), statt bei jedem Aufruf neu von
nflverse zu laden bzw. die AV-Formeln neu zu rechnen:

1. Rohdaten (Play-by-Play-Ausschnitt, Snap Counts, Schedules, Rosters,
   ID-Crosswalk) - werden pro Saison genau EINMAL von nflverse geladen und
   danach nur noch aus der DB gelesen. `loaded_seasons` merkt sich, welche
   Saison/Datensatz-Kombination schon vorhanden ist.

2. Berechnete AV-Ergebnisse - werden pro (Config-Hash, Saison) gespeichert.
   Eine abgeschlossene Saison wird unter einer bestimmten Variablen-
   Konfiguration nur EINMAL gerechnet; danach liefert jede weitere Anfrage
   mit denselben Variablen einen reinen DB-Read. Aendert sich eine Variable
   (anderer Hash) oder ist die Saison noch nicht abgeschlossen, wird neu
   gerechnet.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import sqlite3
from pathlib import Path

import pandas as pd

from .config import AVConfig

DB_PATH = Path(__file__).parent / "data_cache" / "tracker.db"
DB_PATH.parent.mkdir(exist_ok=True)

# Offense-Yards/TDs (player_offense_stats, team_offense/defense_inputs) und
# Defense-Sacks/INTs/Tackles (player_defense_stats) kommen aus fertigen
# Box-Score-Tabellen (import_weekly_data / import_weekly_pfr('def')) - dafuer
# ist kein Play-Level-Datensatz noetig. Nur fuer Kicker-Distanzbaender,
# Punt-Laenge je Versuch, Fumble-Recoveries und Defensive-TDs gibt es keine
# fertige Box-Score-Tabelle; dafuer wird PBP auf genau diese Play-Typen
# gefiltert (~10% der Zeilen einer vollen PBP-Saison statt 100%).
_PBP_SPECIAL_COLS = [
    "season", "week", "posteam", "defteam", "play_type", "game_id",
    "touchdown", "return_touchdown", "interception",
    "field_goal_attempt", "field_goal_result", "kick_distance", "kicker_player_id", "kicker_player_name",
    "extra_point_attempt", "extra_point_result",
    "punt_attempt", "punt_blocked", "punter_player_id", "punter_player_name",
    "punt_returner_player_id", "punt_returner_player_name",
    "kickoff_returner_player_id", "kickoff_returner_player_name",
    "interception_player_id", "interception_player_name",
    "fumble_recovery_1_player_id", "fumble_recovery_1_player_name", "fumble_recovery_1_team",
    "fumble_recovery_2_player_id", "fumble_recovery_2_player_name", "fumble_recovery_2_team",
]

_WEEKLY_COLS = ["season", "week", "player_id", "player_name", "recent_team", "opponent_team",
                "carries", "rushing_yards", "rushing_tds", "rushing_fumbles_lost",
                "attempts", "passing_yards", "passing_tds", "interceptions",
                "receptions", "receiving_yards", "receiving_tds", "receiving_fumbles_lost",
                "sack_fumbles_lost"]
_WEEKLY_DEF_COLS = ["season", "week", "team", "pfr_player_id", "pfr_player_name",
                     "def_sacks", "def_ints", "def_tackles_combined"]

_SNAP_COLS = ["season", "week", "game_id", "game_type", "pfr_player_id", "player", "team",
              "position", "offense_snaps", "offense_pct", "defense_snaps", "defense_pct",
              "st_snaps", "st_pct"]
_SCHEDULE_COLS = ["season", "week", "home_team", "away_team", "result"]
_ROSTER_COLS = ["season", "player_name", "team", "position", "depth_chart_position", "pfr_id"]


def _filter_special_plays(pbp: pd.DataFrame) -> pd.DataFrame:
    """Nur Plays behalten, die fuer Kicking/Punting/Fumble-Recovery/
    Defensive-TDs gebraucht werden - das sind ca. 10% der Plays einer
    Saison, siehe Docstring oben."""
    is_td_return = (pbp.get("touchdown") == 1) & (pbp.get("return_touchdown") == 1)
    has_fumble_recovery = pbp.get("fumble_recovery_1_team").notna() | pbp.get("fumble_recovery_2_team").notna()
    mask = (
        (pbp.get("field_goal_attempt") == 1)
        | (pbp.get("extra_point_attempt") == 1)
        | (pbp.get("punt_attempt") == 1)
        | is_td_return
        | has_fumble_recovery
    )
    return pbp[mask.fillna(False)]


def _derive_weekly_from_pbp(season: int) -> pd.DataFrame:
    """Fallback fuer load_weekly_data(), wenn nflverse die schlanke
    Box-Score-Datei fuer `season` (noch) nicht veroeffentlicht hat: baut
    dieselbe Player-Week-Tabellenform direkt aus vollem PBP nach (nur fuer
    diese eine Saison, nicht dauerhaft als PBP gespeichert)."""
    import nfl_data_py as nfl

    pbp = nfl.import_pbp_data([season], downcast=True, cache=False)

    rush = pbp[pbp["rush_attempt"] == 1].dropna(subset=["rusher_player_id"])
    r = rush.groupby(["season", "week", "rusher_player_id", "rusher_player_name", "posteam", "defteam"]).agg(
        carries=("rush_attempt", "sum"), rushing_yards=("rushing_yards", "sum"),
        rushing_tds=("rush_touchdown", "sum"), rushing_fumbles_lost=("fumble_lost", "sum"),
    ).reset_index().rename(columns={"rusher_player_id": "player_id", "rusher_player_name": "player_name",
                                     "posteam": "recent_team", "defteam": "opponent_team"})

    passers = pbp[pbp["pass_attempt"] == 1].dropna(subset=["passer_player_id"])
    p = passers.groupby(["season", "week", "passer_player_id", "passer_player_name", "posteam", "defteam"]).agg(
        attempts=("pass_attempt", "sum"), passing_yards=("passing_yards", "sum"),
        passing_tds=("pass_touchdown", "sum"), interceptions=("interception", "sum"),
        sack_fumbles_lost=("fumble_lost", "sum"),
    ).reset_index().rename(columns={"passer_player_id": "player_id", "passer_player_name": "player_name",
                                     "posteam": "recent_team", "defteam": "opponent_team"})

    recv = pbp[pbp["complete_pass"] == 1].dropna(subset=["receiver_player_id"])
    c = recv.groupby(["season", "week", "receiver_player_id", "receiver_player_name", "posteam", "defteam"]).agg(
        receptions=("complete_pass", "sum"), receiving_yards=("receiving_yards", "sum"),
        receiving_tds=("pass_touchdown", "sum"), receiving_fumbles_lost=("fumble_lost", "sum"),
    ).reset_index().rename(columns={"receiver_player_id": "player_id", "receiver_player_name": "player_name",
                                     "posteam": "recent_team", "defteam": "opponent_team"})

    keys = ["season", "week", "player_id", "player_name", "recent_team", "opponent_team"]
    out = r.merge(p, on=keys, how="outer").merge(c, on=keys, how="outer")
    return out.fillna(0)


def _derive_weekly_def_from_pbp(season: int) -> pd.DataFrame:
    """Fallback fuer load_weekly_def(), analog zu _derive_weekly_from_pbp:
    baut Sacks/INTs/Tackles-Zaehler direkt aus vollem PBP nach."""
    import nfl_data_py as nfl

    pbp = nfl.import_pbp_data([season], downcast=True, cache=False)
    counts: dict[tuple, dict] = {}

    def bump(pid, name, team, wk, field, amount=1.0):
        if pd.isna(pid):
            return
        key = (pid, wk)
        rec = counts.setdefault(key, {"pfr_player_id": pid, "pfr_player_name": name, "team": team,
                                       "season": season, "week": wk,
                                       "def_sacks": 0.0, "def_ints": 0.0, "def_tackles_combined": 0.0})
        rec[field] += amount

    for _, r in pbp[pbp["sack"] == 1].iterrows():
        bump(r.get("sack_player_id"), r.get("sack_player_name"), r.get("defteam"), r.get("week"), "def_sacks", 1.0)
        for i in (1, 2):
            hid, hname = r.get(f"half_sack_{i}_player_id"), r.get(f"half_sack_{i}_player_name")
            if pd.notna(hid):
                bump(hid, hname, r.get("defteam"), r.get("week"), "def_sacks", 0.5)

    for _, r in pbp[pbp["interception"] == 1].iterrows():
        bump(r.get("interception_player_id"), r.get("interception_player_name"), r.get("defteam"), r.get("week"), "def_ints", 1.0)

    tkl = pbp[(pbp["solo_tackle"] == 1) | (pbp["tackle_with_assist"] == 1) | (pbp["assist_tackle"] == 1)]
    for _, r in tkl.iterrows():
        for i in (1, 2):
            sid, sname = r.get(f"solo_tackle_{i}_player_id"), r.get(f"solo_tackle_{i}_player_name")
            if pd.notna(sid):
                bump(sid, sname, r.get("defteam"), r.get("week"), "def_tackles_combined", 1.0)
            twid, twname, twteam = r.get(f"tackle_with_assist_{i}_player_id"), r.get(f"tackle_with_assist_{i}_player_name"), r.get(f"tackle_with_assist_{i}_team")
            if pd.notna(twid) and twteam == r.get("defteam"):
                bump(twid, twname, twteam, r.get("week"), "def_tackles_combined", 1.0)
        for i in (1, 2, 3, 4):
            aid, aname = r.get(f"assist_tackle_{i}_player_id"), r.get(f"assist_tackle_{i}_player_name")
            if pd.notna(aid):
                bump(aid, aname, r.get("defteam"), r.get("week"), "def_tackles_combined", 0.5)

    return pd.DataFrame.from_dict(counts, orient="index").reset_index(drop=True)


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def ensure_schema() -> None:
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS loaded_seasons (
                dataset TEXT NOT NULL, season INTEGER NOT NULL, loaded_at TEXT NOT NULL,
                PRIMARY KEY (dataset, season)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS av_config_registry (
                config_hash TEXT PRIMARY KEY, config_json TEXT NOT NULL, created_at TEXT NOT NULL
            )
        """)
        # PK enthaelt 'team': ein Spieler, der die Saison wechselt (Trade),
        # kommt mit demselben player_id aber zwei Teams vor.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS av_results (
                config_hash TEXT NOT NULL, season INTEGER NOT NULL,
                player_id TEXT NOT NULL, player_name TEXT, team TEXT NOT NULL, av REAL NOT NULL,
                computed_at TEXT NOT NULL,
                PRIMARY KEY (config_hash, season, player_id, team)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_av_results_lookup ON av_results(config_hash, season)")


ensure_schema()


# ---------------------------------------------------------------------------
# Config-Hashing
# ---------------------------------------------------------------------------

def config_hash(cfg: AVConfig) -> str:
    payload = json.dumps(dataclasses.asdict(cfg), sort_keys=True)
    h = hashlib.sha256(payload.encode()).hexdigest()[:16]
    with _connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO av_config_registry (config_hash, config_json, created_at) VALUES (?, ?, datetime('now'))",
            (h, payload),
        )
    return h


# ---------------------------------------------------------------------------
# Generischer Rohdaten-Loader: pro Saison nur einmal von nflverse holen
# ---------------------------------------------------------------------------

def _missing_seasons(dataset: str, seasons: list[int]) -> list[int]:
    with _connect() as conn:
        rows = conn.execute(
            f"SELECT season FROM loaded_seasons WHERE dataset = ? AND season IN ({','.join('?' * len(seasons))})",
            [dataset, *seasons],
        ).fetchall()
    have = {r[0] for r in rows}
    return [s for s in seasons if s not in have]


def _mark_loaded(dataset: str, seasons: list[int]) -> None:
    with _connect() as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO loaded_seasons (dataset, season, loaded_at) VALUES (?, ?, datetime('now'))",
            [(dataset, s) for s in seasons],
        )


def _load_seasonal(dataset: str, table: str, seasons: list[int], columns: list[str],
                    fetch_fn, prepare_fn=None, min_season: int | None = None,
                    fallback_fn=None) -> pd.DataFrame:
    """min_season: manche nflverse-Quellen lehnen Jahre vor einem bestimmten
    Startjahr komplett ab (z.B. Snap Counts vor 2013, Defense-Box-Scores vor
    2018 - siehe README). Jahre davor werden als 'geladen, aber leer'
    markiert, damit nicht bei jedem Aufruf erneut (erfolglos) angefragt wird.

    fallback_fn(season) -> DataFrame: wird pro Saison versucht, wenn
    fetch_fn() fuer sie fehlschlaegt (z.B. weil nflverse die schlanke
    Box-Score-Datei fuer die aktuellste Saison noch nicht veroeffentlicht
    hat, PBP dafuer aber schon existiert)."""
    seasons = sorted(set(seasons))
    missing = _missing_seasons(dataset, seasons)
    if missing:
        fetchable = [s for s in missing if min_season is None or s >= min_season]
        frames = []
        for s in fetchable:
            try:
                frames.append(fetch_fn([s]))
            except Exception:
                if fallback_fn is None:
                    raise
                frames.append(fallback_fn(s))
        if frames:
            fresh = pd.concat(frames, ignore_index=True)
            if prepare_fn:
                fresh = prepare_fn(fresh)
            cols_present = [c for c in columns if c in fresh.columns]
            fresh = fresh[cols_present].copy()
            with _connect() as conn:
                fresh.to_sql(table, conn, if_exists="append", index=False)
        _mark_loaded(dataset, missing)  # inkl. zu alter Jahre, damit die nicht jedes Mal neu versucht werden

    with _connect() as conn:
        placeholders = ",".join("?" * len(seasons))
        try:
            return pd.read_sql(f"SELECT * FROM {table} WHERE season IN ({placeholders})", conn, params=seasons)
        except pd.errors.DatabaseError:
            return pd.DataFrame(columns=columns)


def load_pbp_special(seasons: list[int]) -> pd.DataFrame:
    """Play-Level-Daten, aber nur die ~10% der Plays, die fuer Kicking/
    Punting/Fumble-Recoveries/Defensive-TDs gebraucht werden (siehe
    _filter_special_plays). Alles andere (Offense-Yards, Sacks/INTs/Tackles)
    kommt aus fertigen Box-Score-Tabellen - siehe load_weekly_data/
    load_weekly_def."""
    import nfl_data_py as nfl

    return _load_seasonal("pbp_special", "raw_pbp_special", seasons, _PBP_SPECIAL_COLS,
                           lambda s: nfl.import_pbp_data(s, downcast=True, cache=False),
                           prepare_fn=_filter_special_plays)


def load_weekly_data(seasons: list[int]) -> pd.DataFrame:
    """Offense-Box-Score je Spieler/Woche (Rushing/Passing/Receiving). Faellt
    pro Saison auf eine PBP-Ableitung zurueck, falls nflverse die Box-Score-
    Datei (noch) nicht veroeffentlicht hat (typischerweise die laufende/
    letzte Saison, kurz nachdem sie zu Ende ist)."""
    import nfl_data_py as nfl

    return _load_seasonal("weekly", "raw_weekly", seasons, _WEEKLY_COLS,
                           lambda s: nfl.import_weekly_data(s, downcast=True),
                           fallback_fn=_derive_weekly_from_pbp)


def load_weekly_def(seasons: list[int]) -> pd.DataFrame:
    """Defense-Box-Score je Spieler/Woche (Sacks/INTs/Tackles kombiniert).
    Nur ab 2018 verfuegbar (nflverse lehnt frueher komplett ab); Fallback
    auf PBP-Ableitung, falls die Datei fuer eine sonst unterstuetzte Saison
    (noch) nicht veroeffentlicht ist."""
    import nfl_data_py as nfl

    return _load_seasonal("weekly_def", "raw_weekly_def", seasons, _WEEKLY_DEF_COLS,
                           lambda s: nfl.import_weekly_pfr("def", s), min_season=2018,
                           fallback_fn=_derive_weekly_def_from_pbp)


def load_snap_counts(seasons: list[int]) -> pd.DataFrame:
    """Nur ab 2013 verfuegbar (nflverse lehnt frueher komplett ab)."""
    import nfl_data_py as nfl

    return _load_seasonal("snap_counts", "raw_snap_counts", seasons, _SNAP_COLS,
                           nfl.import_snap_counts, min_season=2013)


def load_schedules(seasons: list[int]) -> pd.DataFrame:
    import nfl_data_py as nfl

    return _load_seasonal("schedules", "raw_schedules", seasons, _SCHEDULE_COLS, nfl.import_schedules)


def load_rosters(seasons: list[int]) -> pd.DataFrame:
    import nfl_data_py as nfl

    return _load_seasonal("rosters", "raw_rosters", seasons, _ROSTER_COLS, nfl.import_seasonal_rosters)


def load_ids() -> pd.DataFrame:
    """Statischer ID-Crosswalk (kein Saison-Bezug) - einmalig laden, per
    force_refresh_ids() bei Bedarf neu ziehen (z.B. nach Rookie-Draft)."""
    with _connect() as conn:
        has_table = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='raw_ids'"
        ).fetchone()
        if has_table:
            df = pd.read_sql("SELECT * FROM raw_ids", conn)
            if not df.empty:
                return df

    import nfl_data_py as nfl

    ids = nfl.import_ids()
    with _connect() as conn:
        ids.to_sql("raw_ids", conn, if_exists="replace", index=False)
    return ids


def force_refresh_ids() -> None:
    with _connect() as conn:
        conn.execute("DROP TABLE IF EXISTS raw_ids")


# ---------------------------------------------------------------------------
# AV-Ergebnis-Cache
# ---------------------------------------------------------------------------

def is_season_final(schedules: pd.DataFrame, season: int) -> bool:
    season_games = schedules[schedules["season"] == season]
    if season_games.empty:
        return False
    return season_games["result"].notna().all()


def get_cached_av(config_hash_: str, season: int) -> pd.DataFrame | None:
    with _connect() as conn:
        df = pd.read_sql(
            "SELECT player_id, player_name, team, av FROM av_results WHERE config_hash = ? AND season = ?",
            conn, params=(config_hash_, season),
        )
    return df.sort_values("av", ascending=False).reset_index(drop=True) if not df.empty else None


def store_av(config_hash_: str, season: int, df: pd.DataFrame) -> None:
    if df.empty:
        return
    out = df[["player_id", "player_name", "team", "av"]].copy()
    out["config_hash"] = config_hash_
    out["season"] = season
    out["computed_at"] = pd.Timestamp.utcnow().isoformat()
    with _connect() as conn:
        conn.execute("DELETE FROM av_results WHERE config_hash = ? AND season = ?", (config_hash_, season))
        out.to_sql("av_results", conn, if_exists="append", index=False)


def cache_status(seasons: list[int]) -> pd.DataFrame:
    """Fuer die UI: welche Rohdaten/AV-Ergebnisse sind schon in der DB?"""
    with _connect() as conn:
        raw = pd.read_sql("SELECT dataset, season FROM loaded_seasons", conn)
        av_seasons = pd.read_sql("SELECT DISTINCT season FROM av_results", conn)
    rows = []
    for s in seasons:
        rows.append({
            "season": s,
            "raw_data_cached": s in set(raw[raw["dataset"] == "weekly"]["season"]) if not raw.empty else False,
            "any_av_cached": s in set(av_seasons["season"]) if not av_seasons.empty else False,
        })
    return pd.DataFrame(rows)


def clear_all() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
    for ext in ("-wal", "-shm"):
        p = Path(str(DB_PATH) + ext)
        if p.exists():
            p.unlink()
    ensure_schema()
