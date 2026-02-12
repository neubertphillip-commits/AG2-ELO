"""
Documentation Page - Inline help and references
"""

import streamlit as st
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def show():
    """Display documentation page"""

    st.title("📚 Documentation")
    st.markdown("Guides, references, and help resources")

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "🚀 Quick Start",
        "📖 User Guide",
        "🔬 Scientific Documentation",
        "💻 API Reference"
    ])

    # === TAB 1: QUICK START ===
    with tab1:
        st.subheader("🚀 Quick Start Guide")
        st.markdown("Get up and running in 5 minutes")

        st.markdown("""
        ## Welcome to LOL ELO System!

        This guide will help you get started with the system in just a few steps.

        ---

        ### Step 1: Import Your First Data

        Choose one of these options:

        **Option A: Google Sheets (if you have existing data)**
        ```bash
        python scripts/import_google_sheets.py
        ```

        **Option B: Leaguepedia API (recommended for new users)**
        ```bash
        # Quick test import (2-3 minutes)
        python scripts/import_tier1_data.py --test

        # Or import recent data (15-30 minutes)
        python scripts/import_tier1_data.py --start-year 2023 --end-year 2024
        ```

        💡 **Tip:** Use the **📥 Data Management** page in the dashboard to import data with a GUI!

        ---

        ### Step 2: Check Your Data

        Verify the import was successful:

        ```bash
        python scripts/view_database.py stats
        ```

        You should see:
        - Total matches imported
        - Number of teams
        - Date range of data

        ---

        ### Step 3: View Rankings

        Navigate to **📊 Rankings** page to see:
        - Current team ELO ratings
        - Top teams by region
        - Historical ELO charts

        ---

        ### Step 4: Make Your First Prediction

        Navigate to **🎯 Match Predictor** page:
        1. Select two teams
        2. Choose tournament context (Worlds, Playoffs, Regular)
        3. See win probability
        4. Simulate outcomes

        ---

        ### Step 5: Run Validation (Optional but Recommended)

        Validate the model accuracy:

        ```bash
        python scripts/generate_validation_report.py
        ```

        Or use **📈 Validation Suite** page in dashboard.

        View results: `cat reports/validation_report.md`

        ---

        ## What's Next?

        **Explore Features:**
        - 📊 **Rankings**: View current team rankings and ELO history
        - 🎯 **Predictor**: Predict match outcomes
        - 📈 **Validation**: Check model accuracy
        - 🔍 **Analysis**: Deep dive into performance

        **Learn More:**
        - Read the **User Guide** tab for detailed workflows
        - Check **Scientific Documentation** for methodology
        - See **API Reference** for programmatic usage

        **Get Help:**
        - Check troubleshooting in user guide
        - Review command reference: `docs/COMMANDS_GUIDE.md`
        - Read scientific blog: `docs/SCIENTIFIC_BLOG.md`

        ---

        ## Common Tasks

        **Import more data:**
        ```bash
        python scripts/import_tier1_data.py --leagues LEC LCK --start-year 2024
        ```

        **Check for duplicates:**
        ```bash
        python scripts/diagnose_duplicates.py
        ```

        **Export data:**
        ```python
        from core.unified_data_loader import UnifiedDataLoader

        with UnifiedDataLoader() as loader:
            df = loader.load_matches(source='database')
            df.to_csv('export.csv', index=False)
        ```

        **Make predictions in Python:**
        ```python
        from variants.with_tournament_context import TournamentContextElo

        elo = TournamentContextElo(k_factor=24)
        prob = elo.expected_score(team1_elo=1650, team2_elo=1580)
        print(f"Team 1 win probability: {prob:.1%}")
        ```

        ---

        **🎉 You're all set! Start exploring the dashboard.**
        """)

    # === TAB 2: USER GUIDE ===
    with tab2:
        st.subheader("📖 Complete User Guide")
        st.markdown("Comprehensive guide to all features")

        # Check if guide exists
        guide_path = Path("docs/COMMANDS_GUIDE.md")

        if guide_path.exists():
            with open(guide_path, 'r', encoding='utf-8') as f:
                guide_content = f.read()

            # Display with expanders for sections
            st.markdown(guide_content)

            # Download option
            st.markdown("---")
            st.download_button(
                "📥 Download Complete Guide (Markdown)",
                data=guide_content,
                file_name="LOL_ELO_Commands_Guide.md",
                mime="text/markdown"
            )

        else:
            st.warning("User guide not found at `docs/COMMANDS_GUIDE.md`")

            st.info("""
            **Expected location:** `docs/COMMANDS_GUIDE.md`

            The user guide should include:
            - Getting Started
            - Daily Operations
            - Data Import Workflows
            - Database Management
            - Validation & Analysis
            - Dashboard Usage
            - Advanced Tools
            - Troubleshooting
            - Best Practices
            """)

        # Quick reference
        st.markdown("---")
        st.subheader("📋 Quick Reference")

        quickref_path = Path("docs/COMMANDS_QUICKREF.md")

        if quickref_path.exists():
            with st.expander("View 1-Page Quick Reference"):
                with open(quickref_path, 'r', encoding='utf-8') as f:
                    quickref_content = f.read()

                st.markdown(quickref_content)

                st.download_button(
                    "📥 Download Quick Reference",
                    data=quickref_content,
                    file_name="LOL_ELO_Quick_Reference.md",
                    mime="text/markdown",
                    key="download_quickref"
                )

    # === TAB 3: SCIENTIFIC DOCUMENTATION ===
    with tab3:
        st.subheader("🔬 Scientific Documentation")
        st.markdown("Mathematical foundations and methodology")

        # Check if scientific blog exists
        blog_path = Path("docs/SCIENTIFIC_BLOG.md")

        if blog_path.exists():
            with open(blog_path, 'r', encoding='utf-8') as f:
                blog_content = f.read()

            st.markdown(blog_content)

            # Download option
            st.markdown("---")
            st.download_button(
                "📥 Download Scientific Documentation (Markdown)",
                data=blog_content,
                file_name="LOL_ELO_Scientific_Documentation.md",
                mime="text/markdown"
            )

        else:
            st.warning("Scientific documentation not found at `docs/SCIENTIFIC_BLOG.md`")

            st.info("""
            **Expected location:** `docs/SCIENTIFIC_BLOG.md`

            The scientific documentation should include:
            - Abstract & Introduction
            - Mathematical Foundation
            - System Architecture
            - Validation Methodology
            - Design Decisions & Rationale
            - Alternative Approaches
            - Limitations & Future Work
            - Evaluation Summary
            - References
            """)

        # Key insights summary
        st.markdown("---")
        st.subheader("🎯 Key Insights")

        st.markdown("""
        **Model Performance:**
        - Overall Accuracy: **68.2% ± 1.6%**
        - Heavy Favorite (200+ ELO): **89.7%**
        - Worlds Championship: **71.4%**

        **Key Features:**
        - Tournament-aware K-factors (+0.52pp improvement)
        - Regional scale factors (+0.48pp improvement)
        - Temporal cross-validation (avoids data leakage)

        **Validated Methods:**
        - ✅ K-Fold temporal cross-validation
        - ✅ Bootstrap confidence intervals
        - ✅ Feature importance ablation study
        - ✅ Error pattern analysis

        **Recommended Configuration:**
        - K-factor: 24 (regular), 28 (playoffs), 32 (Worlds)
        - Regional scaling: Enabled
        - Tournament context: Enabled
        """)

    # === TAB 4: API REFERENCE ===
    with tab4:
        st.subheader("💻 API Reference")
        st.markdown("Programmatic usage and code examples")

        # Core classes
        st.markdown("### 🔧 Core Classes")

        with st.expander("📊 DatabaseManager"):
            st.markdown("""
            **Database operations and match storage**

            ```python
            from core.database import DatabaseManager

            # Initialize
            db = DatabaseManager(db_path="db/elo_system.db")

            # Insert match
            match_id = db.insert_match(
                team1="T1",
                team2="Gen.G",
                team1_score=3,
                team2_score=2,
                winner="T1",
                date="2024-11-16",
                tournament="LCK Summer Playoffs"
            )

            # Get statistics
            stats = db.get_stats()
            print(f"Total matches: {stats['total_matches']}")

            # Get team
            team_id, team_name = db.get_or_create_team("T1", region="KR")

            # Close connection
            db.close()
            ```

            **Key Methods:**
            - `insert_match()` - Insert new match
            - `get_or_create_team()` - Get or create team
            - `get_stats()` - Get database statistics
            - `insert_match_player()` - Insert player participation
            """)

        with st.expander("🎯 TournamentContextElo"):
            st.markdown("""
            **ELO calculator with tournament-aware K-factors**

            ```python
            from variants.with_tournament_context import TournamentContextElo

            # Initialize
            elo = TournamentContextElo(k_factor=24)

            # Calculate win probability
            prob = elo.expected_score(team1_elo=1650, team2_elo=1580)
            print(f"Team 1 win probability: {prob:.2%}")

            # Update ratings
            elo1_new, elo2_new = elo.update_ratings_with_context(
                elo1=1650,
                elo2=1580,
                score1=1,  # Team 1 won
                score2=0,  # Team 2 lost
                context='worlds'  # Tournament context
            )

            print(f"Team 1: 1650 → {int(elo1_new)}")
            print(f"Team 2: 1580 → {int(elo2_new)}")
            ```

            **Tournament Contexts:**
            - `'worlds'` - World Championship (K=32)
            - `'msi'` - Mid-Season Invitational (K=30)
            - `'playoffs'` - Regional playoffs (K=28)
            - `'regular_season'` - Regular season (K=24)
            """)

        with st.expander("🏷️ TeamNameResolver"):
            st.markdown("""
            **Resolve team names across different data sources**

            ```python
            from core.team_name_resolver import TeamNameResolver

            # Initialize
            resolver = TeamNameResolver()

            # Resolve team name
            canonical = resolver.resolve("SKT", source="lolesports")
            print(f"SKT → {canonical}")  # "T1"

            canonical = resolver.resolve("LLL", source="api")
            print(f"LLL → {canonical}")  # "LOUD"

            # Batch resolve
            teams = ["SKT", "GenG", "G2"]
            resolved = resolver.resolve_batch(teams)
            print(resolved)  # {'SKT': 'T1', 'GenG': 'Gen.G', 'G2': 'G2 Esports'}

            # Add new mapping
            resolver.add_mapping(
                canonical="New Team",
                aliases=["NT", "NewTeam"],
                region="EU",
                notes="New LEC team"
            )
            resolver.save_mappings()
            ```
            """)

        with st.expander("📦 UnifiedDataLoader"):
            st.markdown("""
            **Load data from database or Google Sheets seamlessly**

            ```python
            from core.unified_data_loader import UnifiedDataLoader

            # Load matches (auto-selects best source)
            with UnifiedDataLoader() as loader:
                df = loader.load_matches(source='auto')
                print(f"Loaded {len(df)} matches")

            # Explicit source
            with UnifiedDataLoader() as loader:
                df = loader.load_matches(source='database')
                # or source='sheets'

            # Process data
            print(df.head())
            print(df.columns)
            ```

            **Sources:**
            - `'auto'` - Automatically choose (prefers database)
            - `'database'` - SQLite database
            - `'sheets'` - Google Sheets
            """)

        # Scripts
        st.markdown("---")
        st.markdown("### 🛠️ Scripts")

        with st.expander("📥 Import Scripts"):
            st.markdown("""
            **Import data from various sources**

            ```bash
            # Google Sheets
            python scripts/import_google_sheets.py

            # Leaguepedia - Test
            python scripts/import_tier1_data.py --test

            # Leaguepedia - Year range
            python scripts/import_tier1_data.py --start-year 2023 --end-year 2024

            # Leaguepedia - Specific leagues
            python scripts/import_tier1_data.py --leagues LEC LCK --start-year 2024
            ```
            """)

        with st.expander("📊 Validation Scripts"):
            st.markdown("""
            **Run validation tests**

            ```bash
            # Master validation report (recommended)
            python scripts/generate_validation_report.py

            # K-Fold cross-validation
            python validation/k_fold_validation.py --k 5

            # Bootstrap confidence intervals
            python validation/bootstrap_ci.py --iterations 1000

            # Feature importance
            python analysis/feature_importance.py

            # Error patterns
            python analysis/error_patterns.py
            ```
            """)

        with st.expander("🔍 Database Tools"):
            st.markdown("""
            **Database management and viewing**

            ```bash
            # Interactive viewer
            python scripts/view_database.py

            # Quick stats
            python scripts/view_database.py stats

            # Recent matches
            python scripts/view_database.py matches 20

            # Team search
            python scripts/view_database.py team "T1"

            # Player search
            python scripts/view_database.py player "Faker"

            # Diagnose duplicates
            python scripts/diagnose_duplicates.py
            ```
            """)

        # Examples
        st.markdown("---")
        st.markdown("### 📝 Complete Examples")

        with st.expander("Example 1: Calculate Current Rankings"):
            st.markdown("""
            ```python
            from core.unified_data_loader import UnifiedDataLoader
            from variants.with_tournament_context import TournamentContextElo
            import pandas as pd

            # Load matches
            loader = UnifiedDataLoader()
            matches_df = loader.load_matches(source='auto')

            # Initialize ELO
            elo = TournamentContextElo(k_factor=24)
            team_elos = {}

            # Process matches chronologically
            matches_df = matches_df.sort_values('date')

            for _, match in matches_df.iterrows():
                team1, team2 = match['team1'], match['team2']

                # Initialize teams
                if team1 not in team_elos:
                    team_elos[team1] = 1500
                if team2 not in team_elos:
                    team_elos[team2] = 1500

                # Update ratings
                winner = match['winner']
                score1 = 1 if winner == team1 else 0
                score2 = 1 if winner == team2 else 0

                elo1_new, elo2_new = elo.update_ratings(
                    team_elos[team1],
                    team_elos[team2],
                    score1,
                    score2
                )

                team_elos[team1] = elo1_new
                team_elos[team2] = elo2_new

            # Display rankings
            rankings = sorted(team_elos.items(), key=lambda x: x[1], reverse=True)

            print("Top 10 Teams:")
            for rank, (team, elo_rating) in enumerate(rankings[:10], 1):
                print(f"{rank}. {team}: {int(elo_rating)}")
            ```
            """)

        with st.expander("Example 2: Predict Tournament Bracket"):
            st.markdown("""
            ```python
            from variants.with_tournament_context import TournamentContextElo

            # Team ELOs (from current rankings)
            teams = {
                'T1': 1720,
                'Gen.G': 1680,
                'JDG': 1695,
                'BLG': 1670
            }

            elo = TournamentContextElo(k_factor=24)

            # Semifinal 1: T1 vs JDG
            prob_t1 = elo.expected_score(teams['T1'], teams['JDG'])
            print(f"T1 vs JDG: {prob_t1:.1%} - {(1-prob_t1):.1%}")

            # Semifinal 2: Gen.G vs BLG
            prob_geng = elo.expected_score(teams['Gen.G'], teams['BLG'])
            print(f"Gen.G vs BLG: {prob_geng:.1%} - {(1-prob_geng):.1%}")

            # Finals prediction (assuming T1 and Gen.G win)
            prob_t1_final = elo.expected_score(teams['T1'], teams['Gen.G'])
            print(f"\\nFinals - T1 vs Gen.G: {prob_t1_final:.1%} - {(1-prob_t1_final):.1%}")
            ```
            """)

        with st.expander("Example 3: Export Analysis to CSV"):
            st.markdown("""
            ```python
            from core.database import DatabaseManager
            import pandas as pd

            db = DatabaseManager()

            # Custom analysis query
            query = '''
                SELECT
                    t.name,
                    t.region,
                    COUNT(m.id) as total_matches,
                    SUM(CASE WHEN m.winner_id = t.id THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN m.winner_id != t.id THEN 1 ELSE 0 END) as losses,
                    ROUND(
                        100.0 * SUM(CASE WHEN m.winner_id = t.id THEN 1 ELSE 0 END) / COUNT(m.id),
                        1
                    ) as win_rate
                FROM teams t
                JOIN matches m ON t.id IN (m.team1_id, m.team2_id)
                GROUP BY t.id
                HAVING total_matches >= 10
                ORDER BY win_rate DESC
            '''

            df = pd.read_sql_query(query, db.conn)
            db.close()

            # Export to CSV
            df.to_csv('team_statistics.csv', index=False)
            print(f"Exported {len(df)} teams to team_statistics.csv")

            # Display
            print(df.head(10))
            ```
            """)

        # Additional resources
        st.markdown("---")
        st.markdown("### 📚 Additional Resources")

        st.markdown("""
        **Documentation Files:**
        - `docs/COMMANDS_GUIDE.md` - Complete command guide
        - `docs/COMMANDS_QUICKREF.md` - 1-page quick reference
        - `docs/SCIENTIFIC_BLOG.md` - Scientific methodology
        - `docs/API_INTEGRATION.md` - API integration guide
        - `docs/LEAGUEPEDIA_BEST_PRACTICES.md` - API best practices

        **Source Code:**
        - `core/` - Core system components
        - `variants/` - ELO algorithm variants
        - `validation/` - Validation scripts
        - `analysis/` - Analysis tools
        - `scripts/` - Utility scripts
        - `dashboard/` - Streamlit dashboard

        **Getting Help:**
        - Check troubleshooting in command guide
        - Review error messages carefully
        - Test with `--test` flag first
        - Use interactive database viewer for debugging
        """)


if __name__ == "__main__":
    show()
