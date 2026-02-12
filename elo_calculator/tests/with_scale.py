"""
System Test - WITH Scale Factors
Tests the optimized configuration
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from core.data_loader import MatchDataLoader
from variants.with_scale_factor import ScaleFactorEloCalculator
from validation.temporal_split import TemporalValidator, print_validation_report


# ============================================================================
# OPTIMIZED CONFIGURATION (from optimization results)
# ============================================================================

# Winner Configuration
BEST_K = 24
BEST_SCALE_FACTORS = {
    '1-0': 1.00,
    '2-0': 1.00,
    '2-1': 0.50,  # Conservative - strong reduction
    '3-0': 1.00,
    '3-1': 0.90,
    '3-2': 0.80,
}

# Alternative: Simplicity
SIMPLE_K = 16
SIMPLE_SCALE_FACTORS = None  # No scale factors


def test_optimized_config():
    """Test the optimized configuration"""
    print("\n" + "="*70)
    print(" "*15 + "OPTIMIZED CONFIGURATION TEST")
    print("="*70)
    
    # Load data
    print("\nLoading matches...")
    loader = MatchDataLoader()
    matches = loader.get_matches_as_dicts()
    print(f"✓ Loaded {len(matches)} matches")
    
    # Test both configurations
    validator = TemporalValidator(train_ratio=0.7)
    
    # Configuration 1: Winner (K=24, Conservative Scale)
    print("\n" + "="*70)
    print("CONFIGURATION 1: K=24 + Conservative Scale")
    print("="*70)
    
    result1 = validator.validate_variant(
        ScaleFactorEloCalculator,
        matches,
        variant_name="K=24, Conservative Scale",
        K=BEST_K,
        scale_factors=BEST_SCALE_FACTORS
    )
    
    print_validation_report(result1)
    
    # Get scale factor usage stats
    stats1 = result1['calculator'].get_statistics()
    print(f"\n📈 SCALE FACTOR USAGE:")
    for sf, count in sorted(stats1['scale_factor_distribution'].items()):
        percentage = (count / stats1['total_matches']) * 100
        print(f"  {sf:.2f}: {count} matches ({percentage:.1f}%)")
    
    # Configuration 2: Simple (K=16, No Scale)
    print("\n" + "="*70)
    print("CONFIGURATION 2: K=16 + No Scale (Simplicity)")
    print("="*70)
    
    result2 = validator.validate_variant(
        ScaleFactorEloCalculator,
        matches,
        variant_name="K=16, No Scale",
        K=SIMPLE_K,
        scale_factors=SIMPLE_SCALE_FACTORS
    )
    
    print_validation_report(result2)
    
    # Comparison
    print("\n" + "="*70)
    print("COMPARISON")
    print("="*70)
    
    print(f"\n📊 Test Accuracy:")
    print(f"  Config 1 (K=24, Conservative): {result1['test_accuracy']:.4f} ({result1['test_accuracy']*100:.2f}%)")
    print(f"  Config 2 (K=16, No Scale):     {result2['test_accuracy']:.4f} ({result2['test_accuracy']*100:.2f}%)")
    print(f"  Difference: {(result1['test_accuracy'] - result2['test_accuracy'])*100:+.2f} pp")
    
    print(f"\n⚖️  Overfitting:")
    print(f"  Config 1: {result1['overfitting']:.4f}")
    print(f"  Config 2: {result2['overfitting']:.4f}")
    
    print(f"\n📈 Brier Score (lower is better):")
    print(f"  Config 1: {result1['brier_score']:.4f}")
    print(f"  Config 2: {result2['brier_score']:.4f}")
    
    # Recommendation
    print(f"\n💡 RECOMMENDATION:")
    
    acc_diff = (result1['test_accuracy'] - result2['test_accuracy']) * 100
    
    if acc_diff > 0.5:
        print(f"  ✅ Use Config 1 (K=24, Conservative)")
        print(f"     +{acc_diff:.2f}pp accuracy is worth the complexity")
        recommended = "Config 1"
    elif acc_diff < -0.5:
        print(f"  ✅ Use Config 2 (K=16, No Scale)")
        print(f"     Simpler AND more accurate!")
        recommended = "Config 2"
    else:
        print(f"  ⚖️  Configs are similar ({acc_diff:+.2f}pp)")
        print(f"     Recommend Config 2 for simplicity")
        recommended = "Config 2"
    
    # Save recommendation to config
    print(f"\n📝 To use {recommended}, update config.py:")
    if recommended == "Config 1":
        print(f"""
config.py:
    K_FACTOR = {BEST_K}
    USE_SCALE_FACTORS = True
    SCALE_FACTORS = {{
        '1-0': 1.00,
        '2-0': 1.00,
        '2-1': 0.50,
        '3-0': 1.00,
        '3-1': 0.90,
        '3-2': 0.80,
    }}
        """)
    else:
        print(f"""
config.py:
    K_FACTOR = {SIMPLE_K}
    USE_SCALE_FACTORS = False
        """)
    
    return result1, result2


if __name__ == "__main__":
    try:
        result1, result2 = test_optimized_config()
        
        print("\n" + "="*70)
        print("✅ OPTIMIZATION TEST COMPLETE!")
        print("="*70)
        
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
