"""
Alle Konstanten der Approximate-Value-Methodik (Pro-Football-Reference) an
einer Stelle, editierbar. Defaults entsprechen 1:1 den auf
pro-football-reference.com/about/approximate_value.htm dokumentierten Werten.

Viele dieser Werte sind von PFR selbst als "arbitrary calibration" bezeichnet
(z.B. der Kicker-/Punter-Divisor). Sie lassen sich hier anpassen, ohne den
Rechenkern (av_engine.py) zu verändern.
"""

from dataclasses import dataclass


@dataclass
class AVConfig:
    # ---- Offense: Team-Pool ------------------------------------------
    # team_offense_points = offense_pool_scale * (team pts/drive) / (lg pts/drive)
    offense_pool_scale: float = 100.0

    # ---- Offensive Line -------------------------------------------------
    o_line_pool_share: float = 5 / 11  # 5 der 11 Offense-Spieler sind Linemen
    pos_multiplier_tackle: float = 1.2
    pos_multiplier_guard_center: float = 1.0
    pos_multiplier_fullback: float = 0.3
    pos_multiplier_tight_end: float = 0.2
    games_started_weight_oline: float = 5.0
    all_pro_multiplier_1st: float = 1.9   # nur fuer T/G/C
    all_pro_multiplier_2nd: float = 1.6
    all_pro_multiplier_pro_bowl: float = 1.3

    # ---- Skill-Position-Split --------------------------------------------
    rusher_pool_base_share: float = 0.22
    rusher_pool_reference_ratio: float = 0.37  # Liga-Referenz Rush/Total-Yards
    passer_share_of_remainder: float = 0.26
    receiver_share_of_remainder: float = 0.74

    rb_min_carries_for_efficiency: int = 200
    rb_efficiency_bonus_mult: float = 0.75
    rb_efficiency_penalty_mult: float = 2.0

    qb_min_attempts_for_efficiency: int = 150
    qb_efficiency_bonus_mult: float = 0.5
    qb_efficiency_penalty_mult: float = 2.0

    # ---- Defense: Team-Pool -----------------------------------------------
    front_seven_share: float = 2 / 3
    secondary_share: float = 1 / 3

    games_started_weight_defense: float = 5.0
    sack_weight: float = 1.0
    fumble_recovery_weight: float = 4.0
    interception_weight: float = 4.0
    defensive_td_weight: float = 5.0

    tackle_constant_dl: float = 0.6
    tackle_constant_lb: float = 0.3
    tackle_constant_db: float = 0.0
    tackle_constant_start_year: int = 1994  # davor keine offizielle Tackle-Stat

    all_pro_level_1st: float = 1.5
    all_pro_level_2nd: float = 1.0
    all_pro_level_pro_bowl: float = 0.5
    year_constant_pre_sack_era: float = 40.0
    year_constant_post_sack_era: float = 80.0
    sack_era_start_year: int = 1982  # davor keine offiziellen Sacks

    # ---- Special Teams ------------------------------------------------
    return_td_av: float = 1.0

    kicker_baseline_av_per_16: float = 3.125
    kicker_paa_divisor: float = 5.0
    kicker_playing_time_fga_weight: float = 3.0

    punter_baseline_av_per_16: float = 2.1875
    punter_yards_divisor: float = 200.0
    punt_block_penalty_yards: float = 13.0

    # ---- Saison-Normierung -------------------------------------------
    full_season_games: int = 16  # PFR normiert historisch auf 16, nicht 17

    # ---- Naeherungen fuer Daten, die ueber freie APIs nicht sauber
    #      verfuegbar sind (siehe README fuer Details) -------------------
    games_started_snap_threshold: float = 0.5  # Snap-% als "Start"-Proxy
    enable_all_pro_bonus: bool = False  # mangels freier Quelle standardmaessig aus
    assist_tackle_weight: float = 0.5   # Solo=1.0, Assist=diese Gewichtung

    # ---- Weighted Career AV --------------------------------------------
    weighted_career_weight_start: float = 1.0
    weighted_career_weight_step: float = 0.05  # -5 Prozentpunkte je Rang
    weighted_career_max_seasons: int = 20  # danach Gewicht <= 0
