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

# Schlanke Auswahl an PBP-Spalten, die av_engine/aggregate tatsaechlich
# braucht. Volles PBP hat ~370 Spalten - das waere unnoetig viel DB-Groesse.
_PBP_BASE_COLS = [
    "season", "week", "posteam", "defteam", "play_type", "game_id",
    "rush_attempt", "rush_touchdown", "rushing_yards", "rusher_player_id", "rusher_player_name",
    "pass_attempt", "pass_touchdown", "passing_yards", "passer_player_id", "passer_player_name",
    "interception", "complete_pass", "receiving_yards", "receiver_player_id", "receiver_player_name",
    "fumble_lost", "touchdown", "return_touchdown",
    "field_goal_attempt", "field_goal_result", "kick_distance", "kicker_player_id", "kicker_player_name",
    "extra_point_attempt", "extra_point_result",
    "punt_attempt", "punt_blocked", "punter_player_id", "punter_player_name",
    "punt_returner_player_id", "punt_returner_player_name",
    "kickoff_returner_player_id", "kickoff_returner_player_name",
    "sack", "sack_player_id", "sack_player_name",
    "half_sack_1_player_id", "half_sack_1_player_name", "half_sack_2_player_id", "half_sack_2_player_name",
    "interception_player_id", "interception_player_name",
    "fumble_recovery_1_player_id", "fumble_recovery_1_player_name", "fumble_recovery_1_team",
    "fumble_recovery_2_player_id", "fumble_recovery_2_player_name", "fumble_recovery_2_team",
    "solo_tackle", "solo_tackle_1_player_id", "solo_tackle_1_player_name",
    "solo_tackle_2_player_id", "solo_tackle_2_player_name",
    "tackle_with_assist", "tackle_with_assist_1_player_id", "tackle_with_assist_1_player_name",
    "tackle_with_assist_1_team", "tackle_with_assist_2_player_id", "tackle_with_assist_2_player_name",
    "tackle_with_assist_2_team",
    "assist_tackle", "assist_tackle_1_player_id", "assist_tackle_1_player_name",
    "assist_tackle_2_player_id", "assist_tackle_2_player_name",
    "assist_tackle_3_player_id", "assist_tackle_3_player_name",
    "assist_tackle_4_player_id", "assist_tackle_4_player_name",
]

_SNAP_COLS = ["season", "week", "game_id", "game_type", "pfr_player_id", "player", "team",
              "position", "offense_snaps", "offense_pct", "defense_snaps", "defense_pct",
              "st_snaps", "st_pct"]
_SCHEDULE_COLS = ["season", "week", "home_team", "away_team", "result"]
_ROSTER_COLS = ["season", "player_name", "team", "position", "depth_chart_position", "pfr_id"]


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
                    fetch_fn, prepare_fn=None) -> pd.DataFrame:
    seasons = sorted(set(seasons))
    missing = _missing_seasons(dataset, seasons)
    if missing:
        fresh = fetch_fn(missing)
        if prepare_fn:
            fresh = prepare_fn(fresh)
        cols_present = [c for c in columns if c in fresh.columns]
        fresh = fresh[cols_present].copy()
        with _connect() as conn:
            fresh.to_sql(table, conn, if_exists="append", index=False)
        _mark_loaded(dataset, missing)

    with _connect() as conn:
        placeholders = ",".join("?" * len(seasons))
        try:
            return pd.read_sql(f"SELECT * FROM {table} WHERE season IN ({placeholders})", conn, params=seasons)
        except pd.errors.DatabaseError:
            return pd.DataFrame(columns=columns)


def load_pbp(seasons: list[int]) -> pd.DataFrame:
    import nfl_data_py as nfl

    return _load_seasonal("pbp", "raw_pbp", seasons, _PBP_BASE_COLS,
                           lambda s: nfl.import_pbp_data(s, downcast=True, cache=False))


def load_snap_counts(seasons: list[int]) -> pd.DataFrame:
    import nfl_data_py as nfl

    return _load_seasonal("snap_counts", "raw_snap_counts", seasons, _SNAP_COLS, nfl.import_snap_counts)


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
            "raw_data_cached": s in set(raw[raw["dataset"] == "pbp"]["season"]) if not raw.empty else False,
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
