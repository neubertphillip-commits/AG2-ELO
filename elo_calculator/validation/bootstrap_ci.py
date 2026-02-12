"""
Bootstrap Confidence Intervals
Calculate statistical confidence for accuracy metrics
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd
from typing import List, Dict, Callable
from collections import defaultdict

from core.unified_data_loader import UnifiedDataLoader
from variants.with_dynamic_offsets import DynamicOffsetElo
import config


def bootstrap_resample(data: List, n_iterations: int = 1000) -> List[List]:
    """
    Generate bootstrap samples

    Args:
        data: Original data
        n_iterations: Number of bootstrap samples

    Returns:
        List of bootstrap samples
    """
    samples = []
    n = len(data)

    for _ in range(n_iterations):
        # Sample with replacement
        sample = np.random.choice(data, size=n, replace=True)
        samples.append(sample.tolist())

    return samples


def calculate_accuracy_ci(predictions: List[Dict],
                          n_iterations: int = 1000,
                          confidence: float = 0.95) -> Dict:
    """
    Calculate confidence interval for accuracy using bootstrap

    Args:
        predictions: List of prediction dictionaries
        n_iterations: Number of bootstrap iterations
        confidence: Confidence level (default: 95%)

    Returns:
        Dictionary with CI results
    """
    print(f"\n[PROCESSING] Running bootstrap with {n_iterations} iterations...")

    # Extract binary results
    results = [1 if p['correct'] else 0 for p in predictions]
    n_samples = len(results)

    # Original accuracy
    original_acc = np.mean(results) * 100

    # Bootstrap
    bootstrap_accs = []

    for i in range(n_iterations):
        if (i + 1) % 200 == 0:
            print(f"  Progress: {i + 1}/{n_iterations}")

        # Resample
        sample = np.random.choice(results, size=n_samples, replace=True)
        bootstrap_accs.append(np.mean(sample) * 100)

    # Calculate percentiles
    alpha = 1 - confidence
    lower_percentile = (alpha / 2) * 100
    upper_percentile = (1 - alpha / 2) * 100

    ci_lower = np.percentile(bootstrap_accs, lower_percentile)
    ci_upper = np.percentile(bootstrap_accs, upper_percentile)

    return {
        'accuracy': original_acc,
        'ci_lower': ci_lower,
        'ci_upper': ci_upper,
        'confidence': confidence,
        'n_iterations': n_iterations,
        'n_samples': n_samples,
        'bootstrap_mean': np.mean(bootstrap_accs),
        'bootstrap_std': np.std(bootstrap_accs)
    }


def analyze_cross_regional_ci(df: pd.DataFrame,
                               elo_variant=DynamicOffsetElo,
                               n_iterations: int = 1000) -> Dict:
    """
    Calculate CI for cross-regional accuracy

    Args:
        df: DataFrame with matches
        elo_variant: ELO variant to use
        n_iterations: Bootstrap iterations

    Returns:
        Results dictionary
    """
    print("="*70)
    print("BOOTSTRAP CI: CROSS-REGIONAL ACCURACY")
    print("="*70)

    # Initialize ELO
    elo = elo_variant(
        k_factor=config.K_FACTOR,
        initial_elo=config.INITIAL_ELO,
        use_scale_factors=config.USE_SCALE_FACTORS,
        scale_factors=config.SCALE_FACTORS
    )

    # Define regions
    REGION_KEYWORDS = {
        'EU': ['LEC', 'EU LCS', 'European'],
        'CN': ['LPL', 'Chinese'],
        'KR': ['LCK', 'Korean', 'Champions'],
        'NA': ['LCS', 'NA LCS', 'North America'],
        'International': ['Worlds', 'MSI', 'World Championship', 'Mid-Season']
    }

    def get_region(tournament_str):
        if pd.isna(tournament_str):
            return 'Unknown'
        for region, keywords in REGION_KEYWORDS.items():
            if any(kw in str(tournament_str) for kw in keywords):
                return region
        return 'Unknown'

    # Process matches
    cross_regional_predictions = []
    total_predictions = []
    team_regions = {}  # Track which region each team is from

    print(f"\n[DATA] Processing {len(df)} matches...")

    for _, row in df.iterrows():
        try:
            team1 = row['team1']
            team2 = row['team2']
            score = row['score']
            tournament = row.get('tournament', '')

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
            correct = predicted_winner == actual_winner

            # Determine regions
            match_region = get_region(tournament)

            # Track team regions based on tournaments they play in
            if match_region != 'International' and match_region != 'Unknown':
                team_regions[team1] = match_region
                team_regions[team2] = match_region

            prediction = {
                'team1': team1,
                'team2': team2,
                'tournament': tournament,
                'match_region': match_region,
                'predicted': predicted_winner,
                'actual': actual_winner,
                'correct': correct
            }

            total_predictions.append(prediction)

            # Check if cross-regional
            if match_region == 'International':
                # International tournament - check team home regions
                team1_region = team_regions.get(team1, 'Unknown')
                team2_region = team_regions.get(team2, 'Unknown')

                if team1_region != 'Unknown' and team2_region != 'Unknown' and team1_region != team2_region:
                    prediction['team1_region'] = team1_region
                    prediction['team2_region'] = team2_region
                    cross_regional_predictions.append(prediction)

            # Update ELO
            elo.update_ratings(team1, team2, score1, score2)

        except Exception as e:
            continue

    print(f"[OK] Total predictions: {len(total_predictions)}")
    print(f"[OK] Cross-regional predictions: {len(cross_regional_predictions)}")

    # Calculate CIs
    print(f"\n📈 Calculating confidence intervals...")

    overall_ci = calculate_accuracy_ci(total_predictions, n_iterations)

    results = {
        'overall': overall_ci,
        'cross_regional': None
    }

    if len(cross_regional_predictions) > 0:
        cross_regional_ci = calculate_accuracy_ci(cross_regional_predictions, n_iterations)
        results['cross_regional'] = cross_regional_ci

    # Print results
    print("\n" + "="*70)
    print("RESULTS")
    print("="*70)

    print(f"\n[DATA] Overall Accuracy:")
    print(f"  Accuracy: {overall_ci['accuracy']:.2f}%")
    print(f"  95% CI:   [{overall_ci['ci_lower']:.2f}%, {overall_ci['ci_upper']:.2f}%]")
    print(f"  Samples:  {overall_ci['n_samples']}")
    print(f"  Margin of Error: ±{(overall_ci['ci_upper'] - overall_ci['ci_lower']) / 2:.2f}%")

    if results['cross_regional']:
        cr_ci = results['cross_regional']
        print(f"\n🌍 Cross-Regional Accuracy:")
        print(f"  Accuracy: {cr_ci['accuracy']:.2f}%")
        print(f"  95% CI:   [{cr_ci['ci_lower']:.2f}%, {cr_ci['ci_upper']:.2f}%]")
        print(f"  Samples:  {cr_ci['n_samples']}")
        print(f"  Margin of Error: ±{(cr_ci['ci_upper'] - cr_ci['ci_lower']) / 2:.2f}%")

        # Comparison
        print(f"\n💡 Interpretation:")
        if cr_ci['n_samples'] < 50:
            print(f"  [WARNING]  Warning: Only {cr_ci['n_samples']} cross-regional samples")
            print(f"     Large margin of error (±{(cr_ci['ci_upper'] - cr_ci['ci_lower']) / 2:.2f}%)")
            print(f"     Need more international tournament data")
        elif cr_ci['n_samples'] < 100:
            print(f"  [WARNING]  Moderate sample size ({cr_ci['n_samples']} samples)")
            print(f"     Margin of error: ±{(cr_ci['ci_upper'] - cr_ci['ci_lower']) / 2:.2f}%")
        else:
            print(f"  ✅ Good sample size ({cr_ci['n_samples']} samples)")
            print(f"     Margin of error: ±{(cr_ci['ci_upper'] - cr_ci['ci_lower']) / 2:.2f}%")

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Bootstrap Confidence Intervals')
    parser.add_argument('--iterations', type=int, default=1000,
                       help='Number of bootstrap iterations (default: 1000)')

    args = parser.parse_args()

    # Load data
    print("\n[LOADING] Loading data...")
    with UnifiedDataLoader() as loader:
        df = loader.load_matches(source='auto')

    print(f"[OK] Loaded {len(df)} matches")

    # Run bootstrap
    results = analyze_cross_regional_ci(df, n_iterations=args.iterations)

    # Save results
    output_file = "validation/bootstrap_ci_results.json"
    Path("validation").mkdir(exist_ok=True)

    import json
    with open(output_file, 'w') as f:
        # Convert to JSON
        json_results = {
            'overall': results['overall'],
            'cross_regional': results['cross_regional'] if results['cross_regional'] else None
        }
        json.dump(json_results, f, indent=2)

    print(f"\n[SAVED] Results saved to: {output_file}")
