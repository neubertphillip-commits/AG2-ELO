"""
Export complete ELO match history in Excel format

This script exports all matches with calculated ELO ratings for each team
at the time of the match, similar to the Excel match sheet format.
"""

import sys
from pathlib import Path
from datetime import datetime
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import DatabaseManager
from core.elo_calculator_service import EloCalculatorService
from variants.with_dynamic_offsets import DynamicOffsetElo


def export_elo_history(variant='dynamic_offset', k_factor=24, use_scale_factors=True,
                       output_file='exports/elo_match_history.csv'):
    """
    Export complete match history with ELO ratings

    Args:
        variant: ELO variant to use
        k_factor: K-factor for ELO calculation
        use_scale_factors: Whether to use scale factors
        output_file: Output file path
    """

    print("="*70)
    print("ELO MATCH HISTORY EXPORT")
    print("="*70)

    # Initialize
    db = DatabaseManager()

    # Get all matches
    print(f"\n[LOADING] Loading matches...")
    matches = db.get_all_matches(limit=None)
    print(f"[OK] Loaded {len(matches)} matches")

    # Initialize ELO calculator
    print(f"\n[CALCULATING] Calculating ELO ratings ({variant})...")

    if variant == 'dynamic_offset':
        elo = DynamicOffsetElo(
            k_factor=k_factor,
            initial_elo=1500,
            use_scale_factors=use_scale_factors
        )
    else:
        # Use service for other variants
        service = EloCalculatorService(db)
        config_id, team_ratings = service.calculate_or_load_elos(
            variant=variant,
            k_factor=k_factor,
            use_scale_factors=use_scale_factors
        )

    # Build match history with ELO values
    history_data = []

    # Track ELO for manual calculation if using DynamicOffsetElo
    if variant == 'dynamic_offset':
        for i, match in enumerate(matches, 1):
            team1 = match['team1_name']
            team2 = match['team2_name']
            score1 = match['team1_score']
            score2 = match['team2_score']

            # Get ELO BEFORE match
            team1_elo_before = elo.get_rating(team1)
            team2_elo_before = elo.get_rating(team2)

            # Calculate expected win probability
            prob_team1_wins = 1 / (1 + 10 ** ((team2_elo_before - team1_elo_before) / 400))
            prob_team2_wins = 1 - prob_team1_wins

            # Update ratings
            elo.update_ratings(team1, team2, score1, score2)

            # Get ELO AFTER match
            team1_elo_after = elo.get_rating(team1)
            team2_elo_after = elo.get_rating(team2)

            # Calculate deltas
            delta1 = team1_elo_after - team1_elo_before
            delta2 = team2_elo_after - team2_elo_before

            # Determine winner
            if score1 > score2:
                winner = team1
                loser = team2
            else:
                winner = team2
                loser = team1

            # Build row
            row = {
                'Match #': i,
                'Date': match['date'],
                'Team 1': team1,
                'Team 2': team2,
                'Score': f"{score1}-{score2}",
                'Winner': winner,
                'Tournament': match.get('tournament', match.get('stage', 'Unknown')),
                'Stage': match.get('stage', ''),
                'Team 1 ELO Before': round(team1_elo_before, 1),
                'Team 2 ELO Before': round(team2_elo_before, 1),
                'Team 1 Win Probability': f"{prob_team1_wins*100:.1f}%",
                'Team 2 Win Probability': f"{prob_team2_wins*100:.1f}%",
                'Team 1 ELO Change': f"{delta1:+.1f}" if delta1 else "0.0",
                'Team 2 ELO Change': f"{delta2:+.1f}" if delta2 else "0.0",
                'Team 1 ELO After': round(team1_elo_after, 1),
                'Team 2 ELO After': round(team2_elo_after, 1),
                'Patch': match.get('patch', ''),
                'Source': match.get('source', '')
            }

            history_data.append(row)

            if i % 100 == 0:
                print(f"  Processed {i}/{len(matches)} matches...")

    print(f"\n[OK] Calculated ELO for {len(history_data)} matches")

    # Create DataFrame
    df = pd.DataFrame(history_data)

    # Export to CSV
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"\n[EXPORTING] Writing to {output_file}...")
    df.to_csv(output_file, index=False, encoding='utf-8-sig')  # UTF-8 with BOM for Excel

    print(f"\n[OK] Export complete!")
    print(f"  File: {output_file}")
    print(f"  Rows: {len(df)}")
    print(f"  Columns: {len(df.columns)}")

    # Print column summary
    print(f"\n[INFO] Columns:")
    for col in df.columns:
        print(f"  - {col}")

    # Print sample
    print(f"\n[SAMPLE] First 3 matches:")
    print(df.head(3).to_string(index=False))

    return output_file


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Export ELO Match History')
    parser.add_argument('--variant', type=str, default='dynamic_offset',
                       choices=['base', 'scale_factor', 'dynamic_offset', 'tournament_context'],
                       help='ELO variant to use')
    parser.add_argument('--k-factor', type=int, default=24,
                       help='K-factor for ELO calculation')
    parser.add_argument('--no-scale', action='store_true',
                       help='Disable scale factors')
    parser.add_argument('--output', type=str, default='exports/elo_match_history.csv',
                       help='Output file path')

    args = parser.parse_args()

    export_elo_history(
        variant=args.variant,
        k_factor=args.k_factor,
        use_scale_factors=not args.no_scale,
        output_file=args.output
    )
