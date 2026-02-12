"""
System Test - Tests the complete ELO system
Run this to verify everything works!
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.data_loader import MatchDataLoader
from core.validator import validate_and_report
from core.metrics import print_metrics_report
from variants.base_elo import BaseEloCalculator
from validation.temporal_split import TemporalValidator, print_validation_report

def test_data_loading():
    """Test 1: Can we load data from Google Sheets?"""
    print("\n" + "="*60)
    print("TEST 1: DATA LOADING")
    print("="*60)
    
    try:
        loader = MatchDataLoader()
        df = loader.load_matches()
        
        print(f"✅ SUCCESS!")
        print(f"   Loaded {len(df)} matches")
        print(f"   Date range: {df['Date'].min().date()} to {df['Date'].max().date()}")
        print(f"   Unique teams: {len(loader.get_unique_teams())}")
        
        return True, df
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False, None


def test_data_validation(df):
    """Test 2: Is the data quality good?"""
    print("\n" + "="*60)
    print("TEST 2: DATA VALIDATION")
    print("="*60)
    
    try:
        validate_and_report(df)
        print("\n✅ Validation complete!")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_base_elo(matches):
    """Test 3: Does base ELO calculator work?"""
    print("\n" + "="*60)
    print("TEST 3: BASE ELO CALCULATOR")
    print("="*60)
    
    try:
        calculator = BaseEloCalculator()
        
        # Process first 10 matches
        print("\nProcessing first 10 matches...")
        for i, match in enumerate(matches[:10]):
            result = calculator.update(match)
            print(f"  Match {i+1}: {result['team1']} vs {result['team2']} → {result['actual_winner']} wins")
            print(f"    Prediction: {result['predicted_winner']} ({'✓' if result['correct'] else '✗'})")
        
        # Get leaderboard
        print("\nCurrent leaderboard (top 5):")
        leaderboard = calculator.get_leaderboard()
        for team in leaderboard[:5]:
            print(f"  {team['rank']}. {team['team']}: {team['elo']:.0f}")
        
        print("\n✅ Base ELO works!")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_temporal_validation(matches):
    """Test 4: Does temporal validation work?"""
    print("\n" + "="*60)
    print("TEST 4: TEMPORAL VALIDATION")
    print("="*60)
    
    try:
        validator = TemporalValidator(train_ratio=0.7)
        result = validator.validate_variant(
            BaseEloCalculator,
            matches,
            "Base ELO Test"
        )
        
        print_validation_report(result)
        
        print("\n✅ Temporal validation works!")
        return True, result
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*70)
    print(" "*20 + "SYSTEM TEST SUITE")
    print("="*70)
    
    # Test 1: Data loading
    success, df = test_data_loading()
    if not success:
        print("\n❌ CRITICAL: Data loading failed. Cannot continue.")
        return False
    
    # Convert to match dicts
    loader = MatchDataLoader()
    matches = loader.get_matches_as_dicts()
    
    # Test 2: Data validation
    test_data_validation(df)
    
    # Test 3: Base ELO
    if not test_base_elo(matches):
        print("\n❌ Base ELO test failed")
        return False
    
    # Test 4: Temporal validation
    success, result = test_temporal_validation(matches)
    if not success:
        print("\n❌ Temporal validation failed")
        return False
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print("\n✅ ALL TESTS PASSED!")
    print(f"\nYour system is ready to use!")
    print(f"  • {len(matches)} matches loaded")
    print(f"  • {len(loader.get_unique_teams())} teams tracked")
    print(f"  • Test accuracy: {result['test_accuracy']:.2%}")
    print("\nNext steps:")
    print("  1. Create more ELO variants (with form, scale factor, etc.)")
    print("  2. Compare variants using validation/compare.py")
    print("  3. Integrate best variant into Streamlit dashboard")
    
    return True


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
