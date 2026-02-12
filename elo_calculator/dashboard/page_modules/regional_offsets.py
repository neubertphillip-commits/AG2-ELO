"""
Regional Offsets Page - Dedicated page for regional strength analysis
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
    """Display regional offsets analysis page"""

    st.title("🌍 Regional Strength Offsets")
    st.markdown("Dynamic regional strength analysis and cross-regional match flow")

    # Info box
    with st.expander("ℹ️ What are Regional Offsets?", expanded=False):
        st.markdown("""
        **Regional Offsets** adjust team ratings based on regional strength, measured through cross-regional matches.

        ### How it Works:
        1. **Base ELO**: Standard rating (e.g., 1500)
        2. **Regional Offset**: Adjustment based on region performance (+83 for strong, -50 for weak)
        3. **Final ELO**: Base + Offset (e.g., 1500 + 83 = 1583)

        ### Example:
        - **LCK** teams get +83 points (historically dominant)
        - **LEC** teams get +20 points (competitive)
        - **LTA** teams get -50 points (developing region)

        These offsets are **dynamic** - they update as more cross-regional matches are played!
        """)

    try:
        db = DatabaseManager()
        service = EloCalculatorService(db)

        # Calculate DynamicOffsetElo
        with st.spinner('Calculating regional offsets...'):
            config_id, ratings = service.calculate_or_load_elos(
                variant='dynamic_offset',
                k_factor=24,
                use_scale_factors=True
            )

        # Load the actual calculator to get offsets
        from variants.with_dynamic_offsets import DynamicOffsetElo

        elo = DynamicOffsetElo(k_factor=24, use_scale_factors=True)

        # Reload all matches to populate offsets
        matches = db.get_all_matches(limit=None)
        for match in matches:
            elo.update_ratings(
                match['team1_name'],
                match['team2_name'],
                match['team1_score'],
                match['team2_score']
            )

        # Get offsets
        offsets = elo.calculator.offsets
        confidence = elo.calculator.confidence
        sample_counts = elo.calculator.sample_counts
        history = elo.calculator.history

        if offsets:
            # === CURRENT OFFSETS ===
            st.markdown("---")
            st.subheader("📊 Current Regional Offsets")

            # Create DataFrame
            offset_data = []
            for region, offset_value in offsets.items():
                offset_data.append({
                    'Region': region,
                    'Offset': round(offset_value, 1),
                    'Confidence': f"{confidence.get(region, 0)*100:.0f}%",
                    'Samples': sum(count for pair, count in sample_counts.items() if region in pair)
                })

            df_offsets = pd.DataFrame(offset_data)
            df_offsets = df_offsets.sort_values('Offset', ascending=False)

            # Metrics in columns
            cols = st.columns(min(4, len(df_offsets)))
            for i, (_, row) in enumerate(df_offsets.iterrows()):
                if i < len(cols):
                    with cols[i]:
                        delta_color = "normal" if row['Offset'] >= 0 else "inverse"
                        st.metric(
                            row['Region'],
                            f"{row['Offset']:+.1f}",
                            delta=f"{row['Confidence']} confidence"
                        )

            # Table
            st.markdown("---")
            st.dataframe(
                df_offsets,
                use_container_width=True,
                hide_index=True,
                column_config={
                    'Offset': st.column_config.NumberColumn(
                        'ELO Offset',
                        help='Positive = stronger than expected',
                        format='%+.1f'
                    ),
                    'Samples': st.column_config.NumberColumn(
                        'Cross-Regional Matches',
                        help='Number of matches used to calculate offset'
                    )
                }
            )

            # === HISTORICAL EVOLUTION ===
            st.markdown("---")
            st.subheader("📈 Historical Regional Strength Evolution")

            if history and len(history) > 10:
                # Build time series data
                offset_evolution = {}

                for i, h in enumerate(history):
                    # Track ALL regions for each match (after normalization)
                    for region in offsets.keys():
                        offset_key = f'offset_{region}'
                        if offset_key in h:
                            if region not in offset_evolution:
                                offset_evolution[region] = []
                            offset_evolution[region].append({
                                'match_index': i,
                                'offset': h[offset_key]
                            })

                # Create chart data
                if offset_evolution:
                    chart_data = pd.DataFrame()
                    for region, data_points in offset_evolution.items():
                        if len(data_points) > 5:  # Only show if enough data
                            df_region = pd.DataFrame(data_points)
                            chart_data[region] = df_region.set_index('match_index')['offset']

                    if not chart_data.empty:
                        st.line_chart(chart_data, use_container_width=True)

                        st.caption("""
                        This chart shows how regional strength offsets evolved over time as more cross-regional
                        matches were played. Sharp changes indicate surprising results (upsets or dominant performances).
                        """)
                    else:
                        st.info("Not enough historical data to show evolution chart")
                else:
                    st.info("No historical offset data available")

            else:
                st.info("Need more matches to show historical evolution (minimum 10)")

            # === CROSS-REGIONAL MATCH FLOW ===
            st.markdown("---")
            st.subheader("🌊 Cross-Regional Match Flow (Flusstabelle)")

            st.markdown("""
            Diese Tabelle zeigt die letzten cross-regionalen Matches und wie sie die Regional Offsets beeinflusst haben.
            Ähnlich wie die "Fluss-Daten" in der Excel-Datei.
            """)

            # Filter cross-regional matches from history
            cross_regional_matches = [h for h in history if h.get('is_cross_region')]

            if cross_regional_matches:
                # Show last 30 cross-regional matches
                recent_cross = cross_regional_matches[-30:]

                flow_data = []
                for h in reversed(recent_cross):  # Most recent first
                    winner_region = h.get('region1') if h.get('correct') else h.get('region2')
                    loser_region = h.get('region2') if h.get('correct') else h.get('region1')

                    flow_data.append({
                        'Match #': h.get('match_index', 0),
                        'Winner Region': winner_region,
                        'Loser Region': loser_region,
                        'ELO Transfer': abs(h.get('delta1', 0)),
                        'Winner Offset After': f"{h.get('offset1', 0):+.1f}" if h.get('correct') else f"{h.get('offset2', 0):+.1f}",
                        'Loser Offset After': f"{h.get('offset2', 0):+.1f}" if h.get('correct') else f"{h.get('offset1', 0):+.1f}",
                        'Impact': f"±{abs(h.get('delta1', 0)) * 0.1:.1f}"  # Offset impact is ~10% of ELO change
                    })

                df_flow = pd.DataFrame(flow_data)

                st.dataframe(
                    df_flow,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        'ELO Transfer': st.column_config.NumberColumn(
                            'ELO Transfer',
                            help='How much ELO was transferred between regions',
                            format='%.1f'
                        ),
                        'Impact': st.column_config.TextColumn(
                            'Offset Impact',
                            help='How much this match affected regional offsets'
                        )
                    }
                )

                st.caption(f"""
                Showing the {len(flow_data)} most recent cross-regional matches.
                Each match transfers ELO between regions and adjusts regional strength offsets.
                """)

                # === REGION vs REGION MATRIX ===
                st.markdown("---")
                st.subheader("📊 Region vs Region Win Matrix")

                # Build win matrix
                region_vs_region = {}
                for region1 in regions:
                    region_vs_region[region1] = {}
                    for region2 in regions:
                        if region1 != region2:
                            region_vs_region[region1][region2] = {'wins': 0, 'total': 0}

                # Count wins
                for h in cross_regional_matches:
                    r1 = h.get('region1')
                    r2 = h.get('region2')
                    if r1 and r2 and r1 != r2:
                        if h.get('correct'):  # region1 won
                            region_vs_region[r1][r2]['wins'] += 1
                            region_vs_region[r1][r2]['total'] += 1
                            region_vs_region[r2][r1]['total'] += 1
                        else:  # region2 won
                            region_vs_region[r2][r1]['wins'] += 1
                            region_vs_region[r2][r1]['total'] += 1
                            region_vs_region[r1][r2]['total'] += 1

                # Create matrix dataframe
                matrix_data = []
                for r1 in regions:
                    row = {'Region': r1}
                    for r2 in regions:
                        if r1 == r2:
                            row[r2] = '-'
                        else:
                            wins = region_vs_region[r1][r2]['wins']
                            total = region_vs_region[r1][r2]['total']
                            if total > 0:
                                winrate = wins / total * 100
                                row[r2] = f"{wins}-{total-wins} ({winrate:.0f}%)"
                            else:
                                row[r2] = '0-0'
                    matrix_data.append(row)

                df_matrix = pd.DataFrame(matrix_data)

                st.dataframe(
                    df_matrix,
                    use_container_width=True,
                    hide_index=True
                )

                st.caption("""
                Zeigt Siege-Niederlagen und Winrate für jede Region gegen jede andere Region.
                Format: Siege-Niederlagen (Winrate%)
                """)

            else:
                st.info("No cross-regional match data available. Import international tournaments (MSI, Worlds) to see regional matchups!")

            # === INTERPRETATION ===
            if len(df_offsets) >= 2:
                st.markdown("---")
                st.subheader("💡 Interpretation")

                strongest = df_offsets.iloc[0]
                weakest = df_offsets.iloc[-1]

                st.markdown(f"""
                **Strongest Region:** {strongest['Region']} (+{strongest['Offset']:.1f} ELO)
                - Teams from this region perform ~{abs(strongest['Offset'])/20:.0f} points better than expected
                - Based on {strongest['Samples']} cross-regional matches

                **Weakest Region:** {weakest['Region']} ({weakest['Offset']:+.1f} ELO)
                - Teams from this region perform ~{abs(weakest['Offset'])/20:.0f} points worse than expected
                - Based on {weakest['Samples']} cross-regional matches

                **Gap:** {strongest['Offset'] - weakest['Offset']:.1f} ELO points
                - This equals ~{(strongest['Offset'] - weakest['Offset'])*2.5:.0f}% win probability swing
                """)
            else:
                st.info("Need at least 2 regions to show comparison")

        else:
            st.warning("No regional offset data available. Need more cross-regional matches!")

    except Exception as e:
        st.error(f"Error loading regional offsets: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
