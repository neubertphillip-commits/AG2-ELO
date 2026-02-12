"""
Match Predictor Page - Predict match outcomes
"""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.database import DatabaseManager
from core.elo_calculator_service import EloCalculatorService


def show():
    """Display match predictor page"""

    st.title("Match Outcome Predictor")
    st.markdown("Predict League of Legends match outcomes using ELO ratings")

    # ELO Configuration Selection
    st.markdown("---")
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

    with col1:
        variant = st.selectbox(
            "ELO Variant",
            ["tournament_context", "dynamic_offset", "scale_factor", "base"],
            format_func=lambda x: {
                'tournament_context': 'Tournament Context (Best)',
                'dynamic_offset': 'Dynamic Regional Offsets',
                'scale_factor': 'Scale Factor',
                'base': 'Base ELO'
            }[x],
            key="predictor_variant"
        )

    with col2:
        k_factor = st.number_input("K-Factor", min_value=8, max_value=48, value=24, step=4, key="predictor_k")

    with col3:
        use_scale_factors = st.checkbox("Scale Factors", value=True, key="predictor_scale")

    with col4:
        # Regional Offsets checkbox (disabled for variants that always use it)
        regional_offsets_disabled = variant in ['dynamic_offset', 'tournament_context']
        use_regional_offsets = st.checkbox(
            "Regional Offsets",
            value=regional_offsets_disabled,
            disabled=regional_offsets_disabled,
            help="Adjust ratings based on regional strength (always enabled for Dynamic Offset and Tournament Context)",
            key="predictor_regional"
        )

    # ELO Variant Descriptions
    with st.expander("What are these ELO variants?", expanded=False):
        st.markdown("""
        ### ELO Calculation Methods

        **Base ELO:** Classic ELO - Simple and transparent (~69.85% accuracy)

        **Scale Factor:** Rewards dominant victories more than close wins (~70.46% accuracy)

        **Dynamic Regional Offsets:** Adjusts for regional strength based on international matches (~70.46% accuracy)

        **Tournament Context (BEST):** Adapts K-factor based on tournament importance (~70.56% accuracy)

        See the Rankings page for detailed explanations.
        """)

    # Load current ELOs
    with st.spinner("Loading current team ratings..."):
        try:
            db = DatabaseManager()
            service = EloCalculatorService(db)

            config_id, team_ratings = service.calculate_or_load_elos(
                variant=variant,
                k_factor=k_factor,
                use_scale_factors=use_scale_factors,
                use_regional_offsets=use_regional_offsets
            )

            # Convert to simple dict (elo values only)
            team_elos = {team: stats['elo'] for team, stats in team_ratings.items()}
        except Exception as e:
            st.error(f"Error loading ELOs: {str(e)}")
            team_elos = {}

    if not team_elos:
        st.warning("No team data available. Import matches first!")
        st.markdown("""
        **To get started:**
        1. Navigate to **📥 Data Management**
        2. Import data from Google Sheets or Leaguepedia
        3. Return here to make predictions
        """)
        return

    # Sort teams by ELO
    sorted_teams = sorted(team_elos.items(), key=lambda x: x[1], reverse=True)
    team_names = [team for team, _ in sorted_teams]

    st.markdown("---")

    # === MATCH PREDICTION ===
    st.subheader("⚔️ Match Prediction")

    col1, col2, col3 = st.columns([2, 1, 2])

    with col1:
        # Find index of previously selected team, or default to 0
        default_team1_idx = 0
        if 'team1_select' in st.session_state and st.session_state.team1_select in team_names:
            default_team1_idx = team_names.index(st.session_state.team1_select)

        team1 = st.selectbox(
            "Team 1",
            team_names,
            index=default_team1_idx,
            key="team1_select"
        )
        team1_elo = team_elos.get(team1, 1500)
        st.metric("Current ELO", int(team1_elo))

    with col2:
        st.markdown("<div style='text-align: center; padding-top: 2rem;'><h2>VS</h2></div>", unsafe_allow_html=True)

    with col3:
        # Find index of previously selected team, or default to 1
        default_team2_idx = min(1, len(team_names) - 1)
        if 'team2_select' in st.session_state and st.session_state.team2_select in team_names:
            default_team2_idx = team_names.index(st.session_state.team2_select)

        team2 = st.selectbox(
            "Team 2",
            team_names,
            index=default_team2_idx,
            key="team2_select"
        )
        team2_elo = team_elos.get(team2, 1500)
        st.metric("Current ELO", int(team2_elo))

    # Tournament context
    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        tournament_context = st.selectbox(
            "Tournament Context",
            ["Regular Season", "Playoffs", "Worlds Championship", "MSI"],
            help="Different contexts use different K-factors for rating updates"
        )

    with col2:
        series_format = st.selectbox(
            "Series Format",
            ["Best of 1", "Best of 3", "Best of 5"],
            help="Series format (informational only, doesn't affect prediction)"
        )

    # Map context to internal format
    context_map = {
        "Regular Season": "regular_season",
        "Playoffs": "playoffs",
        "Worlds Championship": "worlds",
        "MSI": "msi"
    }
    context = context_map[tournament_context]

    # Calculate prediction
    st.markdown("---")
    st.subheader("📊 Prediction Results")

    # Calculate expected probabilities using standard ELO formula
    prob_team1 = 1 / (1 + 10 ** ((team2_elo - team1_elo) / 400))
    prob_team2 = 1 - prob_team1

    # Display probabilities
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"### {team1}")
        st.markdown(f"<div style='font-size: 3rem; font-weight: bold; color: {'#2ecc71' if prob_team1 > 0.5 else '#e74c3c'};'>{prob_team1:.1%}</div>", unsafe_allow_html=True)
        st.caption("Win Probability")

        if prob_team1 > 0.5:
            st.success(f"✓ Favored to win")
        else:
            st.info(f"Underdog")

    with col2:
        st.markdown(f"### {team2}")
        st.markdown(f"<div style='font-size: 3rem; font-weight: bold; color: {'#2ecc71' if prob_team2 > 0.5 else '#e74c3c'};'>{prob_team2:.1%}</div>", unsafe_allow_html=True)
        st.caption("Win Probability")

        if prob_team2 > 0.5:
            st.success(f"✓ Favored to win")
        else:
            st.info(f"Underdog")

    # Additional insights
    st.markdown("---")
    st.subheader("🔍 Match Insights")

    elo_diff = abs(team1_elo - team2_elo)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("ELO Difference", f"{int(elo_diff)}")
        if elo_diff < 50:
            match_type = "Toss-up"
            color = "orange"
        elif elo_diff < 100:
            match_type = "Slight Favorite"
            color = "blue"
        elif elo_diff < 150:
            match_type = "Clear Favorite"
            color = "green"
        else:
            match_type = "Heavy Favorite"
            color = "darkgreen"

        st.markdown(f"<div style='color: {color}; font-weight: bold;'>{match_type}</div>", unsafe_allow_html=True)

    with col2:
        # Get K-factor for context
        k_factors = elo.tournament_k_factors
        k = k_factors.get(context, 24)
        st.metric("K-Factor", k)
        st.caption(f"Rating change magnitude for {tournament_context}")

    with col3:
        # Expected rating change
        expected_change = k * (1 - prob_team1) if prob_team1 > 0.5 else k * prob_team1
        st.metric("Expected Rating Change", f"±{int(expected_change)}")
        st.caption("If favorite wins")

    # Historical matchup (if available)
    st.markdown("---")
    st.subheader("📜 Head-to-Head History")

    try:
        loader = UnifiedDataLoader()
        matches_df = loader.load_matches(source='auto')

        h2h = matches_df[
            ((matches_df['team1'] == team1) & (matches_df['team2'] == team2)) |
            ((matches_df['team1'] == team2) & (matches_df['team2'] == team1))
        ]

        if not h2h.empty:
            # Count wins
            team1_wins = len(h2h[h2h['winner'] == team1])
            team2_wins = len(h2h[h2h['winner'] == team2])
            total_matches = len(h2h)

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric(f"{team1} Wins", team1_wins)

            with col2:
                st.metric("Total Matches", total_matches)

            with col3:
                st.metric(f"{team2} Wins", team2_wins)

            # Show recent matches
            st.markdown("**Recent Matches:**")
            recent_h2h = h2h.sort_values('date', ascending=False).head(5)

            for _, match in recent_h2h.iterrows():
                date = pd.to_datetime(match['date']).strftime('%Y-%m-%d')
                score = f"{match['team1_score']}-{match['team2_score']}"
                winner = match['winner']
                tournament = match.get('tournament', 'Unknown')

                st.caption(f"**{date}** | {match['team1']} vs {match['team2']} | {score} | Winner: **{winner}** | {tournament}")

        else:
            st.info(f"No previous matches found between {team1} and {team2}")

    except Exception as e:
        st.warning(f"Could not load head-to-head data: {str(e)}")

    # === WHAT-IF SCENARIOS ===
    st.markdown("---")
    st.subheader("🔮 What-If Scenarios")

    with st.expander("📈 ELO Simulation"):
        st.markdown("See how ELO ratings would change after this match")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"**If {team1} wins:**")
            elo1_if_win, elo2_if_loss = elo.update_ratings_with_context(
                team1_elo, team2_elo, 1, 0, context
            )
            st.metric(
                f"{team1} New ELO",
                int(elo1_if_win),
                delta=int(elo1_if_win - team1_elo)
            )
            st.metric(
                f"{team2} New ELO",
                int(elo2_if_loss),
                delta=int(elo2_if_loss - team2_elo)
            )

        with col2:
            st.markdown(f"**If {team2} wins:**")
            elo1_if_loss, elo2_if_win = elo.update_ratings_with_context(
                team1_elo, team2_elo, 0, 1, context
            )
            st.metric(
                f"{team1} New ELO",
                int(elo1_if_loss),
                delta=int(elo1_if_loss - team1_elo)
            )
            st.metric(
                f"{team2} New ELO",
                int(elo2_if_win),
                delta=int(elo2_if_win - team2_elo)
            )

    with st.expander("🎲 Monte Carlo Simulation"):
        st.markdown("Simulate 1000 matches to see outcome distribution")

        if st.button("Run Simulation"):
            import numpy as np

            simulations = 1000
            team1_wins = 0

            for _ in range(simulations):
                if np.random.random() < prob_team1:
                    team1_wins += 1

            team2_wins = simulations - team1_wins

            st.markdown(f"**Results from {simulations} simulated matches:**")

            col1, col2 = st.columns(2)

            with col1:
                st.metric(f"{team1} Wins", team1_wins)
                st.progress(team1_wins / simulations)

            with col2:
                st.metric(f"{team2} Wins", team2_wins)
                st.progress(team2_wins / simulations)

            st.caption(f"Theoretical: {team1} {prob_team1:.1%} vs {team2} {prob_team2:.1%}")

    # === PROBABILITY CALCULATOR ===
    st.markdown("---")
    st.subheader("🧮 Custom Probability Calculator")

    with st.expander("Calculate win probability from custom ELO values"):
        col1, col2 = st.columns(2)

        with col1:
            custom_elo1 = st.number_input(
                "Team 1 ELO",
                min_value=1000,
                max_value=2500,
                value=1500,
                step=10
            )

        with col2:
            custom_elo2 = st.number_input(
                "Team 2 ELO",
                min_value=1000,
                max_value=2500,
                value=1500,
                step=10
            )

        custom_prob1 = elo.expected_score(custom_elo1, custom_elo2)
        custom_prob2 = 1 - custom_prob1

        st.markdown(f"""
        **Win Probabilities:**
        - Team 1 (ELO {custom_elo1}): **{custom_prob1:.2%}**
        - Team 2 (ELO {custom_elo2}): **{custom_prob2:.2%}**
        """)

        # Show formula
        st.markdown("""
        **Formula:**
        ```
        P(Team 1 wins) = 1 / (1 + 10^((ELO2 - ELO1) / 400))
        ```
        """)


if __name__ == "__main__":
    show()
