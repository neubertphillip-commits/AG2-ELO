"""
Feature Importance Analysis
Ablation study to determine contribution of each feature
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from typing import Dict, List
from dataclasses import dataclass

from core.unified_data_loader import UnifiedDataLoader
from variants.base_elo import BaseElo
from variants.with_scale_factor import ScaleFactorElo
from variants.with_dynamic_offsets import DynamicOffsetElo
from variants.with_tournament_context import TournamentContextElo
import config


@dataclass
class FeatureConfig:
    """Configuration for a feature combination"""
    name: str
    description: str
    variant_class: type
    k_factor: float
    use_scale: bool
    use_offsets: bool = False
    use_tournament_context: bool = False


def evaluate_configuration(df: pd.DataFrame, config_obj: FeatureConfig,
                          train_split: float = 0.7) -> Dict:
    """
    Evaluate a single configuration

    Args:
        df: DataFrame with matches
        config_obj: Feature configuration
        train_split: Train/test split ratio

    Returns:
        Dictionary with evaluation metrics
    """
    # Split data temporally
    split_idx = int(len(df) * train_split)
    train_df = df.iloc[:split_idx].copy()
    test_df = df.iloc[split_idx:].copy()

    # Initialize ELO variant
    if config_obj.use_tournament_context:
        elo = TournamentContextElo(
            k_factor=config_obj.k_factor,
            initial_elo=config.INITIAL_ELO,
            use_scale_factors=config_obj.use_scale,
            scale_factors=config.SCALE_FACTORS if config_obj.use_scale else None
        )
    elif config_obj.use_offsets:
        elo = DynamicOffsetElo(
            k_factor=config_obj.k_factor,
            initial_elo=config.INITIAL_ELO,
            use_scale_factors=config_obj.use_scale,
            scale_factors=config.SCALE_FACTORS if config_obj.use_scale else None
        )
    elif config_obj.use_scale:
        elo = ScaleFactorElo(
            k_factor=config_obj.k_factor,
            initial_elo=config.INITIAL_ELO,
            scale_factors=config.SCALE_FACTORS
        )
    else:
        elo = BaseElo(
            k_factor=config_obj.k_factor,
            initial_elo=config.INITIAL_ELO
        )

    # Train on training data
    for _, row in train_df.iterrows():
        try:
            team1 = row['team1']
            team2 = row['team2']
            score = row['score']
            tournament = row.get('tournament', '')
            stage = row.get('stage', '')

            score_parts = score.split('-')
            if len(score_parts) != 2:
                continue

            score1 = int(score_parts[0])
            score2 = int(score_parts[1])

            # Update with tournament context if available
            if hasattr(elo, 'update_ratings') and config_obj.use_tournament_context:
                elo.update_ratings(team1, team2, score1, score2,
                                  tournament=tournament, stage=stage)
            else:
                elo.update_ratings(team1, team2, score1, score2)
        except:
            continue

    # Evaluate on both train and test
    train_correct = 0
    train_total = 0
    test_correct = 0
    test_total = 0

    # Test set evaluation
    for _, row in test_df.iterrows():
        try:
            team1 = row['team1']
            team2 = row['team2']
            score = row['score']

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

            if predicted_winner == actual_winner:
                test_correct += 1
            test_total += 1

            # Update for next prediction
            tournament = row.get('tournament', '')
            stage = row.get('stage', '')

            if hasattr(elo, 'update_ratings') and config_obj.use_tournament_context:
                elo.update_ratings(team1, team2, score1, score2,
                                  tournament=tournament, stage=stage)
            else:
                elo.update_ratings(team1, team2, score1, score2)
        except:
            continue

    # Train set evaluation (retrospective)
    elo_train = config_obj.variant_class(
        k_factor=config_obj.k_factor,
        initial_elo=config.INITIAL_ELO,
        use_scale_factors=config_obj.use_scale,
        scale_factors=config.SCALE_FACTORS if config_obj.use_scale else None
    ) if not config_obj.use_tournament_context else TournamentContextElo(
        k_factor=config_obj.k_factor,
        initial_elo=config.INITIAL_ELO,
        use_scale_factors=config_obj.use_scale,
        scale_factors=config.SCALE_FACTORS if config_obj.use_scale else None
    )

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
            actual_winner = team1 if score1 > score2 else team2

            elo1 = elo_train.get_rating(team1)
            elo2 = elo_train.get_rating(team2)
            predicted_winner = team1 if elo1 > elo2 else team2

            if predicted_winner == actual_winner:
                train_correct += 1
            train_total += 1

            elo_train.update_ratings(team1, team2, score1, score2)
        except:
            continue

    train_acc = (train_correct / train_total * 100) if train_total > 0 else 0
    test_acc = (test_correct / test_total * 100) if test_total > 0 else 0
    overfitting = train_acc - test_acc

    return {
        'config': config_obj.name,
        'description': config_obj.description,
        'train_accuracy': train_acc,
        'test_accuracy': test_acc,
        'overfitting': overfitting,
        'train_samples': train_total,
        'test_samples': test_total
    }


def run_feature_importance_analysis(df: pd.DataFrame) -> List[Dict]:
    """
    Run ablation study on all feature combinations

    Args:
        df: DataFrame with matches

    Returns:
        List of results
    """
    print("="*70)
    print("FEATURE IMPORTANCE ANALYSIS (Ablation Study)")
    print("="*70)

    # Define configurations to test
    configurations = [
        # Baseline
        FeatureConfig(
            name="Baseline",
            description="Base ELO, K=20",
            variant_class=BaseElo,
            k_factor=20,
            use_scale=False
        ),

        # K-factor optimization
        FeatureConfig(
            name="Optimized K",
            description="Base ELO, K=24 (optimized)",
            variant_class=BaseElo,
            k_factor=24,
            use_scale=False
        ),

        # Scale factors
        FeatureConfig(
            name="K24 + Scale",
            description="K=24 + Scale Factors",
            variant_class=ScaleFactorElo,
            k_factor=24,
            use_scale=True
        ),

        # Regional offsets
        FeatureConfig(
            name="K24 + Scale + Offsets",
            description="K=24 + Scale + Regional Offsets",
            variant_class=DynamicOffsetElo,
            k_factor=24,
            use_scale=True,
            use_offsets=True
        ),

        # Tournament context
        FeatureConfig(
            name="K24 + Scale + Offsets + Context",
            description="Full system + Tournament Context",
            variant_class=TournamentContextElo,
            k_factor=24,
            use_scale=True,
            use_offsets=True,
            use_tournament_context=True
        ),
    ]

    results = []

    for i, config_obj in enumerate(configurations, 1):
        print(f"\n{'='*70}")
        print(f"Configuration {i}/{len(configurations)}: {config_obj.name}")
        print(f"{'='*70}")
        print(f"Description: {config_obj.description}")

        result = evaluate_configuration(df, config_obj)
        results.append(result)

        print(f"\n[DATA] Results:")
        print(f"  Train Accuracy: {result['train_accuracy']:.2f}%")
        print(f"  Test Accuracy:  {result['test_accuracy']:.2f}%")
        print(f"  Overfitting:    {result['overfitting']:+.2f}%")

    return results


def print_comparison_table(results: List[Dict]):
    """Print comparison table of all configurations"""
    print("\n" + "="*70)
    print("FEATURE IMPORTANCE COMPARISON")
    print("="*70)

    # Sort by test accuracy
    results_sorted = sorted(results, key=lambda x: x['test_accuracy'], reverse=True)

    print(f"\n{'Config':<35} {'Train':<10} {'Test':<10} {'Gap':<10} {'vs Baseline':<12}")
    print("-"*77)

    baseline_acc = next(r['test_accuracy'] for r in results if r['config'] == 'Baseline')

    for r in results_sorted:
        improvement = r['test_accuracy'] - baseline_acc
        improvement_str = f"+{improvement:.2f}%" if improvement > 0 else f"{improvement:.2f}%"

        print(f"{r['config']:<35} {r['train_accuracy']:>6.2f}%  {r['test_accuracy']:>6.2f}%  "
              f"{r['overfitting']:>6.2f}%  {improvement_str:>10}")

    # Calculate incremental improvements
    print(f"\n💡 Incremental Improvements:")

    for i in range(1, len(results)):
        prev = results[i-1]
        curr = results[i]
        delta = curr['test_accuracy'] - prev['test_accuracy']

        print(f"\n  {prev['config']} → {curr['config']}:")
        print(f"    {delta:+.2f}% ({prev['test_accuracy']:.2f}% → {curr['test_accuracy']:.2f}%)")


if __name__ == "__main__":
    # Load data
    print("\n[LOADING] Loading data...")
    with UnifiedDataLoader() as loader:
        df = loader.load_matches(source='auto')

    print(f"[OK] Loaded {len(df)} matches")

    # Run analysis
    results = run_feature_importance_analysis(df)

    # Print comparison
    print_comparison_table(results)

    # Save results
    output_file = "analysis/feature_importance_results.json"
    Path("analysis").mkdir(exist_ok=True)

    import json
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n[SAVED] Results saved to: {output_file}")
