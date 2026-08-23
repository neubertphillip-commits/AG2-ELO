"""
Streamlit-Dashboard fuer den NFL-Approximate-Value-Tracker.

Start:  streamlit run nfl_av_tracker/app.py
"""

from __future__ import annotations

import dataclasses

import pandas as pd
import streamlit as st

from nfl_av_tracker import AVConfig, db
from nfl_av_tracker.career import weighted_career_av
from nfl_av_tracker.pipeline import build_multi_season_av, build_season_av, warm_historical_cache
from nfl_av_tracker.projection import build_projected_season_av

st.set_page_config(page_title="NFL Approximate Value Tracker", page_icon="🏈", layout="wide")

CURRENT_SEASON = 2025  # letzte vollstaendig abgeschlossene Saison als Default
FIRST_AVAILABLE_SEASON = 1999  # nflverse-PBP-Daten beginnen 1999


@st.cache_data(show_spinner="Lade & berechne Saison-AV ...", ttl=3600)
def _cached_season_av(cfg_dict: dict, season: int) -> pd.DataFrame:
    return build_season_av(AVConfig(**cfg_dict), season)


@st.cache_data(show_spinner="Lade & berechne Hochrechnung ...", ttl=1800)
def _cached_projection(cfg_dict: dict, season: int, through_week: int) -> pd.DataFrame:
    return build_projected_season_av(AVConfig(**cfg_dict), season, through_week)


@st.cache_data(show_spinner="Lade & berechne Stand der laufenden Saison ...", ttl=1800)
def _cached_partial_season(cfg_dict: dict, season: int, through_week: int) -> pd.DataFrame:
    return build_season_av(AVConfig(**cfg_dict), season, through_week)


@st.cache_data(show_spinner="Lade & berechne mehrere Saisons (kann dauern) ...", ttl=3600)
def _cached_multi_season(cfg_dict: dict, seasons: tuple[int, ...]) -> pd.DataFrame:
    return build_multi_season_av(AVConfig(**cfg_dict), list(seasons))


def _config_sidebar() -> AVConfig:
    st.sidebar.header("⚙️ AV-Variablen")
    st.sidebar.caption(
        "Alle Konstanten der PFR-Methodik. Viele sind laut PFR selbst "
        "willkuerlich kalibriert - hier frei anpassbar."
    )
    if "cfg" not in st.session_state:
        st.session_state.cfg = AVConfig()
    cfg = st.session_state.cfg

    if st.sidebar.button("↺ Auf PFR-Standardwerte zuruecksetzen"):
        st.session_state.cfg = AVConfig()
        st.rerun()

    updates = {}
    with st.sidebar.expander("Offense: Team-Pool & O-Line"):
        updates["offense_pool_scale"] = st.number_input("Offense-Pool-Skalierung", value=cfg.offense_pool_scale)
        updates["o_line_pool_share"] = st.number_input("O-Line-Poolanteil", value=cfg.o_line_pool_share, format="%.4f")
        updates["pos_multiplier_tackle"] = st.number_input("Positions-Multiplikator Tackle", value=cfg.pos_multiplier_tackle)
        updates["pos_multiplier_guard_center"] = st.number_input("Positions-Multiplikator Guard/Center", value=cfg.pos_multiplier_guard_center)
        updates["pos_multiplier_fullback"] = st.number_input("Positions-Multiplikator Fullback", value=cfg.pos_multiplier_fullback)
        updates["pos_multiplier_tight_end"] = st.number_input("Positions-Multiplikator Tight End", value=cfg.pos_multiplier_tight_end)
        updates["games_started_weight_oline"] = st.number_input("Gewicht Games Started (O-Line)", value=cfg.games_started_weight_oline)

    with st.sidebar.expander("Offense: Skill Positions"):
        updates["rusher_pool_base_share"] = st.number_input("Rusher-Pool Basisanteil", value=cfg.rusher_pool_base_share)
        updates["rusher_pool_reference_ratio"] = st.number_input("Liga-Referenz Rush/Total-Yards", value=cfg.rusher_pool_reference_ratio)
        updates["passer_share_of_remainder"] = st.number_input("Passer-Anteil am Rest-Pool", value=cfg.passer_share_of_remainder)
        updates["receiver_share_of_remainder"] = st.number_input("Receiver-Anteil am Rest-Pool", value=cfg.receiver_share_of_remainder)
        updates["rb_min_carries_for_efficiency"] = st.number_input("Min. Carries fuer RB-Effizienzbonus", value=cfg.rb_min_carries_for_efficiency, step=1)
        updates["rb_efficiency_bonus_mult"] = st.number_input("RB-Effizienzbonus-Multiplikator", value=cfg.rb_efficiency_bonus_mult)
        updates["rb_efficiency_penalty_mult"] = st.number_input("RB-Effizienzmalus-Multiplikator", value=cfg.rb_efficiency_penalty_mult)
        updates["qb_min_attempts_for_efficiency"] = st.number_input("Min. Attempts fuer QB-Effizienzbonus", value=cfg.qb_min_attempts_for_efficiency, step=1)
        updates["qb_efficiency_bonus_mult"] = st.number_input("QB-Effizienzbonus-Multiplikator", value=cfg.qb_efficiency_bonus_mult)
        updates["qb_efficiency_penalty_mult"] = st.number_input("QB-Effizienzmalus-Multiplikator", value=cfg.qb_efficiency_penalty_mult)

    with st.sidebar.expander("Defense"):
        updates["front_seven_share"] = st.number_input("Front-Seven-Poolanteil", value=cfg.front_seven_share, format="%.4f")
        updates["secondary_share"] = st.number_input("Secondary-Poolanteil", value=cfg.secondary_share, format="%.4f")
        updates["games_started_weight_defense"] = st.number_input("Gewicht Games Started (Defense)", value=cfg.games_started_weight_defense)
        updates["sack_weight"] = st.number_input("Gewicht Sack", value=cfg.sack_weight)
        updates["fumble_recovery_weight"] = st.number_input("Gewicht Fumble Recovery", value=cfg.fumble_recovery_weight)
        updates["interception_weight"] = st.number_input("Gewicht Interception", value=cfg.interception_weight)
        updates["defensive_td_weight"] = st.number_input("Gewicht Defensive TD", value=cfg.defensive_td_weight)
        updates["tackle_constant_dl"] = st.number_input("Tackle-Konstante DL", value=cfg.tackle_constant_dl)
        updates["tackle_constant_lb"] = st.number_input("Tackle-Konstante LB", value=cfg.tackle_constant_lb)
        updates["tackle_constant_db"] = st.number_input("Tackle-Konstante DB", value=cfg.tackle_constant_db)

    with st.sidebar.expander("Special Teams"):
        updates["return_td_av"] = st.number_input("AV pro Return-TD", value=cfg.return_td_av)
        updates["kicker_baseline_av_per_16"] = st.number_input("Kicker-Baseline-AV / 16 Spiele", value=cfg.kicker_baseline_av_per_16)
        updates["kicker_paa_divisor"] = st.number_input("Kicker-PAA-Divisor", value=cfg.kicker_paa_divisor)
        updates["punter_baseline_av_per_16"] = st.number_input("Punter-Baseline-AV / 16 Spiele", value=cfg.punter_baseline_av_per_16)
        updates["punter_yards_divisor"] = st.number_input("Punter-Yards-Divisor", value=cfg.punter_yards_divisor)
        updates["punt_block_penalty_yards"] = st.number_input("Yard-Strafe pro geblocktem Punt", value=cfg.punt_block_penalty_yards)

    with st.sidebar.expander("Naeherungen & Career-AV"):
        updates["games_started_snap_threshold"] = st.slider("Snap-%-Schwelle fuer 'Start'", 0.0, 1.0, cfg.games_started_snap_threshold)
        updates["enable_all_pro_bonus"] = st.checkbox("All-Pro-/Pro-Bowl-Bonus aktivieren (braucht manuelle Datenquelle)", value=cfg.enable_all_pro_bonus)
        updates["full_season_games"] = st.number_input("Spiele pro voller Saison", value=cfg.full_season_games, step=1)
        updates["weighted_career_weight_step"] = st.number_input("Weighted-Career Abstufung je Rang", value=cfg.weighted_career_weight_step)
        updates["weighted_career_max_seasons"] = st.number_input("Max. Saisons in Weighted-Career-AV", value=cfg.weighted_career_max_seasons, step=1)

    new_cfg = dataclasses.replace(cfg, **updates)
    st.session_state.cfg = new_cfg
    return new_cfg


def _database_sidebar(cfg: AVConfig) -> None:
    st.sidebar.header("🗄️ Datenbank-Cache")
    st.sidebar.caption(
        "Rohdaten & berechnete AV-Werte liegen dauerhaft in einer lokalen "
        "SQLite-DB. Eine abgeschlossene Saison wird unter der aktuellen "
        "Variablen-Konfiguration nur einmal gerechnet."
    )
    with st.sidebar.expander("Vergangene Saisons vorladen"):
        col1, col2 = st.columns(2)
        with col1:
            start = st.number_input("Von", min_value=FIRST_AVAILABLE_SEASON, max_value=CURRENT_SEASON, value=CURRENT_SEASON - 9, step=1, key="warm_start")
        with col2:
            end = st.number_input("Bis", min_value=FIRST_AVAILABLE_SEASON, max_value=CURRENT_SEASON, value=CURRENT_SEASON, step=1, key="warm_end")
        force = st.checkbox("Neu berechnen, auch wenn schon gecached", value=False)
        if st.button("▶ Jetzt vorladen"):
            seasons = list(range(int(start), int(end) + 1))
            with st.spinner(f"Lade & berechne {len(seasons)} Saison(en) ..."):
                result = warm_historical_cache(cfg, seasons, force=force)
            st.dataframe(result, use_container_width=True, hide_index=True)

        status = db.cache_status(list(range(int(start), int(end) + 1)))
        st.dataframe(
            status.rename(columns={"season": "Saison", "raw_data_cached": "Rohdaten da", "any_av_cached": "AV gecached"}),
            use_container_width=True, hide_index=True, height=200,
        )

    if st.sidebar.button("🗑️ Kompletten Cache loeschen"):
        db.clear_all()
        st.cache_data.clear()
        st.sidebar.success("Cache geleert.")


def _leaderboard_tab(cfg: AVConfig):
    st.subheader("Saison-Rangliste")
    col1, col2 = st.columns([1, 3])
    with col1:
        season = st.number_input("Saison", min_value=FIRST_AVAILABLE_SEASON, max_value=CURRENT_SEASON, value=CURRENT_SEASON, step=1, key="lb_season")
    df = _cached_season_av(dataclasses.asdict(cfg), int(season))
    st.dataframe(df.rename(columns={"player_name": "Spieler", "team": "Team", "av": "AV"}), use_container_width=True, height=650)


def _career_tab(cfg: AVConfig):
    st.subheader("Career & Weighted Career AV")
    st.caption(
        "Weighted Career AV = 100% beste Saison + 95% zweitbeste + 90% drittbeste + ... "
        "'AV je Saison' teilt das Ergebnis durch die Anzahl der eingerechneten Saisons "
        "(max. per Konfiguration begrenzt) fuer einen fairen Pro-Saison-Schnitt."
    )
    col1, col2 = st.columns(2)
    with col1:
        start = st.number_input("Von Saison", min_value=FIRST_AVAILABLE_SEASON, max_value=CURRENT_SEASON, value=CURRENT_SEASON - 4, step=1)
    with col2:
        end = st.number_input("Bis Saison", min_value=FIRST_AVAILABLE_SEASON, max_value=CURRENT_SEASON, value=CURRENT_SEASON, step=1)

    if start > end:
        st.error("Startsaison muss vor oder gleich Endsaison liegen.")
        return
    if end - start > 9:
        st.warning("Mehr als 10 Saisons: Erstberechnung kann mehrere Minuten dauern (danach gecached).")

    seasons = tuple(range(int(start), int(end) + 1))
    multi = _cached_multi_season(dataclasses.asdict(cfg), seasons)
    wc = weighted_career_av(cfg, multi)
    st.dataframe(
        wc.rename(columns={
            "player_name": "Spieler", "career_av": "Career AV", "weighted_career_av": "Weighted Career AV",
            "seasons_played": "Saisons gespielt", "seasons_counted": "Saisons eingerechnet",
            "weighted_av_per_season": "Weighted AV / Saison",
        }),
        use_container_width=True, height=650,
    )


def _live_tab(cfg: AVConfig):
    st.subheader("Laufende Saison: Stand & Hochrechnung")
    col1, col2 = st.columns(2)
    with col1:
        season = st.number_input("Saison", min_value=FIRST_AVAILABLE_SEASON, max_value=CURRENT_SEASON + 1, value=CURRENT_SEASON + 1, step=1, key="live_season")
    with col2:
        week = st.slider("Bis einschliesslich Woche", min_value=1, max_value=22, value=8)

    tab_a, tab_b = st.columns(2)
    with tab_a:
        st.markdown(f"**Aktueller Stand (durch Woche {week})**")
        try:
            df_now = _cached_partial_season(dataclasses.asdict(cfg), int(season), int(week))
            st.dataframe(df_now.rename(columns={"player_name": "Spieler", "team": "Team", "av": "AV"}), use_container_width=True, height=600)
        except Exception as e:
            st.error(f"Keine Daten fuer diese Saison/Woche gefunden: {e}")
    with tab_b:
        st.markdown(f"**Hochrechnung auf volle Saison (Pace ab Woche {week})**")
        try:
            df_proj = _cached_projection(dataclasses.asdict(cfg), int(season), int(week))
            st.dataframe(df_proj.rename(columns={"player_name": "Spieler", "team": "Team", "av": "AV"}), use_container_width=True, height=600)
        except Exception as e:
            st.error(f"Keine Daten fuer diese Saison/Woche gefunden: {e}")


def main():
    st.title("🏈 NFL Approximate Value Tracker")
    st.caption(
        "Nachbau der Pro-Football-Reference-AV-Methodik auf Basis kostenloser nflverse-Daten "
        "(nfl_data_py). Post-Game-Aktualisierung, keine Echtzeit-In-Game-Werte."
    )

    cfg = _config_sidebar()
    _database_sidebar(cfg)

    tab1, tab2, tab3 = st.tabs(["📊 Saison-Rangliste", "🏆 Career / Weighted Career", "🔴 Laufende Saison"])
    with tab1:
        _leaderboard_tab(cfg)
    with tab2:
        _career_tab(cfg)
    with tab3:
        _live_tab(cfg)

    with st.expander("ℹ️ Bekannte Datenluecken (freie Quellen)"):
        st.markdown(
            "- **Games Started** wird ueber einen Snap-%-Schwellenwert approximiert "
            "(PFRs eigentliche Start-Flags sind ueber freie APIs nicht verfuegbar).\n"
            "- **All-Pro-/Pro-Bowl-Bonus** ist standardmaessig deaktiviert, da es dafuer "
            "keine zuverlaessige freie, aktuelle Datenquelle gibt (nur echte Wahlen, keine "
            "Alternates - siehe README).\n"
            "- **Tackles** werden aus Play-by-Play-Zuordnungen (solo/assist) aggregiert, "
            "nicht aus offiziellen Team-Stats - kann von PFRs Zahlen abweichen.\n"
            "- Historische Datenverfuegbarkeit (nflverse PBP) beginnt 1999, nicht 1960.\n"
            "- Abgeschlossene Saisons werden je Variablen-Konfiguration einmalig berechnet "
            "und in einer lokalen SQLite-DB gecached (siehe Sidebar 'Datenbank-Cache')."
        )


if __name__ == "__main__":
    main()
