"""
Performance Metrics for ELO Systems
Calculates accuracy, calibration, and other metrics
"""

import numpy as np
from typing import List, Dict, Tuple
from collections import defaultdict


class MetricsCalculator:
    """
    Calculates performance metrics for ELO prediction systems
    """
    
    @staticmethod
    def calculate_accuracy(predictions: List[Dict]) -> float:
        """
        Calculate prediction accuracy
        
        Args:
            predictions: List of prediction dicts with 'predicted' and 'actual' keys
            
        Returns:
            Accuracy as float (0.0 to 1.0)
        """
        if not predictions:
            return 0.0
        
        correct = sum(1 for p in predictions if p['predicted'] == p['actual'])
        return correct / len(predictions)
    
    @staticmethod
    def calculate_brier_score(predictions: List[Dict]) -> float:
        """
        Calculate Brier score (calibration metric)
        Lower is better (0.0 = perfect calibration)
        
        Args:
            predictions: List with 'probability' and 'outcome' (0 or 1)
            
        Returns:
            Brier score
        """
        if not predictions:
            return 1.0
        
        scores = [(p['probability'] - p['outcome']) ** 2 for p in predictions]
        return np.mean(scores)
    
    @staticmethod
    def calculate_log_loss(predictions: List[Dict]) -> float:
        """
        Calculate logarithmic loss
        Lower is better
        
        Args:
            predictions: List with 'probability' and 'outcome' (0 or 1)
            
        Returns:
            Log loss
        """
        if not predictions:
            return float('inf')
        
        # Clip probabilities to avoid log(0)
        epsilon = 1e-15
        
        losses = []
        for p in predictions:
            prob = np.clip(p['probability'], epsilon, 1 - epsilon)
            outcome = p['outcome']
            loss = -(outcome * np.log(prob) + (1 - outcome) * np.log(1 - prob))
            losses.append(loss)
        
        return np.mean(losses)
    
    @staticmethod
    def calculate_confidence_calibration(predictions: List[Dict], n_bins: int = 10) -> Dict:
        """
        Calculate calibration curve
        Groups predictions by confidence and checks if predicted probability matches actual outcome rate
        
        Args:
            predictions: List with 'probability' and 'outcome'
            n_bins: Number of bins for calibration curve
            
        Returns:
            Dictionary with calibration data
        """
        if not predictions:
            return {'bins': [], 'predicted': [], 'actual': [], 'counts': []}
        
        # Sort predictions by probability
        sorted_preds = sorted(predictions, key=lambda x: x['probability'])
        
        # Create bins
        bin_size = len(sorted_preds) // n_bins
        
        bins = []
        predicted_probs = []
        actual_rates = []
        counts = []
        
        for i in range(n_bins):
            start_idx = i * bin_size
            end_idx = start_idx + bin_size if i < n_bins - 1 else len(sorted_preds)
            
            bin_preds = sorted_preds[start_idx:end_idx]
            
            if bin_preds:
                avg_prob = np.mean([p['probability'] for p in bin_preds])
                actual_rate = np.mean([p['outcome'] for p in bin_preds])
                
                bins.append(f"{avg_prob:.1%}")
                predicted_probs.append(avg_prob)
                actual_rates.append(actual_rate)
                counts.append(len(bin_preds))
        
        return {
            'bins': bins,
            'predicted': predicted_probs,
            'actual': actual_rates,
            'counts': counts
        }
    
    @staticmethod
    def calculate_elo_statistics(elo_changes: List[float]) -> Dict:
        """
        Calculate statistics on ELO changes
        
        Args:
            elo_changes: List of ELO changes (deltas)
            
        Returns:
            Dictionary with statistics
        """
        if not elo_changes:
            return {}
        
        changes_abs = [abs(c) for c in elo_changes]
        
        return {
            'mean_change': np.mean(changes_abs),
            'median_change': np.median(changes_abs),
            'std_change': np.std(changes_abs),
            'min_change': np.min(changes_abs),
            'max_change': np.max(changes_abs),
            'total_changes': len(elo_changes)
        }
    
    @staticmethod
    def calculate_per_league_accuracy(predictions: List[Dict]) -> Dict:
        """
        Calculate accuracy per league
        
        Args:
            predictions: List with 'predicted', 'actual', 'league'
            
        Returns:
            Dictionary with per-league accuracy
        """
        league_stats = defaultdict(lambda: {'correct': 0, 'total': 0})
        
        for p in predictions:
            league = p.get('league', 'Unknown')
            league_stats[league]['total'] += 1
            if p['predicted'] == p['actual']:
                league_stats[league]['correct'] += 1
        
        return {
            league: {
                'accuracy': stats['correct'] / stats['total'] if stats['total'] > 0 else 0.0,
                'total_matches': stats['total']
            }
            for league, stats in league_stats.items()
        }
    
    @staticmethod
    def compare_systems(system1_preds: List[Dict], system2_preds: List[Dict], 
                       names: Tuple[str, str] = ('System 1', 'System 2')) -> Dict:
        """
        Compare two prediction systems
        
        Args:
            system1_preds: Predictions from system 1
            system2_preds: Predictions from system 2
            names: Names of the systems
            
        Returns:
            Comparison dictionary
        """
        acc1 = MetricsCalculator.calculate_accuracy(system1_preds)
        acc2 = MetricsCalculator.calculate_accuracy(system2_preds)
        
        brier1 = MetricsCalculator.calculate_brier_score(system1_preds)
        brier2 = MetricsCalculator.calculate_brier_score(system2_preds)
        
        return {
            names[0]: {
                'accuracy': acc1,
                'brier_score': brier1,
                'total_predictions': len(system1_preds)
            },
            names[1]: {
                'accuracy': acc2,
                'brier_score': brier2,
                'total_predictions': len(system2_preds)
            },
            'difference': {
                'accuracy_delta': acc2 - acc1,
                'accuracy_delta_percentage_points': (acc2 - acc1) * 100,
                'brier_delta': brier2 - brier1,
                'winner_by_accuracy': names[1] if acc2 > acc1 else names[0],
                'winner_by_calibration': names[1] if brier2 < brier1 else names[0]
            }
        }


def print_metrics_report(predictions: List[Dict], system_name: str = "System") -> None:
    """
    Print comprehensive metrics report
    
    Args:
        predictions: Predictions list
        system_name: Name of the system being evaluated
    """
    calc = MetricsCalculator()
    
    print("="*60)
    print(f"{system_name} PERFORMANCE METRICS")
    print("="*60)
    
    accuracy = calc.calculate_accuracy(predictions)
    print(f"\n📊 Accuracy: {accuracy:.2%}")
    
    # Brier score (if probabilities available)
    if predictions and 'probability' in predictions[0]:
        brier = calc.calculate_brier_score(predictions)
        print(f"📊 Brier Score: {brier:.4f} (lower is better)")
        
        log_loss = calc.calculate_log_loss(predictions)
        print(f"📊 Log Loss: {log_loss:.4f} (lower is better)")
    
    # ELO statistics (if available)
    if predictions and 'elo_change' in predictions[0]:
        elo_changes = [p['elo_change'] for p in predictions]
        elo_stats = calc.calculate_elo_statistics(elo_changes)
        
        print(f"\n⚖️  ELO STATISTICS:")
        print(f"  Mean change: {elo_stats['mean_change']:.1f}")
        print(f"  Median change: {elo_stats['median_change']:.1f}")
        print(f"  Std dev: {elo_stats['std_change']:.1f}")
        print(f"  Range: {elo_stats['min_change']:.1f} - {elo_stats['max_change']:.1f}")
    
    # Per-league accuracy (if available)
    if predictions and 'league' in predictions[0]:
        league_acc = calc.calculate_per_league_accuracy(predictions)
        
        print(f"\n🌍 PER-LEAGUE ACCURACY:")
        for league, stats in sorted(league_acc.items(), key=lambda x: x[1]['accuracy'], reverse=True):
            print(f"  {league}: {stats['accuracy']:.2%} ({stats['total_matches']} matches)")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    # Test with sample data
    sample_predictions = [
        {'predicted': 'T1', 'actual': 'T1', 'probability': 0.75, 'outcome': 1},
        {'predicted': 'GenG', 'actual': 'GenG', 'probability': 0.65, 'outcome': 1},
        {'predicted': 'T1', 'actual': 'DK', 'probability': 0.55, 'outcome': 0},
        {'predicted': 'WBG', 'actual': 'WBG', 'probability': 0.80, 'outcome': 1},
    ]
    
    print_metrics_report(sample_predictions, "Test System")
