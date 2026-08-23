"""
Datenzugriff ueber nfl_data_py (kostenloser Wrapper um die nflverse-Daten,
kein API-Key noetig). Ergebnisse werden lokal als Parquet gecached, damit
Streamlit-Reruns und wiederholte Aufrufe nicht jedes Mal neu von GitHub
(nflverse Release-Assets) laden.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

CACHE_DIR = Path(__file__).parent / "data_cache"
CACHE_DIR.mkdir(exist_ok=True)


def _cache_path(name: str, seasons: list[int]) -> Path:
    tag = "-".join(str(s) for s in sorted(seasons))
    return CACHE_DIR / f"{name}_{tag}.parquet"


def _load_or_fetch(name: str, seasons: list[int], fetch_fn) -> pd.DataFrame:
    path = _cache_path(name, seasons)
    if path.exists():
        return pd.read_parquet(path)
    df = fetch_fn(seasons)
    try:
        df.to_parquet(path)
    except Exception:
        pass  # Cache ist ein Nice-to-have, kein Hard-Requirement
    return df


def get_weekly_data(seasons: list[int]) -> pd.DataFrame:
    """Offense-Boxscore je Spieler/Woche (Rushing/Passing/Receiving)."""
    import nfl_data_py as nfl

    return _load_or_fetch(
        "weekly", seasons, lambda s: nfl.import_weekly_data(s, downcast=True)
    )


def get_pbp_data(seasons: list[int]) -> pd.DataFrame:
    """Play-by-Play - Quelle fuer Defense-/Kicking-/Punting-Individualstats
    und fuer die Team-Punkte-pro-Drive-Zaehler."""
    import nfl_data_py as nfl

    return _load_or_fetch(
        "pbp", seasons, lambda s: nfl.import_pbp_data(s, downcast=True, cache=False)
    )


def get_snap_counts(seasons: list[int]) -> pd.DataFrame:
    """Snap-Anteile je Spieler/Spiel - Proxy fuer 'Games Started', da PFRs
    eigentliche Start-Flags ueber freie APIs nicht sauber verfuegbar sind."""
    import nfl_data_py as nfl

    return _load_or_fetch("snaps", seasons, nfl.import_snap_counts)


def get_schedules(seasons: list[int]) -> pd.DataFrame:
    import nfl_data_py as nfl

    return _load_or_fetch("schedules", seasons, nfl.import_schedules)


def get_seasonal_rosters(seasons: list[int]) -> pd.DataFrame:
    """Fuer Positionszuordnung (Tackle/Guard/Center/... , DL/LB/DB)."""
    import nfl_data_py as nfl

    return _load_or_fetch("rosters", seasons, nfl.import_seasonal_rosters)


def clear_cache() -> None:
    for f in CACHE_DIR.glob("*.parquet"):
        f.unlink()
