"""
Error Pattern Analysis
Identifies which types of matchups the system predicts worst
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from typing import Dict, List
from collections import defaultdict

from core.unified_data_loader import UnifiedDataLoader
from variants.with_dynamic_offsets import DynamicOffsetElo
import config


def categorize_matchup(elo_diff: float) -> str:
    """
    Categorize matchup by ELO difference

    Args:
        elo_diff: Absolute ELO difference

    Returns:
        Matchup category
    """
    if elo_diff < 25:
        return "Toss-up (<25)"
    elif elo_diff < 50:
        return "Close (25-50)"
    elif elo_diff < 100:
        return "Moderate (50-100)"
    elif elo_diff < 150:
        return "Large (100-150)"
    else:
        return "Stomp (>150)"


def analyze_error_patterns(df: pd.DataFrame, train_split: float = 0.7) -> Dict:
    """
    Analyze error patterns in predictions

    Args:
        df: DataFrame with matches
        train_split: Train/test split ratio

    Returns:
        Dictionary with error analysis
    """
    print("="*70)
    print("ERROR PATTERN ANALYSIS")
    print("="*70)

    # Split data
    split_idx = int(len(df) * train_split)
    train_df = df.iloc[:split_idx].copy()
    test_df = df.iloc[split_idx:].copy()

    print(f"\n[DATA] Data Split:")
    print(f"  Train: {len(train_df)} matches")
    print(f"  Test:  {len(test_df)} matches")

    # Initialize ELO
    elo = DynamicOffsetElo(
        k_factor=config.K_FACTOR,
        initial_elo=config.INITIAL_ELO,
        use_scale_factors=config.USE_SCALE_FACTORS,
        scale_factors=config.SCALE_FACTORS
    )

    # Train
    print(f"\n[PROCESSING] Training on {len(train_df)} matches...")
    for _, row in train_df.iterrows():
        try:
            team1 = row['team1']
            team2 = row['team2']
            score = row['score']

            score_parts = score.split('-')
            if len(score_parts) != 2:
                continue

            score1 = int(score_parts[0])
            score2 = int(score_parts[1])

            elo.update_ratings(team1, team2, score1, score2)
        except:
            continue

    # Analyze test set
    print(f"\n[ANALYZING] Analyzing {len(test_df)} test matches...")

    predictions = []
    errors_by_category = defaultdict(lambda: {'correct': 0, 'total': 0})
    errors_by_tournament = defaultdict(lambda: {'correct': 0, 'total': 0})
    errors_by_closeness = defaultdict(lambda: {'correct': 0, 'total': 0})

    for _, row in test_df.iterrows():
        try:
            team1 = row['team1']
            team2 = row['team2']
            score = row['score']
            tournament = row.get('tournament', 'Unknown')
            stage = row.get('stage', 'Unknown')

            score_parts = score.split('-')
            if len(score_parts) != 2:
                continue

            score1 = int(score_parts[0])
            score2 = int(score_parts[1])
            actual_winner = team1 if score1 > score2 else team2

            # Get prediction
            elo1 = elo.get_rating(team1)
            elo2 = elo.get_rating(team2)
            elo_diff = abs(elo1 - elo2)
            predicted_winner = team1 if elo1 > elo2 else team2
            correct = predicted_winner == actual_winner

            # Categorize matchup
            matchup_category = categorize_matchup(elo_diff)

            # Track prediction
            prediction = {
                'team1': team1,
                'team2': team2,
                'elo1': elo1,
                'elo2': elo2,
                'elo_diff': elo_diff,
                'predicted': predicted_winner,
                'actual': actual_winner,
                'correct': correct,
                'matchup_category': matchup_category,
                'tournament': tournament,
                'stage': stage,
                'score': score,
                'closeness': abs(score1 - score2)
            }
            predictions.append(prediction)

            # Track by category
            errors_by_category[matchup_category]['total'] += 1
            if correct:
                errors_by_category[matchup_category]['correct'] += 1

            # Track by tournament
            errors_by_tournament[tournament]['total'] += 1
            if correct:
                errors_by_tournament[tournament]['correct'] += 1

            # Track by match closeness
            closeness = "Stomp" if abs(score1 - score2) >= 2 else "Close"
            errors_by_closeness[closeness]['total'] += 1
            if correct:
                errors_by_closeness[closeness]['correct'] += 1

            # Update for next prediction
            elo.update_ratings(team1, team2, score1, score2)

        except:
            continue

    # Analysis results
    results = {
        'predictions': predictions,
        'by_elo_diff': errors_by_category,
        'by_tournament': errors_by_tournament,
        'by_closeness': errors_by_closeness
    }

    return results


def print_error_analysis(results: Dict):
    """Print error analysis results"""

    print("\n" + "="*70)
    print("ERROR PATTERN RESULTS")
    print("="*70)

    # Overall accuracy
    total = len(results['predictions'])
    correct = sum(1 for p in results['predictions'] if p['correct'])
    accuracy = (correct / total * 100) if total > 0 else 0

    print(f"\n[DATA] Overall Test Accuracy: {accuracy:.2f}% ({correct}/{total})")

    # By ELO difference
    print(f"\n📈 Accuracy by ELO Difference:")
    print(f"\n  {'Category':<20} {'Accuracy':<12} {'Samples':<10} {'Correct/Total':<15}")
    print("  " + "-"*57)

    sorted_categories = sorted(results['by_elo_diff'].items(),
                              key=lambda x: int(x[0].split('(')[1].split('-')[0].replace('>', '').replace('<', '')))

    for category, stats in sorted_categories:
        cat_acc = (stats['correct'] / stats['total'] * 100) if stats['total'] > 0 else 0
        print(f"  {category:<20} {cat_acc:>6.2f}%      {stats['total']:>6}     "
              f"{stats['correct']}/{stats['total']}")

    # By match closeness
    print(f"\n🎯 Accuracy by Match Closeness:")
    print(f"\n  {'Type':<20} {'Accuracy':<12} {'Samples':<10}")
    print("  " + "-"*42)

    for closeness, stats in results['by_closeness'].items():
        close_acc = (stats['correct'] / stats['total'] * 100) if stats['total'] > 0 else 0
        print(f"  {closeness:<20} {close_acc:>6.2f}%      {stats['total']:>6}")

    # By tournament (top 10)
    print(f"\n🏆 Accuracy by Tournament (Top 10 by sample size):")
    print(f"\n  {'Tournament':<40} {'Accuracy':<12} {'Samples':<10}")
    print("  " + "-"*62)

    sorted_tournaments = sorted(results['by_tournament'].items(),
                               key=lambda x: x[1]['total'], reverse=True)[:10]

    for tournament, stats in sorted_tournaments:
        tourn_acc = (stats['correct'] / stats['total'] * 100) if stats['total'] > 0 else 0
        print(f"  {tournament[:38]:<40} {tourn_acc:>6.2f}%      {stats['total']:>6}")

    # Identify worst predictions (biggest ELO diff wrong)
    print(f"\n❌ Biggest Upsets (High ELO diff, wrong prediction):")
    print(f"\n  {'Match':<50} {'ELO Diff':<12} {'Result':<15}")
    print("  " + "-"*77)

    wrong_predictions = [p for p in results['predictions'] if not p['correct']]
    sorted_wrong = sorted(wrong_predictions, key=lambda x: x['elo_diff'], reverse=True)[:10]

    for p in sorted_wrong:
        match_str = f"{p['team1']} vs {p['team2']}"
        result_str = f"{p['predicted']} lost"
        print(f"  {match_str[:48]:<50} {p['elo_diff']:>8.0f}    {result_str:<15}")

    # Identify surprising correct predictions
    print(f"\n✅ Surprising Correct Predictions (Low ELO diff, correct):")
    print(f"\n  {'Match':<50} {'ELO Diff':<12} {'Result':<15}")
    print("  " + "-"*77)

    correct_predictions = [p for p in results['predictions'] if p['correct']]
    sorted_correct = sorted(correct_predictions, key=lambda x: x['elo_diff'])[:10]

    for p in sorted_correct:
        match_str = f"{p['team1']} vs {p['team2']}"
        result_str = f"{p['predicted']} won"
        print(f"  {match_str[:48]:<50} {p['elo_diff']:>8.0f}    {result_str:<15}")

    # Insights
    print(f"\n💡 Key Insights:")

    # Check if stomps are easier to predict
    by_elo = results['by_elo_diff']
    if 'Stomp (>150)' in by_elo and 'Toss-up (<25)' in by_elo:
        stomp_acc = (by_elo['Stomp (>150)']['correct'] / by_elo['Stomp (>150)']['total'] * 100)
        tossup_acc = (by_elo['Toss-up (<25)']['correct'] / by_elo['Toss-up (<25)']['total'] * 100)

        if stomp_acc > tossup_acc + 10:
            print(f"  ✅ Stomps are much easier to predict ({stomp_acc:.1f}% vs {tossup_acc:.1f}%)")
        elif stomp_acc > tossup_acc:
            print(f"  ✅ Stomps are slightly easier to predict ({stomp_acc:.1f}% vs {tossup_acc:.1f}%)")
        else:
            print(f"  [WARNING]  Stomps are NOT easier to predict ({stomp_acc:.1f}% vs {tossup_acc:.1f}%)")

    # Check close vs stomp matches
    by_close = results['by_closeness']
    if 'Stomp' in by_close and 'Close' in by_close:
        stomp_match_acc = (by_close['Stomp']['correct'] / by_close['Stomp']['total'] * 100)
        close_match_acc = (by_close['Close']['correct'] / by_close['Close']['total'] * 100)

        if abs(stomp_match_acc - close_match_acc) < 5:
            print(f"  ✅ Accuracy similar for close and stomp matches")
        elif stomp_match_acc > close_match_acc:
            print(f"  [WARNING]  Stomp matches easier to predict ({stomp_match_acc:.1f}% vs {close_match_acc:.1f}%)")
        else:
            print(f"  [WARNING]  Close matches easier to predict ({close_match_acc:.1f}% vs {stomp_match_acc:.1f}%)")


if __name__ == "__main__":
    # Load data
    print("\n[LOADING] Loading data...")
    with UnifiedDataLoader() as loader:
        df = loader.load_matches(source='auto')

    print(f"[OK] Loaded {len(df)} matches")

    # Run analysis
    results = analyze_error_patterns(df)

    # Print results
    print_error_analysis(results)

    # Save results
    output_file = "analysis/error_patterns_results.json"
    Path("analysis").mkdir(exist_ok=True)

    import json
    with open(output_file, 'w') as f:
        # Convert to JSON-serializable
        json_results = {
            'total_predictions': len(results['predictions']),
            'correct': sum(1 for p in results['predictions'] if p['correct']),
            'by_elo_diff': {k: dict(v) for k, v in results['by_elo_diff'].items()},
            'by_closeness': {k: dict(v) for k, v in results['by_closeness'].items()},
            'by_tournament': {k: dict(v) for k, v in results['by_tournament'].items()}
        }
        json.dump(json_results, f, indent=2)

    print(f"\n[SAVED] Results saved to: {output_file}")
