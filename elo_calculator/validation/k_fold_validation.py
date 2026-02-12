"""
K-Fold Temporal Cross-Validation
Tests ELO system robustness across different time periods
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd
from datetime import datetime
from typing import List, Dict

from core.unified_data_loader import UnifiedDataLoader
from variants.with_dynamic_offsets import DynamicOffsetElo
import config


def temporal_k_fold_split(df: pd.DataFrame, k: int = 5) -> List[tuple]:
    """
    Split data into k chronological folds

    Args:
        df: DataFrame with matches (must have 'date' column)
        k: Number of folds

    Returns:
        List of (train_df, test_df) tuples
    """
    # Sort by date
    df = df.sort_values('date').reset_index(drop=True)

    # Calculate fold size
    fold_size = len(df) // k

    folds = []
    for i in range(k):
        # Test fold: chunk i
        test_start = i * fold_size
        test_end = (i + 1) * fold_size if i < k - 1 else len(df)

        test_df = df.iloc[test_start:test_end].copy()

        # Train fold: everything BEFORE test fold (chronological!)
        if test_start > 0:
            train_df = df.iloc[:test_start].copy()
        else:
            # For first fold, use next fold as train (or skip)
            continue

        folds.append((train_df, test_df))

    return folds


def evaluate_fold(train_df: pd.DataFrame, test_df: pd.DataFrame,
                  variant_class=DynamicOffsetElo) -> Dict:
    """
    Evaluate ELO system on one fold

    Args:
        train_df: Training data
        test_df: Testing data
        variant_class: ELO variant to use

    Returns:
        Dictionary with evaluation metrics
    """
    # Initialize ELO system
    elo = variant_class(
        k_factor=config.K_FACTOR,
        initial_elo=config.INITIAL_ELO,
        use_scale_factors=config.USE_SCALE_FACTORS,
        scale_factors=config.SCALE_FACTORS
    )

    # Train on training data
    for _, row in train_df.iterrows():
        try:
            team1 = row['team1']
            team2 = row['team2']
            score = row['score']

            # Parse score
            score_parts = score.split('-')
            if len(score_parts) != 2:
                continue

            score1 = int(score_parts[0])
            score2 = int(score_parts[1])

            # Update ELO
            elo.update_ratings(team1, team2, score1, score2)
        except:
            continue

    # Test on test data
    correct = 0
    total = 0
    predictions = []

    for _, row in test_df.iterrows():
        try:
            team1 = row['team1']
            team2 = row['team2']
            score = row['score']

            # Parse score
            score_parts = score.split('-')
            if len(score_parts) != 2:
                continue

            score1 = int(score_parts[0])
            score2 = int(score_parts[1])
            actual_winner = team1 if score1 > score2 else team2

            # Get prediction
            elo1 = elo.get_rating(team1)
            elo2 = elo.get_rating(team2)
            predicted_winner = team1 if elo1 > elo2 else team2

            predictions.append({
                'team1': team1,
                'team2': team2,
                'elo1': elo1,
                'elo2': elo2,
                'predicted': predicted_winner,
                'actual': actual_winner,
                'correct': predicted_winner == actual_winner
            })

            if predicted_winner == actual_winner:
                correct += 1
            total += 1

            # Update for next prediction
            elo.update_ratings(team1, team2, score1, score2)
        except:
            continue

    accuracy = (correct / total * 100) if total > 0 else 0

    return {
        'accuracy': accuracy,
        'correct': correct,
        'total': total,
        'train_size': len(train_df),
        'test_size': len(test_df),
        'predictions': predictions
    }


def run_k_fold_validation(k: int = 5, variant_class=DynamicOffsetElo) -> Dict:
    """
    Run k-fold cross-validation

    Args:
        k: Number of folds
        variant_class: ELO variant to test

    Returns:
        Dictionary with results
    """
    print("="*70)
    print(f"K-FOLD TEMPORAL CROSS-VALIDATION (k={k})")
    print("="*70)

    # Load data
    print("\n[LOADING] Loading data...")
    with UnifiedDataLoader() as loader:
        df = loader.load_matches(source='auto')

    print(f"[OK] Loaded {len(df)} matches")
    print(f"  Date range: {df['date'].min()} to {df['date'].max()}")

    # Create folds
    print(f"\n[DATA] Creating {k} temporal folds...")
    folds = temporal_k_fold_split(df, k=k)
    print(f"[OK] Created {len(folds)} folds")

    # Evaluate each fold
    results = []

    for i, (train_df, test_df) in enumerate(folds, 1):
        print(f"\n[PROCESSING] Fold {i}/{len(folds)}")
        print(f"  Train: {len(train_df)} matches ({train_df['date'].min()} to {train_df['date'].max()})")
        print(f"  Test:  {len(test_df)} matches ({test_df['date'].min()} to {test_df['date'].max()})")

        fold_result = evaluate_fold(train_df, test_df, variant_class)
        results.append(fold_result)

        print(f"  Accuracy: {fold_result['accuracy']:.2f}% ({fold_result['correct']}/{fold_result['total']})")

    # Aggregate results
    accuracies = [r['accuracy'] for r in results]
    mean_acc = np.mean(accuracies)
    std_acc = np.std(accuracies)

    print("\n" + "="*70)
    print("RESULTS")
    print("="*70)

    print(f"\n[DATA] Per-Fold Accuracies:")
    for i, acc in enumerate(accuracies, 1):
        print(f"  Fold {i}: {acc:.2f}%")

    print(f"\n📈 Summary Statistics:")
    print(f"  Mean Accuracy: {mean_acc:.2f}%")
    print(f"  Std Dev:       {std_acc:.2f}%")
    print(f"  95% CI:        {mean_acc:.2f}% ± {1.96 * std_acc:.2f}%")
    print(f"  Range:         [{min(accuracies):.2f}%, {max(accuracies):.2f}%]")

    # Interpretation
    print(f"\n💡 Interpretation:")
    if std_acc < 2.0:
        print(f"  ✅ Very robust (std < 2%)")
        print(f"     System performs consistently across time periods")
    elif std_acc < 5.0:
        print(f"  ✅ Robust (std < 5%)")
        print(f"     Minor variations across time periods")
    elif std_acc < 10.0:
        print(f"  [WARNING]  Moderate variation (std < 10%)")
        print(f"     Performance depends on time period")
    else:
        print(f"  ❌ High variation (std > 10%)")
        print(f"     System may be overfitting or unstable")

    return {
        'folds': results,
        'mean_accuracy': mean_acc,
        'std_accuracy': std_acc,
        'ci_95': (mean_acc - 1.96 * std_acc, mean_acc + 1.96 * std_acc),
        'k': k
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='K-Fold Cross-Validation')
    parser.add_argument('--k', type=int, default=5,
                       help='Number of folds (default: 5)')

    args = parser.parse_args()

    results = run_k_fold_validation(k=args.k)

    # Save results
    output_file = f"validation/k_fold_results_k{args.k}.json"
    Path("validation").mkdir(exist_ok=True)

    import json
    with open(output_file, 'w') as f:
        # Convert to JSON-serializable format
        json_results = {
            'mean_accuracy': results['mean_accuracy'],
            'std_accuracy': results['std_accuracy'],
            'ci_95': results['ci_95'],
            'k': results['k'],
            'fold_accuracies': [r['accuracy'] for r in results['folds']],
            'fold_sizes': [(r['train_size'], r['test_size']) for r in results['folds']]
        }
        json.dump(json_results, f, indent=2)

    print(f"\n[SAVED] Results saved to: {output_file}")
