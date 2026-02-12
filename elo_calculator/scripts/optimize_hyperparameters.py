"""
Hyperparameter Optimization for ELO System
Tests all combinations of K-factors and Scale Factors
Finds the optimal configuration
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from itertools import product
from typing import List, Dict, Tuple

from core.data_loader import MatchDataLoader
from variants.base_elo import BaseEloCalculator
from variants.with_scale_factor import ScaleFactorEloCalculator
from validation.temporal_split import TemporalValidator


# ============================================================================
# HYPERPARAMETER SEARCH SPACE
# ============================================================================

K_FACTORS = [12, 16, 20, 24, 28, 32]

SCALE_FACTOR_PRESETS = {
    'none': None,  # No scale factors (baseline)
    
    'conservative': {
        '1-0': 1.00,
        '2-0': 1.00,
        '2-1': 0.50,  # Very reduced
        '3-0': 1.00,
        '3-1': 0.90,
        '3-2': 0.80,
    },
    
    'moderate': {
        '1-0': 1.00,
        '2-0': 1.00,
        '2-1': 0.85,  # Moderately reduced
        '3-0': 1.00,
        '3-1': 0.90,
        '3-2': 0.80,
    },
    
    'aggressive': {
        '1-0': 1.00,
        '2-0': 1.10,  # Reward stomps
        '2-1': 0.90,
        '3-0': 1.20,  # Big reward for 3-0
        '3-1': 0.95,
        '3-2': 0.85,
    },
    
    'minimal': {
        '1-0': 1.00,
        '2-0': 1.00,
        '2-1': 0.95,  # Barely reduced
        '3-0': 1.00,
        '3-1': 0.95,
        '3-2': 0.90,
    }
}


# ============================================================================
# OPTIMIZATION FUNCTIONS
# ============================================================================

def evaluate_configuration(matches: List[Dict], K: float, 
                          scale_preset: str, validator: TemporalValidator) -> Dict:
    """
    Evaluate one specific configuration
    
    Args:
        matches: Match data
        K: K-factor to test
        scale_preset: Scale factor preset name
        validator: Temporal validator
        
    Returns:
        Results dictionary
    """
    scale_factors = SCALE_FACTOR_PRESETS[scale_preset]
    
    # Choose calculator class
    if scale_factors is None:
        # Baseline ELO
        result = validator.validate_variant(
            BaseEloCalculator,
            matches,
            variant_name=f"K={K}, Scale=None",
            K=K
        )
    else:
        # Scale Factor ELO
        result = validator.validate_variant(
            ScaleFactorEloCalculator,
            matches,
            variant_name=f"K={K}, Scale={scale_preset}",
            K=K,
            scale_factors=scale_factors
        )
    
    return {
        'K': K,
        'scale_preset': scale_preset,
        'train_accuracy': result['train_accuracy'],
        'test_accuracy': result['test_accuracy'],
        'overfitting': result['overfitting'],
        'brier_score': result['brier_score'],
        'high_conf_accuracy': result['high_confidence_accuracy'],
        'high_conf_count': result['high_confidence_count']
    }


def grid_search(matches: List[Dict], k_factors: List[float] = None,
                scale_presets: List[str] = None,
                verbose: bool = True) -> pd.DataFrame:
    """
    Perform grid search over K-factors and Scale presets
    
    Args:
        matches: Match data
        k_factors: List of K values to test (default: K_FACTORS)
        scale_presets: List of scale preset names (default: all)
        verbose: Print progress
        
    Returns:
        DataFrame with all results sorted by test accuracy
    """
    k_factors = k_factors or K_FACTORS
    scale_presets = scale_presets or list(SCALE_FACTOR_PRESETS.keys())
    
    validator = TemporalValidator(train_ratio=0.7)
    
    results = []
    total_configs = len(k_factors) * len(scale_presets)
    current = 0
    
    print(f"\n{'='*70}")
    print(f"HYPERPARAMETER OPTIMIZATION")
    print(f"{'='*70}")
    print(f"\nTesting {total_configs} configurations:")
    print(f"  K-factors: {k_factors}")
    print(f"  Scale presets: {scale_presets}")
    print(f"  Matches: {len(matches)}")
    print(f"\nThis will take ~{total_configs * 3} seconds...\n")
    
    for K, scale_preset in product(k_factors, scale_presets):
        current += 1
        
        if verbose:
            print(f"[{current}/{total_configs}] Testing K={K}, Scale={scale_preset}...", end=' ')
        
        result = evaluate_configuration(matches, K, scale_preset, validator)
        results.append(result)
        
        if verbose:
            print(f"Test Acc: {result['test_accuracy']:.2%}")
    
    # Convert to DataFrame
    df = pd.DataFrame(results)
    
    # Sort by test accuracy (descending)
    df = df.sort_values('test_accuracy', ascending=False)
    df = df.reset_index(drop=True)
    
    # Add rank
    df.insert(0, 'Rank', range(1, len(df) + 1))
    
    return df


def quick_search(matches: List[Dict]) -> pd.DataFrame:
    """
    Quick search with reduced search space
    Faster for initial exploration
    
    Args:
        matches: Match data
        
    Returns:
        DataFrame with results
    """
    k_factors = [16, 20, 24]  # Reduced set
    scale_presets = ['none', 'moderate']  # Just baseline vs moderate
    
    return grid_search(matches, k_factors, scale_presets)


def print_top_results(df: pd.DataFrame, n: int = 10):
    """
    Print top N results in a nice format
    
    Args:
        df: Results DataFrame
        n: Number of top results to show
    """
    print(f"\n{'='*70}")
    print(f"TOP {n} CONFIGURATIONS")
    print(f"{'='*70}\n")
    
    top_n = df.head(n)
    
    for _, row in top_n.iterrows():
        print(f"{row['Rank']}. K={row['K']}, Scale={row['scale_preset']}")
        print(f"   Test Accuracy: {row['test_accuracy']:.4f} ({row['test_accuracy']*100:.2f}%)")
        print(f"   Train Accuracy: {row['train_accuracy']:.4f}")
        print(f"   Overfitting: {row['overfitting']:.4f}")
        print(f"   Brier Score: {row['brier_score']:.4f}")
        print(f"   High Conf: {row['high_conf_count']} predictions @ {row['high_conf_accuracy']:.2%}")
        print()


def analyze_results(df: pd.DataFrame):
    """
    Analyze results and provide insights
    
    Args:
        df: Results DataFrame
    """
    print(f"\n{'='*70}")
    print("ANALYSIS")
    print(f"{'='*70}\n")
    
    # Best overall
    best = df.iloc[0]
    print(f"[BEST] BEST CONFIGURATION:")
    print(f"   K-factor: {best['K']}")
    print(f"   Scale preset: {best['scale_preset']}")
    print(f"   Test Accuracy: {best['test_accuracy']:.4f} ({best['test_accuracy']*100:.2f}%)")

    # Best K-factor (averaged across scale presets)
    best_k = df.groupby('K')['test_accuracy'].mean().idxmax()
    best_k_acc = df.groupby('K')['test_accuracy'].mean().max()
    print(f"\n[STATS] BEST K-FACTOR (averaged): K={best_k} ({best_k_acc:.4f})")

    # Best scale preset (averaged across K-factors)
    best_scale = df.groupby('scale_preset')['test_accuracy'].mean().idxmax()
    best_scale_acc = df.groupby('scale_preset')['test_accuracy'].mean().max()
    print(f"[STATS] BEST SCALE PRESET (averaged): {best_scale} ({best_scale_acc:.4f})")
    
    # Impact of scale factors
    baseline_avg = df[df['scale_preset'] == 'none']['test_accuracy'].mean()
    with_scale_avg = df[df['scale_preset'] != 'none']['test_accuracy'].mean()
    scale_impact = with_scale_avg - baseline_avg
    
    print(f"\n[IMPACT] SCALE FACTOR IMPACT:")
    print(f"   Baseline (no scale): {baseline_avg:.4f}")
    print(f"   With scale factors: {with_scale_avg:.4f}")
    print(f"   Improvement: {scale_impact:.4f} ({scale_impact*100:+.2f} pp)")

    if scale_impact > 0.005:
        print(f"   [OK] Scale factors help!")
    elif scale_impact < -0.005:
        print(f"   [ERROR] Scale factors hurt performance")
    else:
        print(f"   [INFO] Scale factors have minimal impact")

    # Overfitting check
    high_overfit = df[df['overfitting'] > 0.05]
    if len(high_overfit) > 0:
        print(f"\n[WARNING] WARNING: {len(high_overfit)} configurations show high overfitting (>5%)")
        print(f"   Avoid: {high_overfit[['K', 'scale_preset', 'overfitting']].to_string(index=False)}")


def save_results(df: pd.DataFrame, filename: str = "optimization_results.csv"):
    """Save results to CSV"""
    df.to_csv(filename, index=False)
    print(f"\n[SAVED] Results saved to: {filename}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Run hyperparameter optimization"""
    print("Loading matches...")
    loader = MatchDataLoader()
    matches = loader.get_matches_as_dicts()
    print(f"[OK] Loaded {len(matches)} matches\n")
    
    # Choose search type
    print("Search options:")
    print("  1. Quick search (3 K-values × 2 scale presets = 6 configs)")
    print("  2. Full search (6 K-values × 5 scale presets = 30 configs)")
    
    choice = input("\nChoice [1/2]: ").strip()
    
    if choice == '1':
        print("\nRunning QUICK search...")
        results_df = quick_search(matches)
    else:
        print("\nRunning FULL search...")
        results_df = grid_search(matches)
    
    # Show results
    print_top_results(results_df, n=10)
    
    # Analysis
    analyze_results(results_df)
    
    # Save
    save_results(results_df)
    
    print(f"\n{'='*70}")
    print("OPTIMIZATION COMPLETE!")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()