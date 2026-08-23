"""
Oeffentliche Datenzugriffs-Funktionen fuer aggregate.py/pipeline.py.

Delegiert an db.py (SQLite): jede Saison wird nur beim allerersten Mal von
nflverse geladen, danach kommt alles aus der lokalen DB
(nfl_av_tracker/data_cache/tracker.db). Siehe db.py fuer Details.
"""

from __future__ import annotations

import pandas as pd

from . import db


def get_pbp_special(seasons: list[int]) -> pd.DataFrame:
    return db.load_pbp_special(seasons)


def get_weekly_data(seasons: list[int]) -> pd.DataFrame:
    return db.load_weekly_data(seasons)


def get_weekly_def(seasons: list[int]) -> pd.DataFrame:
    return db.load_weekly_def(seasons)


def get_snap_counts(seasons: list[int]) -> pd.DataFrame:
    return db.load_snap_counts(seasons)


def get_schedules(seasons: list[int]) -> pd.DataFrame:
    return db.load_schedules(seasons)


def get_seasonal_rosters(seasons: list[int]) -> pd.DataFrame:
    return db.load_rosters(seasons)


def clear_cache() -> None:
    db.clear_all()
