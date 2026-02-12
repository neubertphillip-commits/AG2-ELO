"""
Temporal Validation Framework
Tests ELO systems on chronologically split data to measure true predictive power
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any
from datetime import datetime
import config


class TemporalValidator:
    """
    Validates ELO systems using temporal (chronological) train/test splits
    This is the CORRECT way to validate - not random splits!
    """
    
    def __init__(self, train_ratio: float = None):
        """
        Initialize validator
        
        Args:
            train_ratio: Portion of data for training (default from config)
        """
        self.train_ratio = train_ratio if train_ratio is not None else config.TRAIN_TEST_SPLIT
    
    def split_matches(self, matches: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Split matches chronologically
        
        Args:
            matches: List of matches (must be sorted by date)
            
        Returns:
            (train_matches, test_matches)
        """
        # Ensure chronological order
        matches_sorted = sorted(matches, key=lambda m: m['date'])
        
        split_idx = int(len(matches_sorted) * self.train_ratio)
        
        train = matches_sorted[:split_idx]
        test = matches_sorted[split_idx:]
        
        return train, test
    
    def validate_variant(self, variant_class: Any, matches: List[Dict], 
                        variant_name: str = None, **variant_kwargs) -> Dict:
        """
        Validate a specific ELO variant
        
        Args:
            variant_class: ELO calculator class (must have .update() and .predict() methods)
            matches: List of all matches
            variant_name: Name for reporting
            **variant_kwargs: Arguments to pass to variant constructor
            
        Returns:
            Validation results dictionary
        """
        variant_name = variant_name or variant_class.__name__
        
        # Split data
        train_matches, test_matches = self.split_matches(matches)
        
        # Initialize calculator
        calculator = variant_class(**variant_kwargs)
        
        # TRAINING PHASE
        print(f"\n{'='*60}")
        print(f"VALIDATING: {variant_name}")
        print(f"{'='*60}")
        print(f"Training on {len(train_matches)} matches...")
        
        train_results = []
        for match in train_matches:
            result = calculator.update(match)
            train_results.append(result)
        
        train_accuracy = sum(r['correct'] for r in train_results) / len(train_results)
        
        print(f"[OK] Train accuracy: {train_accuracy:.2%}")
        
        # TEST PHASE (CRITICAL!)
        print(f"Testing on {len(test_matches)} matches (UNSEEN DATA)...")
        
        test_results = []
        test_predictions = []
        
        for match in test_matches:
            # Predict BEFORE updating (this is the true test!)
            prediction = calculator.predict(match['team1'], match['team2'])
            
            # Check if correct
            correct = (prediction['predicted_winner'] == match['winner'])
            
            test_predictions.append({
                'predicted': prediction['predicted_winner'],
                'actual': match['winner'],
                'correct': correct,
                'probability': prediction['team1_win_prob'] if match['winner'] == match['team1'] else prediction['team2_win_prob'],
                'outcome': 1 if correct else 0,
                'confidence': prediction['confidence_value'],
                'date': match.get('date')
            })
            
            # NOW update the ratings for next prediction
            update = calculator.update(match)
            test_results.append(update)
        
        test_accuracy = sum(p['correct'] for p in test_predictions) / len(test_predictions)
        
        print(f"[OK] Test accuracy: {test_accuracy:.2%}")
        print(f"[OK] Overfitting: {(train_accuracy - test_accuracy):.2%}")
        
        # Calculate additional metrics
        brier_score = self._calculate_brier_score(test_predictions)
        
        # Confidence-based metrics
        high_conf_preds = [p for p in test_predictions if p['confidence'] >= 0.70]
        high_conf_acc = (sum(p['correct'] for p in high_conf_preds) / len(high_conf_preds)) if high_conf_preds else 0.0
        
        # Get split date for reference
        split_date = train_matches[-1]['date'] if 'date' in train_matches[-1] else None
        
        return {
            'variant_name': variant_name,
            'train_size': len(train_matches),
            'test_size': len(test_matches),
            'split_date': split_date,
            'train_accuracy': train_accuracy,
            'test_accuracy': test_accuracy,
            'overfitting': train_accuracy - test_accuracy,
            'brier_score': brier_score,
            'high_confidence_accuracy': high_conf_acc,
            'high_confidence_count': len(high_conf_preds),
            'all_predictions': test_predictions,
            'calculator': calculator  # Return for further analysis
        }
    
    def _calculate_brier_score(self, predictions: List[Dict]) -> float:
        """
        Calculate Brier score for calibration
        
        Args:
            predictions: List of predictions with 'probability' and 'outcome'
            
        Returns:
            Brier score (lower is better)
        """
        if not predictions:
            return 1.0
        
        scores = [(p['probability'] - p['outcome']) ** 2 for p in predictions]
        return np.mean(scores)
    
    def compare_variants(self, variant_configs: List[Dict], matches: List[Dict]) -> pd.DataFrame:
        """
        Compare multiple ELO variants
        
        Args:
            variant_configs: List of dicts with 'class', 'name', and 'kwargs'
            matches: List of matches
            
        Returns:
            DataFrame with comparison results
        """
        results = []
        
        for config in variant_configs:
            result = self.validate_variant(
                config['class'],
                matches,
                config.get('name'),
                **config.get('kwargs', {})
            )
            
            # Extract key metrics
            results.append({
                'Variant': result['variant_name'],
                'Train Accuracy': f"{result['train_accuracy']:.2%}",
                'Test Accuracy': f"{result['test_accuracy']:.2%}",
                'Overfitting': f"{result['overfitting']:.2%}",
                'Brier Score': f"{result['brier_score']:.4f}",
                'High Conf Acc': f"{result['high_confidence_accuracy']:.2%}",
                'Test Size': result['test_size']
            })
        
        df = pd.DataFrame(results)
        
        # Sort by test accuracy (what matters!)
        df['_test_acc_numeric'] = [float(r['test_accuracy'].strip('%'))/100 for r in results]
        df = df.sort_values('_test_acc_numeric', ascending=False)
        df = df.drop('_test_acc_numeric', axis=1)
        
        return df
    
    def rolling_validation(self, variant_class: Any, matches: List[Dict], 
                          window_size: int = 100, step_size: int = 50,
                          **variant_kwargs) -> pd.DataFrame:
        """
        Rolling window validation to see performance over time
        
        Args:
            variant_class: ELO calculator class
            matches: List of matches
            window_size: Size of test window
            step_size: How many matches to step forward
            **variant_kwargs: Arguments for variant
            
        Returns:
            DataFrame with rolling accuracy
        """
        results = []
        
        # Need enough data for at least one window
        if len(matches) < window_size:
            raise ValueError(f"Not enough matches ({len(matches)}) for window size {window_size}")
        
        # Start from minimum training data
        min_train = int(len(matches) * 0.3)
        
        for start_idx in range(min_train, len(matches) - window_size, step_size):
            train = matches[:start_idx]
            test = matches[start_idx:start_idx + window_size]
            
            # Train
            calculator = variant_class(**variant_kwargs)
            for match in train:
                calculator.update(match)
            
            # Test
            correct = 0
            for match in test:
                pred = calculator.predict(match['team1'], match['team2'])
                if pred['predicted_winner'] == match['winner']:
                    correct += 1
                calculator.update(match)
            
            accuracy = correct / len(test)
            
            results.append({
                'end_date': test[-1].get('date'),
                'train_size': len(train),
                'test_size': len(test),
                'accuracy': accuracy
            })
        
        return pd.DataFrame(results)


def print_validation_report(result: Dict) -> None:
    """
    Print formatted validation report
    
    Args:
        result: Validation result dictionary
    """
    print("\n" + "="*60)
    print(f"VALIDATION REPORT: {result['variant_name']}")
    print("="*60)
    
    print(f"\n[DATA] DATA SPLIT:")
    print(f"  Train: {result['train_size']} matches ({result['train_size']/(result['train_size']+result['test_size']):.0%})")
    print(f"  Test:  {result['test_size']} matches ({result['test_size']/(result['train_size']+result['test_size']):.0%})")
    if result['split_date']:
        print(f"  Split date: {result['split_date']}")
    
    print(f"\n🎯 ACCURACY:")
    print(f"  Train: {result['train_accuracy']:.2%}")
    print(f"  Test:  {result['test_accuracy']:.2%} ← THIS IS WHAT MATTERS!")
    
    overfitting_status = ""
    if result['overfitting'] < 0.02:
        overfitting_status = "✅ Excellent (no overfitting)"
    elif result['overfitting'] < 0.05:
        overfitting_status = "[WARNING]  Moderate"
    else:
        overfitting_status = "❌ High overfitting!"
    
    print(f"  Overfitting: {result['overfitting']:.2%} {overfitting_status}")
    
    print(f"\n📈 CALIBRATION:")
    print(f"  Brier Score: {result['brier_score']:.4f} (lower is better)")
    
    print(f"\n🎲 CONFIDENCE:")
    print(f"  High confidence (≥70%) predictions: {result['high_confidence_count']}")
    print(f"  High confidence accuracy: {result['high_confidence_accuracy']:.2%}")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    from core.data_loader import MatchDataLoader
    from variants.base_elo import BaseEloCalculator
    
    print("="*60)
    print("TEMPORAL VALIDATION - DEMO")
    print("="*60)
    
    # Load matches
    print("\nLoading matches...")
    loader = MatchDataLoader()
    matches = loader.get_matches_as_dicts()
    print(f"[OK] Loaded {len(matches)} matches")
    
    # Validate base ELO
    validator = TemporalValidator(train_ratio=0.7)
    result = validator.validate_variant(BaseEloCalculator, matches, "Base ELO")
    
    # Print report
    print_validation_report(result)
