"""
Test Regional Offsets - Validation Script
Compares Baseline vs With Offsets, shows Regional breakdown
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.data_loader import MatchDataLoader
from core.region_mapper import RegionMapper
from variants.with_scale_factor import ScaleFactorEloCalculator
from variants.with_dynamic_offsets import DynamicOffsetCalculator
from validation.temporal_split import TemporalValidator


def analyze_by_region(matches, predictions, region_mapper):
    """Analyze accuracy by region type"""
    regional = []
    cross_regional = []
    
    for i, match in enumerate(matches):
        pred = predictions[i]
        
        is_cross = region_mapper.is_cross_region(
            match['team1'], 
            match['team2'], 
            use_parent=False
        )
        
        if is_cross:
            cross_regional.append(pred)
        else:
            regional.append(pred)
    
    regional_acc = sum(p['correct'] for p in regional) / len(regional) if regional else 0
    cross_acc = sum(p['correct'] for p in cross_regional) / len(cross_regional) if cross_regional else 0
    
    return {
        'regional': {
            'count': len(regional),
            'accuracy': regional_acc
        },
        'cross_regional': {
            'count': len(cross_regional),
            'accuracy': cross_acc
        }
    }


def test_regional_offsets():
    """Test offset system with temporal validation"""
    print("\n" + "="*70)
    print(" "*15 + "REGIONAL OFFSET VALIDATION TEST")
    print("="*70)
    
    # Load data
    print("\nLoading matches...")
    loader = MatchDataLoader()
    matches = loader.get_matches_as_dicts()
    print(f"✓ Loaded {len(matches)} matches")
    
    # Setup
    validator = TemporalValidator(train_ratio=0.7)
    region_mapper = RegionMapper()
    
    # Test 1: Baseline (Scale Factor, no offsets)
    print("\n" + "="*70)
    print("TEST 1: BASELINE (K=24, Conservative Scale, NO Offsets)")
    print("="*70)
    
    baseline_result = validator.validate_variant(
        ScaleFactorEloCalculator,
        matches,
        "Baseline (no offsets)",
        K=24,
        scale_factors={
            '1-0': 1.00,
            '2-0': 1.00,
            '2-1': 0.50,
            '3-0': 1.00,
            '3-1': 0.90,
            '3-2': 0.80,
        }
    )
    
    # Analyze by region
    baseline_split = analyze_by_region(
        validator.split_matches(matches)[1],  # test matches
        baseline_result['all_predictions'],
        region_mapper
    )
    
    print(f"\n📊 BASELINE RESULTS:")
    print(f"  Overall Test Accuracy: {baseline_result['test_accuracy']:.2%}")
    print(f"  Regional Matches ({baseline_split['regional']['count']}): "
          f"{baseline_split['regional']['accuracy']:.2%}")
    print(f"  Cross-Regional ({baseline_split['cross_regional']['count']}): "
          f"{baseline_split['cross_regional']['accuracy']:.2%}")
    print(f"  Gap: {(baseline_split['regional']['accuracy'] - baseline_split['cross_regional']['accuracy'])*100:.2f}pp")
    
    # Test 2: With Offsets
    print("\n" + "="*70)
    print("TEST 2: WITH DYNAMIC OFFSETS")
    print("="*70)
    
    offset_result = validator.validate_variant(
        DynamicOffsetCalculator,
        matches,
        "Dynamic Offsets"
    )
    
    # Analyze by region
    offset_split = analyze_by_region(
        validator.split_matches(matches)[1],  # test matches  
        offset_result['all_predictions'],
        region_mapper
    )
    
    print(f"\n📊 WITH OFFSETS RESULTS:")
    print(f"  Overall Test Accuracy: {offset_result['test_accuracy']:.2%}")
    print(f"  Regional Matches ({offset_split['regional']['count']}): "
          f"{offset_split['regional']['accuracy']:.2%}")
    print(f"  Cross-Regional ({offset_split['cross_regional']['count']}): "
          f"{offset_split['cross_regional']['accuracy']:.2%}")
    print(f"  Gap: {(offset_split['regional']['accuracy'] - offset_split['cross_regional']['accuracy'])*100:.2f}pp")
    
    # Show final offsets
    print(f"\n📈 FINAL OFFSETS:")
    calc = offset_result['calculator']
    offsets_df = calc.get_current_offsets()
    print(offsets_df.to_string(index=False))
    
    # Comparison
    print("\n" + "="*70)
    print("COMPARISON")
    print("="*70)
    
    print(f"\n🎯 OVERALL ACCURACY:")
    print(f"  Baseline: {baseline_result['test_accuracy']:.4f}")
    print(f"  With Offsets: {offset_result['test_accuracy']:.4f}")
    print(f"  Improvement: {(offset_result['test_accuracy'] - baseline_result['test_accuracy'])*100:+.2f}pp")
    
    print(f"\n🌍 CROSS-REGIONAL IMPROVEMENT:")
    baseline_cross = baseline_split['cross_regional']['accuracy']
    offset_cross = offset_split['cross_regional']['accuracy']
    print(f"  Baseline: {baseline_cross:.4f}")
    print(f"  With Offsets: {offset_cross:.4f}")
    print(f"  Improvement: {(offset_cross - baseline_cross)*100:+.2f}pp")
    
    # Recommendation
    print(f"\n💡 RECOMMENDATION:")
    
    cross_improvement = (offset_cross - baseline_cross) * 100
    overall_improvement = (offset_result['test_accuracy'] - baseline_result['test_accuracy']) * 100
    
    if cross_improvement > 2.0 and overall_improvement > 0.5:
        print(f"  ✅ USE OFFSETS!")
        print(f"     Cross-regional improvement: +{cross_improvement:.2f}pp")
        print(f"     Overall improvement: +{overall_improvement:.2f}pp")
    elif cross_improvement > 1.0:
        print(f"  ⚖️  OFFSETS HELP MODERATELY")
        print(f"     Cross-regional improvement: +{cross_improvement:.2f}pp")
        print(f"     Consider using for international tournaments only")
    else:
        print(f"  ❌ OFFSETS DON'T HELP ENOUGH")
        print(f"     Cross-regional improvement: +{cross_improvement:.2f}pp")
        print(f"     Stick with baseline")
    
    # Check if offsets are reasonable
    print(f"\n⚠️  OFFSET SANITY CHECK:")
    max_offset = offsets_df['Offset'].abs().max()
    min_confidence = offsets_df['Confidence'].min()
    
    if max_offset > 100:
        print(f"  ⚠️  WARNING: Max offset is {max_offset:.1f} (> 100)")
        print(f"     Offsets may be too extreme!")
        print(f"     Consider increasing regularization")
    elif max_offset > 75:
        print(f"  ⚠️  CAUTION: Max offset is {max_offset:.1f}")
        print(f"     Within range but on the high side")
    else:
        print(f"  ✅ Max offset {max_offset:.1f} is reasonable")
    
    if min_confidence < 0.5:
        print(f"  ⚠️  WARNING: Min confidence is {min_confidence:.2f} (< 0.5)")
        print(f"     Offsets may be unreliable")
        print(f"     Need more cross-regional matches")
    else:
        print(f"  ✅ Confidence levels are good (min: {min_confidence:.2f})")
    
    return {
        'baseline': baseline_result,
        'with_offsets': offset_result,
        'baseline_split': baseline_split,
        'offset_split': offset_split
    }


if __name__ == "__main__":
    results = test_regional_offsets()
    
    print("\n" + "="*70)
    print("✅ VALIDATION COMPLETE")
    print("="*70)
