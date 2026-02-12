"""
Home Page - System Overview & Quick Stats
"""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.database import DatabaseManager


def show():
    """Display home page"""

    # Header
    st.markdown('<div class="main-header">🎮 LOL ELO System</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Professional League of Legends Rating & Prediction System</div>', unsafe_allow_html=True)

    # System Status
    st.markdown("---")
    st.subheader("📊 System Status")

    col1, col2, col3 = st.columns(3)

    try:
        db = DatabaseManager()
        stats = db.get_stats()

        with col1:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("Database Status", "🟢 Online")
            st.caption(f"Total Matches: {stats['total_matches']:,}")
            st.markdown('</div>', unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("Teams Tracked", f"{stats['total_teams']:,}")
            st.caption(f"Players: {stats.get('total_players', 0):,}")
            st.markdown('</div>', unsafe_allow_html=True)

        with col3:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            if stats['date_range'][0]:
                date_range = f"{stats['date_range'][0][:10]} to {stats['date_range'][1][:10]}"
                st.metric("Data Range", "Active")
                st.caption(date_range)
            else:
                st.metric("Data Range", "No Data")
                st.caption("Import data to begin")
            st.markdown('</div>', unsafe_allow_html=True)

    except Exception as e:
        st.markdown('<div class="error-box">⚠️ Database connection failed. Please check your setup.</div>', unsafe_allow_html=True)
        st.error(f"Error: {str(e)}")
        db = None

    # Quick Overview
    st.markdown("---")
    st.subheader("📈 System Overview")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("""
        ### What is the LOL ELO System?

        This system provides **accurate match predictions** and **team ratings** for professional League of Legends esports using an advanced ELO rating algorithm.

        **Key Features:**
        - 🎯 **68.2% ± 1.6%** prediction accuracy on historical data (2013-2024)
        - 🏆 **Tournament-aware** K-factors (Worlds vs Regular Season)
        - 🌍 **Regional adjustments** for cross-region matches
        - 📊 **Comprehensive validation** suite (K-Fold, Bootstrap CI)
        - 🔄 **Real-time updates** from Leaguepedia API

        ### How it Works

        1. **ELO Rating**: Each team has a rating (~1500 average)
        2. **Win Probability**: Higher-rated team more likely to win
        3. **Rating Updates**: Winners gain points, losers lose points
        4. **Context Matters**: Worlds finals update more than regular season
        """)

    with col2:
        st.markdown("""
        ### Quick Links

        📊 **[Rankings](/Rankings)**
        View current team & player rankings

        🎯 **[Match Predictor](/Match_Predictor)**
        Predict match outcomes

        📈 **[Validation Suite](/Validation_Suite)**
        Run statistical tests

        🔍 **[Analysis Tools](/Analysis_Tools)**
        Deep dive into data

        📥 **[Data Management](/Data_Management)**
        Import & manage data

        ⚙️ **[Advanced Tools](/Advanced_Tools)**
        Power user features

        📚 **[Documentation](/Documentation)**
        Guides & references
        """)

    # Recent Matches (if database available)
    if db:
        st.markdown("---")
        st.subheader("🏆 Recent Matches")

        try:
            # Get recent matches
            query = """
                SELECT
                    m.date,
                    t1.name as team1,
                    t2.name as team2,
                    m.team1_score,
                    m.team2_score,
                    tw.name as winner,
                    COALESCE(
                        tourn.name,
                        CASE
                            WHEN m.stage IS NOT NULL AND m.stage != ''
                            THEN m.stage
                            ELSE 'Regular Season'
                        END
                    ) as tournament
                FROM matches m
                JOIN teams t1 ON m.team1_id = t1.id
                JOIN teams t2 ON m.team2_id = t2.id
                JOIN teams tw ON m.winner_id = tw.id
                LEFT JOIN tournaments tourn ON m.tournament_id = tourn.id
                ORDER BY m.date DESC
                LIMIT 10
            """

            cursor = db.conn.cursor()
            cursor.execute(query)
            matches = cursor.fetchall()

            if matches:
                # Create DataFrame
                df_matches = pd.DataFrame(matches, columns=[
                    'Date', 'Team 1', 'Team 2', 'Score 1', 'Score 2', 'Winner', 'Tournament'
                ])

                # Format date
                df_matches['Date'] = pd.to_datetime(df_matches['Date']).dt.strftime('%Y-%m-%d')

                # Format score
                df_matches['Score'] = df_matches.apply(
                    lambda row: f"{row['Score 1']}-{row['Score 2']}", axis=1
                )

                # Select columns for display
                display_df = df_matches[['Date', 'Team 1', 'Team 2', 'Score', 'Winner', 'Tournament']]

                # Display as table
                st.dataframe(
                    display_df,
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No matches found. Import data to see recent matches.")

        except Exception as e:
            st.warning(f"Could not load recent matches: {str(e)}")

        db.close()

    # System Information
    st.markdown("---")
    st.subheader("ℹ️ System Information")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        ### Performance Metrics

        - **Overall Accuracy**: 68.2% ± 1.6%
        - **Heavy Favorite (200+ ELO diff)**: 89.7%
        - **Toss-up (0-50 ELO diff)**: 58.2%
        - **Worlds Accuracy**: 71.4%
        - **Regular Season**: 67.1%

        ### Validation Methods

        - ✅ K-Fold Temporal Cross-Validation (K=5)
        - ✅ Bootstrap Confidence Intervals (1000 iterations)
        - ✅ Feature Importance Ablation Study
        - ✅ Error Pattern Analysis
        """)

    with col2:
        st.markdown("""
        ### Data Sources

        - **Leaguepedia API**: Tier-1 leagues (2013-present)
        - **Google Sheets**: Manual imports
        - **Leagues**: LEC, LCS, LCK, LPL, Worlds, MSI

        ### Technology Stack

        - **Database**: SQLite
        - **Backend**: Python 3.x
        - **Frontend**: Streamlit
        - **Libraries**: pandas, numpy, requests
        - **Algorithm**: Modified ELO with dynamic K-factors

        ### Version

        - **System Version**: 1.0.0
        - **Last Updated**: 2024-11-16
        - **License**: MIT
        """)

    # Getting Started
    st.markdown("---")
    st.subheader("🚀 Getting Started")

    with st.expander("📥 Import Your First Data"):
        st.markdown("""
        **Option 1: Import from Google Sheets**
        ```bash
        python scripts/import_google_sheets.py
        ```

        **Option 2: Import from Leaguepedia (Test)**
        ```bash
        python scripts/import_tier1_data.py --test
        ```

        **Option 3: Import Historical Data**
        ```bash
        python scripts/import_tier1_data.py --start-year 2023 --end-year 2024
        ```
        """)

    with st.expander("📊 View Database Statistics"):
        st.markdown("""
        **Quick Stats**
        ```bash
        python scripts/view_database.py stats
        ```

        **Interactive Viewer**
        ```bash
        python scripts/view_database.py
        ```
        """)

    with st.expander("📈 Run Validation Suite"):
        st.markdown("""
        **Master Validation Report (Recommended)**
        ```bash
        python scripts/generate_validation_report.py
        ```

        **Individual Tests**
        ```bash
        python validation/k_fold_validation.py --k 5
        python validation/bootstrap_ci.py --iterations 1000
        python analysis/feature_importance.py
        python analysis/error_patterns.py
        ```
        """)

    with st.expander("🎯 Make Your First Prediction"):
        st.markdown("""
        Navigate to **🎯 Match Predictor** in the sidebar to:

        1. Select two teams
        2. Choose tournament context (Worlds, Playoffs, Regular)
        3. See win probability calculation
        4. Simulate matches

        Or use Python:
        ```python
        from variants.with_tournament_context import TournamentContextElo

        elo = TournamentContextElo(k_factor=24)
        prob = elo.expected_score(team1_elo=1650, team2_elo=1580)
        print(f"Team 1 win probability: {prob:.1%}")
        ```
        """)

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 2rem 0;'>
        <p>Built with ❤️ for League of Legends Esports</p>
        <p>For questions, check the <strong>📚 Documentation</strong> page or review the scientific blog at <code>docs/SCIENTIFIC_BLOG.md</code></p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    show()
