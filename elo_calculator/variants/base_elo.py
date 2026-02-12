"""
Base ELO Calculator - Clean Baseline Implementation
NO form factor, NO temporal decay, NO scale factor
Pure ELO algorithm as reference baseline
"""

import numpy as np
from typing import Dict, List, Optional
from collections import defaultdict
import config


class BaseEloCalculator:
    """
    Pure ELO rating system without any additional features
    This serves as the baseline for comparison
    """
    
    def __init__(self, K: float = None, initial_elo: float = None):
        """
        Initialize ELO calculator
        
        Args:
            K: K-factor (default from config)
            initial_elo: Starting ELO for new teams (default from config)
        """
        self.K = K if K is not None else config.K_FACTOR
        self.initial_elo = initial_elo if initial_elo is not None else config.INITIAL_ELO
        self.ratings = defaultdict(lambda: self.initial_elo)
        self.history = []  # Track all updates for analysis
    
    def get_elo(self, team: str) -> float:
        """
        Get current ELO rating for a team
        
        Args:
            team: Team name
            
        Returns:
            Current ELO rating
        """
        return self.ratings[team]
    
    def expected_score(self, elo_a: float, elo_b: float) -> float:
        """
        Calculate expected score using standard ELO formula
        
        Args:
            elo_a: ELO of team A
            elo_b: ELO of team B
            
        Returns:
            Expected score for team A (0.0 to 1.0)
        """
        return 1 / (1 + 10 ** ((elo_b - elo_a) / 400))
    
    def update(self, match: Dict) -> Dict:
        """
        Process one match and update ELO ratings
        
        Args:
            match: Match dictionary with:
                - team1: First team name
                - team2: Second team name
                - winner: Winning team name
                - (optional) date, score1, score2, etc.
        
        Returns:
            Dictionary with update details:
                - team1_old_elo: ELO before update
                - team1_new_elo: ELO after update
                - team2_old_elo: ELO before update
                - team2_new_elo: ELO after update
                - delta1: ELO change for team1
                - delta2: ELO change for team2
                - expected1: Expected score for team1
                - expected2: Expected score for team2
                - predicted_winner: Team with higher ELO
                - correct: Whether prediction was correct
        """
        team1 = match['team1']
        team2 = match['team2']
        winner = match['winner']
        
        # Get current ratings
        elo1 = self.get_elo(team1)
        elo2 = self.get_elo(team2)
        
        # Calculate expected scores
        E1 = self.expected_score(elo1, elo2)
        E2 = 1 - E1
        
        # Actual scores (1 for win, 0 for loss)
        S1 = 1.0 if winner == team1 else 0.0
        S2 = 1.0 - S1
        
        # Calculate rating changes
        delta1 = self.K * (S1 - E1)
        delta2 = self.K * (S2 - E2)
        
        # Update ratings
        new_elo1 = elo1 + delta1
        new_elo2 = elo2 + delta2
        
        self.ratings[team1] = new_elo1
        self.ratings[team2] = new_elo2
        
        # Prediction
        predicted_winner = team1 if elo1 > elo2 else team2
        correct = (predicted_winner == winner)
        
        # Create update record
        update_record = {
            'team1': team1,
            'team2': team2,
            'team1_old_elo': elo1,
            'team1_new_elo': new_elo1,
            'team2_old_elo': elo2,
            'team2_new_elo': new_elo2,
            'delta1': delta1,
            'delta2': delta2,
            'expected1': E1,
            'expected2': E2,
            'predicted_winner': predicted_winner,
            'actual_winner': winner,
            'correct': correct,
            'win_probability': max(E1, E2)
        }
        
        # Add optional match data
        if 'date' in match:
            update_record['date'] = match['date']
        if 'score1' in match and 'score2' in match:
            update_record['score'] = f"{match['score1']}-{match['score2']}"
        
        # Store in history
        self.history.append(update_record)
        
        return update_record
    
    def process_matches(self, matches: List[Dict]) -> List[Dict]:
        """
        Process multiple matches in sequence
        
        Args:
            matches: List of match dictionaries
            
        Returns:
            List of update records
        """
        results = []
        for match in matches:
            result = self.update(match)
            results.append(result)
        return results
    
    def predict(self, team1: str, team2: str) -> Dict:
        """
        Predict outcome of a match without updating ratings
        
        Args:
            team1: First team name
            team2: Second team name
            
        Returns:
            Prediction dictionary with:
                - predicted_winner: Team more likely to win
                - team1_win_prob: Probability team1 wins
                - team2_win_prob: Probability team2 wins
                - elo_diff: ELO difference
                - confidence: Confidence level (High/Medium/Low)
        """
        elo1 = self.get_elo(team1)
        elo2 = self.get_elo(team2)
        
        prob1 = self.expected_score(elo1, elo2)
        prob2 = 1 - prob1
        
        predicted_winner = team1 if prob1 > 0.5 else team2
        confidence_level = max(prob1, prob2)
        
        if confidence_level >= 0.75:
            confidence = "High"
        elif confidence_level >= 0.60:
            confidence = "Medium"
        else:
            confidence = "Low"
        
        return {
            'team1': team1,
            'team2': team2,
            'team1_elo': elo1,
            'team2_elo': elo2,
            'predicted_winner': predicted_winner,
            'team1_win_prob': prob1,
            'team2_win_prob': prob2,
            'elo_diff': abs(elo1 - elo2),
            'confidence': confidence,
            'confidence_value': confidence_level
        }
    
    def get_leaderboard(self, min_elo: float = None) -> List[Dict]:
        """
        Get current leaderboard sorted by ELO
        
        Args:
            min_elo: Optional minimum ELO filter
            
        Returns:
            List of teams with rankings
        """
        teams = []
        for team, elo in self.ratings.items():
            if min_elo is None or elo >= min_elo:
                teams.append({'team': team, 'elo': elo})
        
        # Sort by ELO descending
        teams.sort(key=lambda x: x['elo'], reverse=True)
        
        # Add rankings
        for i, team in enumerate(teams):
            team['rank'] = i + 1
        
        return teams
    
    def get_accuracy(self) -> float:
        """
        Calculate overall prediction accuracy
        
        Returns:
            Accuracy as float (0.0 to 1.0)
        """
        if not self.history:
            return 0.0
        
        correct = sum(1 for h in self.history if h['correct'])
        return correct / len(self.history)
    
    def get_statistics(self) -> Dict:
        """
        Get comprehensive statistics about the system
        
        Returns:
            Dictionary with statistics
        """
        if not self.history:
            return {
                'total_matches': 0,
                'accuracy': 0.0
            }
        
        deltas = [abs(h['delta1']) for h in self.history]
        win_probs = [h['win_probability'] for h in self.history]
        
        return {
            'total_matches': len(self.history),
            'total_teams': len(self.ratings),
            'accuracy': self.get_accuracy(),
            'mean_elo_change': np.mean(deltas),
            'median_elo_change': np.median(deltas),
            'std_elo_change': np.std(deltas),
            'mean_confidence': np.mean(win_probs),
            'k_factor': self.K,
            'initial_elo': self.initial_elo
        }
    
    def reset(self):
        """Reset all ratings and history"""
        self.ratings.clear()
        self.history.clear()


def train_and_evaluate(matches: List[Dict], train_ratio: float = 0.7) -> Dict:
    """
    Train on first portion, evaluate on rest
    
    Args:
        matches: List of matches
        train_ratio: Portion to use for training (e.g., 0.7 = 70%)
        
    Returns:
        Dictionary with train and test results
    """
    split_idx = int(len(matches) * train_ratio)
    train_matches = matches[:split_idx]
    test_matches = matches[split_idx:]
    
    # Train
    calculator = BaseEloCalculator()
    train_results = calculator.process_matches(train_matches)
    
    # Evaluate on test set
    test_results = []
    for match in test_matches:
        # Predict before updating
        prediction = calculator.predict(match['team1'], match['team2'])
        
        # Update ratings
        update = calculator.update(match)
        
        test_results.append({
            **prediction,
            'actual_winner': match['winner'],
            'correct': prediction['predicted_winner'] == match['winner']
        })
    
    # Calculate metrics
    train_accuracy = sum(r['correct'] for r in train_results) / len(train_results)
    test_accuracy = sum(r['correct'] for r in test_results) / len(test_results)
    
    return {
        'train_size': len(train_matches),
        'test_size': len(test_matches),
        'train_accuracy': train_accuracy,
        'test_accuracy': test_accuracy,
        'overfitting': train_accuracy - test_accuracy,
        'final_stats': calculator.get_statistics()
    }


if __name__ == "__main__":
    # Test with sample data
    from core.data_loader import MatchDataLoader
    
    print("="*60)
    print("BASE ELO CALCULATOR - TEST")
    print("="*60)
    
    # Load data
    print("\nLoading matches...")
    loader = MatchDataLoader()
    matches = loader.get_matches_as_dicts()
    print(f"✓ Loaded {len(matches)} matches")
    
    # Train and evaluate
    print("\nTraining and evaluating...")
    results = train_and_evaluate(matches, train_ratio=0.7)
    
    print(f"\n📊 RESULTS:")
    print(f"  Train size: {results['train_size']} matches")
    print(f"  Test size: {results['test_size']} matches")
    print(f"  Train accuracy: {results['train_accuracy']:.2%}")
    print(f"  Test accuracy: {results['test_accuracy']:.2%}")
    print(f"  Overfitting: {results['overfitting']:.2%}")
    
    print(f"\n⚙️  SYSTEM STATS:")
    stats = results['final_stats']
    print(f"  Total teams: {stats['total_teams']}")
    print(f"  Mean ELO change: {stats['mean_elo_change']:.1f}")
    print(f"  K-factor: {stats['k_factor']}")
    
    print("\n" + "="*60)


# Wrapper class for backwards compatibility with validation scripts
class BaseElo:
    """
    Backwards-compatible wrapper for BaseEloCalculator
    Provides the old API expected by validation scripts
    """
    def __init__(self, k_factor: float = 24, initial_elo: float = 1500,
                 use_scale_factors: bool = False, scale_factors: dict = None):
        # Create underlying calculator (ignores scale_factors since it's base ELO)
        self.calculator = BaseEloCalculator(K=k_factor, initial_elo=initial_elo)
        self.k_factor = k_factor
        self.initial_elo = initial_elo

    def update_ratings(self, team1: str, team2: str, score1: int, score2: int):
        """Update ratings"""
        match = {
            'team1': team1,
            'team2': team2,
            'score1': score1,
            'score2': score2,
            'winner': team1 if score1 > score2 else team2
        }
        self.calculator.update(match)

    def predict(self, team1: str, team2: str):
        """Predict match outcome"""
        return self.calculator.predict(team1, team2)

    def get_elo(self, team: str) -> float:
        """Get current ELO"""
        return self.calculator.get_elo(team)

    def get_rating(self, team: str) -> float:
        """Get current rating (alias for get_elo)"""
        return self.get_elo(team)
