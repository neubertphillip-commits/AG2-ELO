"""
Rankings Page - Team & Player Rankings
"""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.database import DatabaseManager
from core.elo_calculator_service import EloCalculatorService
from core.unified_data_loader import UnifiedDataLoader
from variants.with_tournament_context import TournamentContextElo


def show():
    """Display rankings page"""

    st.title("Team & Player Rankings")
    st.markdown("Current ELO ratings and historical performance")

    # Tab selection
    tab1, tab2, tab3 = st.tabs(["Team Rankings", "Player Rankings", "Historical Charts"])

    # === TAB 1: TEAM RANKINGS ===
    with tab1:
        st.subheader("Team Rankings")

        try:
            db = DatabaseManager()
            service = EloCalculatorService(db)

            # ELO Configuration Selection
            st.markdown("---")
            col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])

            with col1:
                variant = st.selectbox(
                    "ELO Variant",
                    ["tournament_context", "dynamic_offset", "scale_factor", "base"],
                    format_func=lambda x: {
                        'tournament_context': 'Tournament Context (Best)',
                        'dynamic_offset': 'Dynamic Regional Offsets',
                        'scale_factor': 'Scale Factor',
                        'base': 'Base ELO'
                    }[x]
                )

            with col2:
                k_factor = st.number_input("K-Factor", min_value=8, max_value=48, value=24, step=4)

            with col3:
                use_scale_factors = st.checkbox("Scale Factors", value=True)

            with col4:
                # Regional Offsets checkbox (disabled for variants that always use it)
                regional_offsets_disabled = variant in ['dynamic_offset', 'tournament_context']
                use_regional_offsets = st.checkbox(
                    "Regional Offsets",
                    value=regional_offsets_disabled,
                    disabled=regional_offsets_disabled,
                    help="Adjust ratings based on regional strength (always enabled for Dynamic Offset and Tournament Context)"
                )

            with col5:
                if st.button("Recalculate", type="primary"):
                    st.session_state['force_recalc'] = True

            # ELO Variant Descriptions
            with st.expander("What are these ELO variants?", expanded=False):
                st.markdown("""
                ### ELO Calculation Methods

                #### 1. Base ELO
                **Simplest method** - Classic ELO rating system
                - Fixed K-factor for all matches
                - No adjustments for match context
                - No regional considerations
                - **Use when:** You want the simplest, most transparent system
                - **Accuracy:** ~69.85%

                #### 2. Scale Factor
                **Match closeness matters** - Adjusts for score difference
                - 3-0 win = Full K-factor (dominant performance)
                - 3-2 win = Reduced K-factor (close match, less certain)
                - Prevents overreacting to lucky wins
                - **Use when:** You want to reward dominant victories more than close ones
                - **Accuracy:** ~70.46%

                #### 3. Dynamic Regional Offsets
                **Cross-regional learning** - Adjusts for regional strength
                - Tracks regional power automatically from international matches
                - LCK beats LEC → LCK gets bonus, LEC gets penalty
                - Updates dynamically as more data comes in
                - **Use when:** You want to compare teams across regions fairly
                - **Accuracy:** ~70.46%

                #### 4. Tournament Context (BEST) ⭐
                **Context-aware** - Different stakes = different K-factors
                - Worlds/MSI: K=32 (high stakes, more rating change)
                - Playoffs: K=28 (important matches)
                - Regular Season: K=24 (standard)
                - Combines Scale Factor + Dynamic Offsets
                - **Use when:** You want the most accurate predictions
                - **Accuracy:** ~70.56%

                ### Parameters

                **K-Factor:** Controls how much ratings change per match
                - Higher K (32-48): Ratings change quickly, volatile
                - Medium K (20-28): Balanced, recommended
                - Lower K (8-16): Ratings change slowly, stable

                **Scale Factors:** Match closeness adjustment
                - Enabled: 3-0 wins count more than 3-2 wins
                - Disabled: All wins count equally
                """)

            # Calculate or load ELOs
            force_recalc = st.session_state.get('force_recalc', False)
            if force_recalc:
                st.session_state['force_recalc'] = False

            with st.spinner('Loading ELO ratings...'):
                config_id, team_elos = service.calculate_or_load_elos(
                    variant=variant,
                    k_factor=k_factor,
                    use_scale_factors=use_scale_factors,
                    use_regional_offsets=use_regional_offsets,
                    force_recalculate=force_recalc
                )

            if not team_elos:
                st.warning("No ELO data available. Import matches first!")
                return

            st.success(f"Loaded {len(team_elos)} teams")

            # Show explanation if using regional offsets
            if (variant in ['dynamic_offset', 'tournament_context']) or use_regional_offsets:
                st.info("""
                **Regional Offsets Active:** ELO values shown include regional strength adjustments.
                - **ELO**: Final rating (Base ELO + Regional Offset)
                - **Base ELO**: Raw ELO without regional adjustment
                - **Regional Offset**: Points added/subtracted based on regional strength

                Example: LCK team with Base ELO 1500 + LCK Offset +83 = Final ELO 1583
                """)

            # Filters
            st.markdown("---")
            col1, col2, col3 = st.columns(3)

            with col1:
                # Get unique regions
                cursor = db.conn.cursor()
                cursor.execute("SELECT DISTINCT region FROM teams WHERE region IS NOT NULL ORDER BY region")
                regions = [r[0] for r in cursor.fetchall()]

                region_filter = st.selectbox(
                    "Filter by Region",
                    ["All Regions"] + regions
                )

            with col2:
                limit = st.number_input("Show Top N Teams", min_value=5, max_value=100, value=20, step=5)

            with col3:
                sort_by = st.selectbox(
                    "Sort By",
                    ["ELO Rating", "Team Name", "Region", "Matches Played"]
                )

            # Get team regions from database
            cursor.execute("SELECT name, region FROM teams")
            db_team_regions = {row[0]: row[1] for row in cursor.fetchall()}

            # Use RegionMapper as fallback for teams without region in DB
            from core.region_mapper import RegionMapper
            region_mapper = RegionMapper()

            team_regions = {}
            for team in team_elos.keys():
                # Try database first, then RegionMapper fallback
                db_region = db_team_regions.get(team)
                if db_region and db_region != 'Unknown':
                    team_regions[team] = db_region
                else:
                    team_regions[team] = region_mapper.get_region(team, detailed=False)

            # Check if this variant uses regional offsets
            using_offsets = (variant in ['dynamic_offset', 'tournament_context']) or use_regional_offsets

            # Create rankings DataFrame
            rankings_data = []
            for team, stats in team_elos.items():
                row = {
                    'Team': team,
                    'ELO': int(stats['elo']),
                    'Region': team_regions.get(team, 'Unknown'),
                    'Matches': stats['matches'],
                    'Wins': stats['wins'],
                    'Losses': stats['losses'],
                    'Win Rate': f"{stats['wins'] / max(stats['matches'], 1) * 100:.1f}%"
                }

                # Add offset columns if regional offsets are enabled
                if using_offsets and stats.get('base_elo') is not None:
                    row['Base ELO'] = int(stats['base_elo'])
                    row['Regional Offset'] = f"{stats.get('regional_offset', 0):+.1f}"

                rankings_data.append(row)

            rankings_df = pd.DataFrame(rankings_data)

            # Apply region filter
            if region_filter != "All Regions":
                rankings_df = rankings_df[rankings_df['Region'] == region_filter]

            # Sort
            if sort_by == "ELO Rating":
                rankings_df = rankings_df.sort_values('ELO', ascending=False)
            elif sort_by == "Team Name":
                rankings_df = rankings_df.sort_values('Team')
            elif sort_by == "Region":
                rankings_df = rankings_df.sort_values(['Region', 'ELO'], ascending=[True, False])
            elif sort_by == "Matches Played":
                rankings_df = rankings_df.sort_values('Matches', ascending=False)

            # Limit results
            rankings_df = rankings_df.head(limit)

            # Add rank column
            rankings_df.insert(0, 'Rank', range(1, len(rankings_df) + 1))

            # Display
            st.dataframe(
                rankings_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Rank": st.column_config.NumberColumn(format="%d"),
                    "ELO": st.column_config.NumberColumn(format="%d"),
                    "Matches": st.column_config.NumberColumn(format="%d"),
                    "Wins": st.column_config.NumberColumn(format="%d"),
                    "Losses": st.column_config.NumberColumn(format="%d"),
                }
            )

            # Top 5 highlight
            st.markdown("---")
            st.subheader("🏅 Top 5 Teams")

            top5 = rankings_df.head(5)
            cols = st.columns(5)

            for idx, (_, row) in enumerate(top5.iterrows()):
                with cols[idx]:
                    medal = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][idx]
                    st.markdown(f"### {medal}")
                    st.markdown(f"**{row['Team']}**")
                    st.metric("ELO", row['ELO'])
                    st.caption(f"{row['Region']} | {row['Win Rate']}")

            db.close()

        except Exception as e:
            st.error(f"Error loading rankings: {str(e)}")

    # === TAB 2: PLAYER RANKINGS ===
    with tab2:
        st.subheader("👤 Player Rankings")

        try:
            db = DatabaseManager()

            # Check if player data exists
            cursor = db.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM players")
            player_count = cursor.fetchone()[0]

            if player_count == 0:
                st.info("""
                **Player rankings coming soon!**

                Currently, the system tracks team-level ELO. Player-level ratings require:
                - Complete roster data
                - Player participation tracking
                - Individual performance metrics

                To enable player rankings:
                1. Import player data via API
                2. Run player ELO calculation
                3. View individual player ratings here

                See `docs/SCIENTIFIC_BLOG.md` Section 7.2 for details on player-level ELO implementation.
                """)
            else:
                # Display player data (if available)
                query = """
                    SELECT
                        p.name,
                        p.role,
                        COUNT(mp.match_id) as matches_played
                    FROM players p
                    LEFT JOIN match_players mp ON p.id = mp.id
                    GROUP BY p.id
                    ORDER BY matches_played DESC
                    LIMIT 50
                """

                cursor.execute(query)
                players = cursor.fetchall()

                if players:
                    df_players = pd.DataFrame(players, columns=[
                        'Player', 'Role', 'Matches Played'
                    ])

                    st.dataframe(
                        df_players,
                        use_container_width=True,
                        hide_index=True
                    )

                    st.caption("Note: Player ELO calculations not yet implemented. Showing participation data only.")
                else:
                    st.info("No player data found.")

            db.close()

        except Exception as e:
            st.error(f"Error loading player data: {str(e)}")

    # === TAB 3: HISTORICAL CHARTS ===
    with tab3:
        st.subheader("📈 Historical ELO Charts")

        try:
            db = DatabaseManager()

            # Team selection
            cursor = db.conn.cursor()
            cursor.execute("SELECT name FROM teams ORDER BY name")
            all_teams = [row[0] for row in cursor.fetchall()]

            if not all_teams:
                st.warning("No teams found. Import data first!")
                db.close()
                return

            # Select teams to chart
            selected_teams = st.multiselect(
                "Select teams to visualize (max 5)",
                all_teams,
                default=all_teams[:min(3, len(all_teams))],
                max_selections=5
            )

            if not selected_teams:
                st.info("Select at least one team to view historical ELO chart.")
                db.close()
                return

            # Load matches
            loader = UnifiedDataLoader()
            matches_df = loader.load_matches(source='auto')

            if matches_df.empty:
                st.warning("No match data available.")
                db.close()
                return

            # Calculate ELO history for selected teams
            st.info("📊 Calculating ELO history...")

            elo = TournamentContextElo(k_factor=24)
            team_elos = {}
            elo_history = {team: [] for team in selected_teams}
            date_history = {team: [] for team in selected_teams}

            # Sort by date
            matches_df = matches_df.sort_values('date')

            for _, match in matches_df.iterrows():
                team1 = match['team1']
                team2 = match['team2']
                match_date = pd.to_datetime(match['date'])

                # Initialize teams if not seen before
                if team1 not in team_elos:
                    team_elos[team1] = 1500
                if team2 not in team_elos:
                    team_elos[team2] = 1500

                # Determine tournament context
                tournament = match.get('tournament', '') or ''
                if tournament and isinstance(tournament, str):
                    tournament_lower = tournament.lower()
                    if 'world' in tournament_lower:
                        context = 'worlds'
                    elif 'playoff' in tournament_lower or 'final' in tournament_lower:
                        context = 'playoffs'
                    else:
                        context = 'regular_season'
                else:
                    context = 'regular_season'

                # Get current ratings
                elo1_before = team_elos[team1]
                elo2_before = team_elos[team2]

                # Determine winner
                winner = match['winner']
                score1 = 1 if winner == team1 else 0
                score2 = 1 if winner == team2 else 0

                # Update ratings
                elo1_after, elo2_after = elo.update_ratings_with_context(
                    elo1_before, elo2_before, score1, score2, context
                )

                team_elos[team1] = elo1_after
                team_elos[team2] = elo2_after

                # Record history for selected teams
                if team1 in selected_teams:
                    elo_history[team1].append(elo1_after)
                    date_history[team1].append(match_date)

                if team2 in selected_teams:
                    elo_history[team2].append(elo2_after)
                    date_history[team2].append(match_date)

            # Create chart DataFrame
            chart_data = pd.DataFrame()

            for team in selected_teams:
                if elo_history[team]:  # Only if team has data
                    team_df = pd.DataFrame({
                        'Date': date_history[team],
                        'ELO': elo_history[team],
                        'Team': team
                    })
                    chart_data = pd.concat([chart_data, team_df], ignore_index=True)

            if not chart_data.empty:
                # Display line chart
                st.line_chart(
                    chart_data,
                    x='Date',
                    y='ELO',
                    color='Team',
                    use_container_width=True
                )

                # Show current ELO values
                st.markdown("---")
                st.subheader("📊 Current ELO Values")

                cols = st.columns(len(selected_teams))
                for idx, team in enumerate(selected_teams):
                    with cols[idx]:
                        current_elo = team_elos.get(team, 1500)
                        st.metric(team, int(current_elo))

                # Export option
                st.markdown("---")
                if st.button("📥 Export Chart Data"):
                    csv = chart_data.to_csv(index=False)
                    st.download_button(
                        label="Download CSV",
                        data=csv,
                        file_name=f"elo_history_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
            else:
                st.warning("No data available for selected teams.")

            db.close()

        except Exception as e:
            st.error(f"Error generating charts: {str(e)}")


if __name__ == "__main__":
    show()
