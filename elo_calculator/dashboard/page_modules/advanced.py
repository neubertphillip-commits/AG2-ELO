"""
Advanced Tools Page - Power user features
"""

import streamlit as st
import pandas as pd
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.database import DatabaseManager
from core.team_name_resolver import TeamNameResolver


def show():
    """Display advanced tools page"""

    st.title("⚙️ Advanced Tools")
    st.markdown("Power user features and utilities")

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "🏷️ Team Name Mapping",
        "🗄️ SQL Console",
        "🔧 ELO Variants",
        "🛠️ System Configuration"
    ])

    # === TAB 1: TEAM NAME MAPPING ===
    with tab1:
        st.subheader("🏷️ Team Name Mapping")
        st.markdown("Manage team name aliases and mappings")

        st.info("""
        **Why Team Name Mapping?**

        Different data sources use different team names:
        - Lolesports API: "LLL"
        - Leaguepedia: "LOUD"
        - Google Sheets: "Los Loud"

        The resolver maps these to a single canonical name: "LOUD"
        """)

        try:
            resolver = TeamNameResolver()

            # Display statistics
            stats = resolver.get_stats()

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Canonical Teams", stats['canonical_teams'])

            with col2:
                st.metric("Total Mappings", stats['total_mappings'])

            with col3:
                st.metric("Cache Size", stats['cache_size'])

            # Show mappings
            st.markdown("---")
            st.subheader("📋 Current Mappings")

            mappings = resolver.mappings.get('mappings', [])

            if mappings:
                # Filter
                search = st.text_input("🔍 Search teams", placeholder="Enter team name or alias...")

                filtered_mappings = mappings
                if search:
                    search_lower = search.lower()
                    filtered_mappings = [
                        m for m in mappings
                        if search_lower in m['canonical_name'].lower() or
                        any(search_lower in alias.lower() for alias in m.get('aliases', []))
                    ]

                # Display
                for mapping in filtered_mappings[:20]:  # Limit to 20
                    with st.expander(f"**{mapping['canonical_name']}** ({mapping.get('region', 'Unknown')})"):
                        st.markdown(f"**Aliases:** {', '.join(mapping.get('aliases', []))}")
                        if mapping.get('notes'):
                            st.caption(f"Notes: {mapping['notes']}")

                if len(filtered_mappings) > 20:
                    st.info(f"Showing 20 of {len(filtered_mappings)} results. Use search to narrow down.")

            # Test resolver
            st.markdown("---")
            st.subheader("🧪 Test Resolver")

            test_name = st.text_input("Enter team name to resolve", placeholder="e.g., SKT, GenG, T 1")

            if test_name:
                resolved = resolver.resolve(test_name, source="dashboard_test")
                fuzzy_result = resolver.fuzzy_match(test_name)

                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("**Input:**")
                    st.code(test_name)

                with col2:
                    st.markdown("**Resolved:**")
                    st.code(resolved)

                if fuzzy_result:
                    canonical, confidence = fuzzy_result
                    st.info(f"Fuzzy match: {canonical} (confidence: {confidence:.2%})")

                if resolved in resolver.canonical_teams:
                    st.success("✓ Resolved to canonical name")
                else:
                    st.warning("⚠️ Not found in mappings - using original name")

            # Add new mapping (info only)
            st.markdown("---")
            st.subheader("➕ Add New Mapping")

            st.info("""
            To add a new team mapping, edit the configuration file:

            ```bash
            # Edit mappings
            nano config/team_name_mappings.json

            # Add entry:
            {
              "canonical_name": "New Team",
              "aliases": ["NT", "NewTeam", "New Team Esports"],
              "region": "EU",
              "notes": "Joined LEC in 2024"
            }

            # Test resolver
            python core/team_name_resolver.py
            ```

            Or use Python:

            ```python
            from core.name_resolver import TeamNameResolver

            resolver = TeamNameResolver()
            resolver.add_mapping(
                canonical="New Team",
                aliases=["NT", "NewTeam"],
                region="EU",
                notes="New team"
            )
            resolver.save_mappings()
            ```
            """)

        except Exception as e:
            st.error(f"Error loading team name resolver: {str(e)}")

    # === TAB 2: SQL CONSOLE ===
    with tab2:
        st.subheader("🗄️ SQL Console")
        st.markdown("Execute custom SQL queries")

        st.warning("⚠️ **Caution:** Only use SELECT queries. Modifying data can corrupt the database!")

        # Schema reference
        with st.expander("📚 Database Schema"):
            st.markdown("""
            **Tables:**

            ```sql
            -- Teams
            CREATE TABLE teams (
                team_id INTEGER PRIMARY KEY,
                team_name TEXT UNIQUE NOT NULL,
                region TEXT,
                created_at TIMESTAMP
            );

            -- Matches
            CREATE TABLE matches (
                match_id INTEGER PRIMARY KEY,
                team1_id INTEGER NOT NULL,
                team2_id INTEGER NOT NULL,
                team1_score INTEGER,
                team2_score INTEGER,
                winner_id INTEGER,
                match_date TEXT,
                tournament TEXT,
                external_id TEXT UNIQUE,
                FOREIGN KEY (team1_id) REFERENCES teams(team_id),
                FOREIGN KEY (team2_id) REFERENCES teams(team_id),
                FOREIGN KEY (winner_id) REFERENCES teams(team_id)
            );

            -- Players
            CREATE TABLE players (
                player_id INTEGER PRIMARY KEY,
                player_name TEXT NOT NULL,
                team_id INTEGER,
                role TEXT,
                FOREIGN KEY (team_id) REFERENCES teams(team_id)
            );

            -- Match Players (for player participation)
            CREATE TABLE match_players (
                match_player_id INTEGER PRIMARY KEY,
                match_id INTEGER NOT NULL,
                player_id INTEGER NOT NULL,
                FOREIGN KEY (match_id) REFERENCES matches(match_id),
                FOREIGN KEY (player_id) REFERENCES players(player_id)
            );

            -- Tournaments
            CREATE TABLE tournaments (
                tournament_id INTEGER PRIMARY KEY,
                tournament_name TEXT NOT NULL,
                start_date TEXT,
                end_date TEXT,
                region TEXT
            );
            ```
            """)

        # Example queries
        with st.expander("📝 Example Queries"):
            st.markdown("""
            ```sql
            -- Top 10 teams by win count
            SELECT
                t.name,
                COUNT(m.id) as total_matches,
                SUM(CASE WHEN m.winner_id = t.id THEN 1 ELSE 0 END) as wins
            FROM teams t
            JOIN matches m ON t.id IN (m.team1_id, m.team2_id)
            GROUP BY t.id
            ORDER BY wins DESC
            LIMIT 10;

            -- Matches by tournament
            SELECT
                tournament,
                COUNT(*) as match_count
            FROM matches
            GROUP BY tournament
            ORDER BY match_count DESC;

            -- Teams by region
            SELECT
                region,
                COUNT(*) as team_count
            FROM teams
            WHERE region IS NOT NULL
            GROUP BY region
            ORDER BY team_count DESC;

            -- Recent Worlds matches
            SELECT
                m.date,
                t1.name as team1,
                t2.name as team2,
                m.team1_score || '-' || m.team2_score as score
            FROM matches m
            JOIN teams t1 ON m.team1_id = t1.team_id
            JOIN teams t2 ON m.team2_id = t2.team_id
            WHERE m.tournament LIKE '%World%'
            ORDER BY m.date DESC
            LIMIT 20;
            ```
            """)

        # SQL input
        sql_query = st.text_area(
            "Enter SQL Query",
            height=150,
            placeholder="SELECT * FROM teams LIMIT 10;",
            help="Only SELECT queries are recommended"
        )

        col1, col2 = st.columns([1, 4])

        with col1:
            execute_button = st.button("▶️ Execute", type="primary")

        with col2:
            if sql_query and not sql_query.strip().upper().startswith('SELECT'):
                st.warning("⚠️ Non-SELECT query detected. Use caution!")

        if execute_button and sql_query:
            try:
                db = DatabaseManager()

                # Execute query
                df_result = pd.read_sql_query(sql_query, db.conn)

                db.close()

                # Display results
                st.success(f"✓ Query executed successfully! ({len(df_result)} rows)")

                st.dataframe(df_result, use_container_width=True)

                # Export option
                if not df_result.empty:
                    csv = df_result.to_csv(index=False)
                    st.download_button(
                        "📥 Download Results (CSV)",
                        data=csv,
                        file_name="query_results.csv",
                        mime="text/csv"
                    )

            except Exception as e:
                st.error(f"❌ Query failed: {str(e)}")

    # === TAB 3: ELO VARIANTS ===
    with tab3:
        st.subheader("🔧 ELO Variants")
        st.markdown("Compare different ELO implementations")

        st.info("""
        The system supports multiple ELO variants with different features:

        1. **BaseElo** - Classic ELO (1960s Arpad Elo)
        2. **ScaleFactorElo** - Adds regional scale factors
        3. **DynamicOffsetElo** - Adds regional initial offsets
        4. **TournamentContextElo** - Dynamic K-factors by tournament (recommended)
        """)

        # Variant comparison
        st.markdown("---")
        st.subheader("📊 Variant Comparison")

        comparison_data = [
            {
                'Variant': 'BaseElo',
                'K-Factor': 'Fixed (24)',
                'Regional Scaling': '❌',
                'Tournament Context': '❌',
                'Use Case': 'Simple baseline'
            },
            {
                'Variant': 'ScaleFactorElo',
                'K-Factor': 'Fixed (24)',
                'Regional Scaling': '✅',
                'Tournament Context': '❌',
                'Use Case': 'Cross-region prediction'
            },
            {
                'Variant': 'DynamicOffsetElo',
                'K-Factor': 'Fixed (24)',
                'Regional Scaling': '✅',
                'Tournament Context': '❌',
                'Use Case': 'Regional strength modeling'
            },
            {
                'Variant': 'TournamentContextElo',
                'K-Factor': 'Dynamic (24-32)',
                'Regional Scaling': '✅',
                'Tournament Context': '✅',
                'Use Case': '🏆 Production (recommended)'
            }
        ]

        df_variants = pd.DataFrame(comparison_data)

        st.dataframe(
            df_variants,
            use_container_width=True,
            hide_index=True
        )

        # Test variant
        st.markdown("---")
        st.subheader("🧪 Test ELO Calculation")

        selected_variant = st.selectbox(
            "Select Variant",
            ["TournamentContextElo", "BaseElo", "ScaleFactorElo", "DynamicOffsetElo"]
        )

        col1, col2, col3 = st.columns(3)

        with col1:
            team1_elo = st.number_input("Team 1 ELO", min_value=1000, max_value=2500, value=1650)

        with col2:
            team2_elo = st.number_input("Team 2 ELO", min_value=1000, max_value=2500, value=1580)

        with col3:
            if selected_variant == "TournamentContextElo":
                context = st.selectbox("Context", ["regular_season", "playoffs", "worlds"])
            else:
                context = None

        if st.button("Calculate"):
            try:
                # Import variant
                if selected_variant == "TournamentContextElo":
                    from variants.with_tournament_context import TournamentContextElo
                    elo = TournamentContextElo(k_factor=24)
                elif selected_variant == "BaseElo":
                    from variants.base_elo import BaseElo
                    elo = BaseElo(k_factor=24)
                elif selected_variant == "ScaleFactorElo":
                    from variants.with_scale_factor import ScaleFactorElo
                    elo = ScaleFactorElo(k_factor=24)
                elif selected_variant == "DynamicOffsetElo":
                    from variants.with_dynamic_offsets import DynamicOffsetElo
                    elo = DynamicOffsetElo(k_factor=24)

                # Calculate probability
                prob1 = elo.expected_score(team1_elo, team2_elo)
                prob2 = 1 - prob1

                st.markdown("---")
                st.subheader("Results")

                col1, col2 = st.columns(2)

                with col1:
                    st.metric("Team 1 Win Probability", f"{prob1:.2%}")

                with col2:
                    st.metric("Team 2 Win Probability", f"{prob2:.2%}")

                # Simulate outcome
                st.markdown("**If Team 1 wins:**")

                if context and selected_variant == "TournamentContextElo":
                    elo1_new, elo2_new = elo.update_ratings_with_context(
                        team1_elo, team2_elo, 1, 0, context
                    )
                else:
                    elo1_new, elo2_new = elo.update_ratings(
                        team1_elo, team2_elo, 1, 0
                    )

                col1, col2 = st.columns(2)

                with col1:
                    st.metric("Team 1 New ELO", int(elo1_new), delta=int(elo1_new - team1_elo))

                with col2:
                    st.metric("Team 2 New ELO", int(elo2_new), delta=int(elo2_new - team2_elo))

            except Exception as e:
                st.error(f"Error: {str(e)}")

        # Code reference
        st.markdown("---")
        st.subheader("💻 Code Reference")

        st.markdown("""
        **Using variants in Python:**

        ```python
        from variants.with_tournament_context import TournamentContextElo

        # Initialize
        elo = TournamentContextElo(k_factor=24)

        # Calculate probability
        prob = elo.expected_score(team1_elo=1650, team2_elo=1580)
        print(f"Team 1 win probability: {prob:.2%}")

        # Update ratings
        elo1_new, elo2_new = elo.update_ratings_with_context(
            elo1=1650,
            elo2=1580,
            score1=1,
            score2=0,
            context='worlds'  # or 'playoffs', 'regular_season'
        )

        print(f"Team 1: 1650 → {elo1_new}")
        print(f"Team 2: 1580 → {elo2_new}")
        ```

        **Test variants from command line:**

        ```bash
        python variants/base_elo.py
        python variants/with_scale_factor.py
        python variants/with_dynamic_offsets.py
        python variants/with_tournament_context.py
        ```
        """)

    # === TAB 4: SYSTEM CONFIGURATION ===
    with tab4:
        st.subheader("🛠️ System Configuration")
        st.markdown("View and manage system settings")

        # File paths
        st.markdown("### 📁 File Paths")

        paths = {
            "Database": "db/elo_system.db",
            "Team Mappings": "config/team_name_mappings.json",
            "Validation Results": "validation/",
            "Analysis Results": "analysis/",
            "Reports": "reports/"
        }

        for name, path in paths.items():
            path_obj = Path(path)
            exists = "✅" if path_obj.exists() else "❌"
            st.markdown(f"**{name}:** `{path}` {exists}")

        # Configuration files
        st.markdown("---")
        st.markdown("### ⚙️ Configuration Files")

        config_files = [
            "config/team_name_mappings.json",
        ]

        selected_config = st.selectbox(
            "Select configuration file",
            config_files
        )

        if st.button("📄 View Configuration"):
            try:
                with open(selected_config, 'r') as f:
                    content = f.read()

                st.code(content, language="json")

            except Exception as e:
                st.error(f"Error reading file: {str(e)}")

        # System info
        st.markdown("---")
        st.markdown("### ℹ️ System Information")

        import platform

        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"""
            **System:**
            - Platform: {platform.system()}
            - Python: {platform.python_version()}
            - Architecture: {platform.machine()}
            """)

        with col2:
            st.markdown(f"""
            **Libraries:**
            - pandas: {pd.__version__}
            - streamlit: {st.__version__}
            """)

        # Environment
        st.markdown("---")
        st.markdown("### 🌍 Environment")

        st.info("""
        **Environment Variables:**

        The system uses these environment variables (if configured):
        - `GOOGLE_SHEETS_CREDENTIALS` - Google Sheets API credentials
        - `LEAGUEPEDIA_API_KEY` - Leaguepedia API key (if required)

        **Configuration locations:**
        - Team mappings: `config/team_name_mappings.json`
        - Database: `db/elo_system.db`
        - Logs: Check terminal output
        """)


if __name__ == "__main__":
    show()
