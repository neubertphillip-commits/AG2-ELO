"""
Regional Offset Hyperparameter Optimization
Finds best prior_std and max_offset values
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from itertools import product
from typing import List, Dict

from core.data_loader import MatchDataLoader
from core.region_mapper import RegionMapper
from variants.with_dynamic_offsets import DynamicOffsetCalculator
from validation.temporal_split import TemporalValidator


# ============================================================================
# HYPERPARAMETER SEARCH SPACE
# ============================================================================

# Reduced search space (most impactful parameters)
PRIOR_STDS = [10, 15, 20, 25]
MAX_OFFSETS = [50, 60, 70, 80]
MIN_SAMPLES = [10, 15, 20]

# Total: 4 × 4 × 3 = 48 configurations (manageable!)


# ============================================================================
# EVALUATION FUNCTIONS
# ============================================================================

def evaluate_config(matches: List[Dict], prior_std: float, 
                   max_offset: float, min_samples: int,
                   validator: TemporalValidator) -> Dict:
    """
    Evaluate one configuration
    
    Args:
        matches: Match data
        prior_std: Prior standard deviation
        max_offset: Maximum offset cap
        min_samples: Minimum samples for confidence
        validator: Temporal validator
        
    Returns:
        Results dictionary
    """
    # Create custom calculator class with these parameters
    class CustomOffsetCalculator(DynamicOffsetCalculator):
        def __init__(self):
            super().__init__()
            self.prior_std = prior_std
            self.max_offset = max_offset
            self.min_samples_for_confidence = min_samples
    
    # Validate
    result = validator.validate_variant(
        CustomOffsetCalculator,
        matches,
        variant_name=f"prior={prior_std}, max={max_offset}, min={min_samples}"
    )
    
    # Get regional breakdown
    region_mapper = RegionMapper()
    train_matches, test_matches = validator.split_matches(matches)
    
    regional = []
    cross_regional = []
    
    for i, match in enumerate(test_matches):
        pred = result['all_predictions'][i]
        
        is_cross = region_mapper.is_cross_region(
            match['team1'], 
            match['team2'], 
            use_parent=False
        )
        
        if is_cross:
            cross_regional.append(pred['correct'])
        else:
            regional.append(pred['correct'])
    
    regional_acc = np.mean(regional) if regional else 0
    cross_acc = np.mean(cross_regional) if cross_regional else 0
    
    # Get final offsets
    calc = result['calculator']
    offsets_df = calc.get_current_offsets()
    
    max_offset_value = offsets_df['Offset'].abs().max()
    mean_confidence = offsets_df['Confidence'].mean()
    
    return {
        'prior_std': prior_std,
        'max_offset': max_offset,
        'min_samples': min_samples,
        'overall_accuracy': result['test_accuracy'],
        'regional_accuracy': regional_acc,
        'cross_regional_accuracy': cross_acc,
        'cross_improvement': cross_acc - 0.5217,  # vs baseline
        'overfitting': result['overfitting'],
        'brier_score': result['brier_score'],
        'max_offset_value': max_offset_value,
        'mean_confidence': mean_confidence,
        'n_cross_regional': len(cross_regional)
    }


def grid_search(matches: List[Dict], 
                prior_stds: List[float] = None,
                max_offsets: List[float] = None,
                min_samples_list: List[int] = None,
                verbose: bool = True) -> pd.DataFrame:
    """
    Grid search over offset hyperparameters
    
    Args:
        matches: Match data
        prior_stds: List of prior_std values to test
        max_offsets: List of max_offset values to test
        min_samples_list: List of min_samples values to test
        verbose: Print progress
        
    Returns:
        DataFrame with results sorted by cross_regional_accuracy
    """
    prior_stds = prior_stds or PRIOR_STDS
    max_offsets = max_offsets or MAX_OFFSETS
    min_samples_list = min_samples_list or MIN_SAMPLES
    
    validator = TemporalValidator(train_ratio=0.7)
    
    results = []
    total_configs = len(prior_stds) * len(max_offsets) * len(min_samples_list)
    current = 0
    
    print(f"\n{'='*70}")
    print(f"OFFSET HYPERPARAMETER OPTIMIZATION")
    print(f"{'='*70}")
    print(f"\nTesting {total_configs} configurations:")
    print(f"  Prior STDs: {prior_stds}")
    print(f"  Max Offsets: {max_offsets}")
    print(f"  Min Samples: {min_samples_list}")
    print(f"  Matches: {len(matches)}")
    print(f"\nThis will take ~{total_configs * 4} seconds...\n")
    
    for prior_std, max_offset, min_samples in product(prior_stds, max_offsets, min_samples_list):
        current += 1
        
        if verbose:
            print(f"[{current}/{total_configs}] Testing prior={prior_std}, "
                  f"max={max_offset}, min={min_samples}...", end=' ')
        
        result = evaluate_config(matches, prior_std, max_offset, min_samples, validator)
        results.append(result)
        
        if verbose:
            print(f"Cross-Regional: {result['cross_regional_accuracy']:.2%} "
                  f"(+{result['cross_improvement']*100:.2f}pp)")
    
    # Convert to DataFrame
    df = pd.DataFrame(results)
    
    # Sort by cross_regional_accuracy (what we care about!)
    df = df.sort_values('cross_regional_accuracy', ascending=False)
    df = df.reset_index(drop=True)
    
    # Add rank
    df.insert(0, 'Rank', range(1, len(df) + 1))
    
    return df


def quick_search(matches: List[Dict]) -> pd.DataFrame:
    """
    Quick search with reduced parameter space
    Faster for initial exploration
    
    Args:
        matches: Match data
        
    Returns:
        DataFrame with results
    """
    prior_stds = [15, 20, 25]  # Reduced
    max_offsets = [60, 70, 80]  # Reduced
    min_samples_list = [10, 15]  # Reduced
    
    return grid_search(matches, prior_stds, max_offsets, min_samples_list)


def print_top_results(df: pd.DataFrame, n: int = 10):
    """Print top N results"""
    print(f"\n{'='*70}")
    print(f"TOP {n} CONFIGURATIONS")
    print(f"{'='*70}\n")
    
    top_n = df.head(n)
    
    for _, row in top_n.iterrows():
        print(f"{row['Rank']}. prior_std={row['prior_std']}, "
              f"max_offset={row['max_offset']}, "
              f"min_samples={row['min_samples']}")
        print(f"   Cross-Regional: {row['cross_regional_accuracy']:.4f} "
              f"(+{row['cross_improvement']*100:.2f}pp vs baseline)")
        print(f"   Overall: {row['overall_accuracy']:.4f}")
        print(f"   Max Offset Used: {row['max_offset_value']:.1f}")
        print(f"   Mean Confidence: {row['mean_confidence']:.3f}")
        print()


def analyze_results(df: pd.DataFrame):
    """Analyze optimization results"""
    print(f"\n{'='*70}")
    print("ANALYSIS")
    print(f"{'='*70}\n")
    
    # Best overall
    best = df.iloc[0]
    print(f"[BEST] BEST CONFIGURATION:")
    print(f"   prior_std: {best['prior_std']}")
    print(f"   max_offset: {best['max_offset']}")
    print(f"   min_samples: {best['min_samples']}")
    print(f"   Cross-Regional Accuracy: {best['cross_regional_accuracy']:.4f}")
    print(f"   Improvement vs Baseline: +{best['cross_improvement']*100:.2f}pp")

    # Best by prior_std
    best_prior = df.groupby('prior_std')['cross_regional_accuracy'].mean().idxmax()
    print(f"\n[STATS] BEST PRIOR_STD (averaged): {best_prior}")
    print(f"   Mean Cross-Regional: {df.groupby('prior_std')['cross_regional_accuracy'].mean()[best_prior]:.4f}")

    # Best by max_offset
    best_max = df.groupby('max_offset')['cross_regional_accuracy'].mean().idxmax()
    print(f"[STATS] BEST MAX_OFFSET (averaged): {best_max}")
    print(f"   Mean Cross-Regional: {df.groupby('max_offset')['cross_regional_accuracy'].mean()[best_max]:.4f}")

    # Best by min_samples
    best_min = df.groupby('min_samples')['cross_regional_accuracy'].mean().idxmax()
    print(f"[STATS] BEST MIN_SAMPLES (averaged): {best_min}")
    print(f"   Mean Cross-Regional: {df.groupby('min_samples')['cross_regional_accuracy'].mean()[best_min]:.4f}")
    
    # Check if results are stable
    top_5 = df.head(5)
    std_dev = top_5['cross_regional_accuracy'].std()
    
    print(f"\n[CHECK] STABILITY CHECK:")
    print(f"   Top 5 std dev: {std_dev:.4f}")

    if std_dev < 0.01:
        print(f"   [OK] Results are very stable - clear winner")
    elif std_dev < 0.02:
        print(f"   [WARNING] Moderate variance - several good options")
    else:
        print(f"   [ERROR] High variance - results may be noisy")
        print(f"      Consider: More data or simpler model")


def save_results(df: pd.DataFrame, filename: str = "offset_optimization_results.csv"):
    """Save results to CSV"""
    df.to_csv(filename, index=False)
    print(f"\n[SAVED] Results saved to: {filename}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Run offset hyperparameter optimization"""
    print("Loading matches...")
    loader = MatchDataLoader()
    matches = loader.get_matches_as_dicts()
    print(f"[OK] Loaded {len(matches)} matches\n")
    
    # Choose search type
    print("Search options:")
    print("  1. Quick search (3×3×2 = 18 configs, ~1 min)")
    print("  2. Full search (4×4×3 = 48 configs, ~3 min)")
    
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
