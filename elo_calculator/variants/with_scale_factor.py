"""
ELO Calculator with Scale Factor
Adjusts K-factor based on match closeness (Bo3/Bo5)
"""

import numpy as np
from typing import Dict, List, Optional
from collections import defaultdict
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import config


class ScaleFactorEloCalculator:
    """
    ELO rating system with scale factor for match closeness
    
    Scale Factor Logic:
    - Stomps (3-0, 2-0) use full K-factor
    - Close matches (3-2, 2-1) use reduced K-factor
    
    Rationale: A 3-0 win shows more dominance than a 3-2 win
    """
    
    def __init__(self, K: float = None, initial_elo: float = None,
                 scale_factors: Dict = None):
        """
        Initialize ELO calculator with scale factors
        
        Args:
            K: Base K-factor (default from config)
            initial_elo: Starting ELO for new teams (default from config)
            scale_factors: Dict with scale factors for different score lines
                          If None, uses default moderate scale factors
        """
        self.K = K if K is not None else config.K_FACTOR
        self.initial_elo = initial_elo if initial_elo is not None else config.INITIAL_ELO
        
        # Default scale factors (moderate)
        self.scale_factors = scale_factors or {
            # Bo1
            '1-0': 1.00,
            
            # Bo3
            '2-0': 1.00,  # Stomp - full weight
            '2-1': 0.5,  # Close - reduced weight
            
            # Bo5
            '3-0': 1.00,  # Complete stomp
            '3-1': 0.90,  # Dominant
            '3-2': 0.80,  # Close series
        }
        
        self.ratings = defaultdict(lambda: self.initial_elo)
        self.history = []
    
    def get_elo(self, team: str) -> float:
        """Get current ELO rating for a team"""
        return self.ratings[team]
    
    def expected_score(self, elo_a: float, elo_b: float) -> float:
        """Calculate expected score using standard ELO formula"""
        return 1 / (1 + 10 ** ((elo_b - elo_a) / 400))
    
    def get_scale_factor(self, score1: int, score2: int) -> float:
        """
        Get scale factor based on score
        
        Args:
            score1: Winner's score
            score2: Loser's score
            
        Returns:
            Scale factor (0.0 to 1.0+)
        """
        # Ensure winner score is first
        winner_score = max(score1, score2)
        loser_score = min(score1, score2)
        
        score_key = f"{winner_score}-{loser_score}"
        
        # Return scale factor or default to 1.0
        return self.scale_factors.get(score_key, 1.0)
    
    def update(self, match: Dict) -> Dict:
        """
        Process one match and update ELO ratings with scale factor
        
        Args:
            match: Match dictionary with:
                - team1: First team name
                - team2: Second team name
                - winner: Winning team name
                - score1: Team1's score
                - score2: Team2's score
                - (optional) date, etc.
        
        Returns:
            Dictionary with update details including scale_factor used
        """
        team1 = match['team1']
        team2 = match['team2']
        winner = match['winner']
        score1 = match.get('score1', 1)
        score2 = match.get('score2', 0)
        
        # Get current ratings
        elo1 = self.get_elo(team1)
        elo2 = self.get_elo(team2)
        
        # Calculate expected scores
        E1 = self.expected_score(elo1, elo2)
        E2 = 1 - E1
        
        # Actual scores
        S1 = 1.0 if winner == team1 else 0.0
        S2 = 1.0 - S1
        
        # Get scale factor based on score closeness
        scale_factor = self.get_scale_factor(score1, score2)
        
        # Apply scale factor to K
        effective_K = self.K * scale_factor
        
        # Calculate rating changes
        delta1 = effective_K * (S1 - E1)
        delta2 = effective_K * (S2 - E2)
        
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
            'win_probability': max(E1, E2),
            'scale_factor': scale_factor,
            'effective_K': effective_K,
            'base_K': self.K,
            'score': f"{score1}-{score2}"
        }
        
        # Add optional match data
        if 'date' in match:
            update_record['date'] = match['date']
        
        # Store in history
        self.history.append(update_record)
        
        return update_record
    
    def process_matches(self, matches: List[Dict]) -> List[Dict]:
        """Process multiple matches in sequence"""
        results = []
        for match in matches:
            result = self.update(match)
            results.append(result)
        return results
    
    def predict(self, team1: str, team2: str) -> Dict:
        """
        Predict outcome without updating ratings
        Same as base ELO (scale factor only affects updates)
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
        """Get current leaderboard sorted by ELO"""
        teams = []
        for team, elo in self.ratings.items():
            if min_elo is None or elo >= min_elo:
                teams.append({'team': team, 'elo': elo})
        
        teams.sort(key=lambda x: x['elo'], reverse=True)
        
        for i, team in enumerate(teams):
            team['rank'] = i + 1
        
        return teams
    
    def get_accuracy(self) -> float:
        """Calculate overall prediction accuracy"""
        if not self.history:
            return 0.0
        
        correct = sum(1 for h in self.history if h['correct'])
        return correct / len(self.history)
    
    def get_statistics(self) -> Dict:
        """Get comprehensive statistics about the system"""
        if not self.history:
            return {
                'total_matches': 0,
                'accuracy': 0.0
            }
        
        deltas = [abs(h['delta1']) for h in self.history]
        win_probs = [h['win_probability'] for h in self.history]
        scale_factors_used = [h['scale_factor'] for h in self.history]
        
        # Count scale factor usage
        scale_factor_counts = {}
        for sf in scale_factors_used:
            scale_factor_counts[sf] = scale_factor_counts.get(sf, 0) + 1
        
        return {
            'total_matches': len(self.history),
            'total_teams': len(self.ratings),
            'accuracy': self.get_accuracy(),
            'mean_elo_change': np.mean(deltas),
            'median_elo_change': np.median(deltas),
            'std_elo_change': np.std(deltas),
            'mean_confidence': np.mean(win_probs),
            'base_k_factor': self.K,
            'initial_elo': self.initial_elo,
            'mean_scale_factor': np.mean(scale_factors_used),
            'scale_factor_distribution': scale_factor_counts
        }
    
    def reset(self):
        """Reset all ratings and history"""
        self.ratings.clear()
        self.history.clear()


def train_and_evaluate(matches: List[Dict], train_ratio: float = 0.7,
                      K: float = 20, scale_factors: Dict = None) -> Dict:
    """
    Train on first portion, evaluate on rest
    
    Args:
        matches: List of matches
        train_ratio: Portion to use for training
        K: K-factor
        scale_factors: Scale factor dictionary
        
    Returns:
        Dictionary with train and test results
    """
    split_idx = int(len(matches) * train_ratio)
    train_matches = matches[:split_idx]
    test_matches = matches[split_idx:]
    
    # Train
    calculator = ScaleFactorEloCalculator(K=K, scale_factors=scale_factors)
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
def test_scale_factor_logic():
    """Test that scale factor works regardless of score order"""
    calc = ScaleFactorEloCalculator()
    
    # Test 1: Winner score first
    sf1 = calc.get_scale_factor(3, 1)
    print(f"Score 3-1: Scale Factor = {sf1}")
    
    # Test 2: Loser score first  
    sf2 = calc.get_scale_factor(1, 3)
    print(f"Score 1-3: Scale Factor = {sf2}")
    
    # Should be equal!
    assert sf1 == sf2, "Scale factors don't match!"
    print("✅ Scale factor logic is correct!\n")
    
    # Test all combinations
    test_cases = [
        (2, 0, 0, 2),
        (2, 1, 1, 2),
        (3, 0, 0, 3),
        (3, 1, 1, 3),
        (3, 2, 2, 3),
    ]
    
    for s1a, s2a, s1b, s2b in test_cases:
        sf_a = calc.get_scale_factor(s1a, s2a)
        sf_b = calc.get_scale_factor(s1b, s2b)
        print(f"{s1a}-{s2a} = {sf_a:.2f}, {s1b}-{s2b} = {sf_b:.2f} → {'✅' if sf_a == sf_b else '❌'}")

if __name__ == "__main__":
    from core.data_loader import MatchDataLoader
    
    print("="*60)
    print("SCALE FACTOR ELO CALCULATOR - TEST")
    print("="*60)
    
    # Load data
    print("\nLoading matches...")
    loader = MatchDataLoader()
    matches = loader.get_matches_as_dicts()
    print(f"✓ Loaded {len(matches)} matches")
    
    # Train and evaluate
    print("\nTraining and evaluating with scale factors...")
    results = train_and_evaluate(matches, train_ratio=0.7, K=20)
    
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
    print(f"  Mean scale factor: {stats['mean_scale_factor']:.3f}")
    print(f"  Base K-factor: {stats['base_k_factor']}")
    
    print(f"\n📈 SCALE FACTOR USAGE:")
    for sf, count in sorted(stats['scale_factor_distribution'].items()):
        percentage = (count / stats['total_matches']) * 100
        print(f"  {sf:.2f}: {count} matches ({percentage:.1f}%)")
    
    print("\n" + "="*60)


# Wrapper class for backwards compatibility with validation scripts
class ScaleFactorElo:
    """
    Backwards-compatible wrapper for ScaleFactorEloCalculator
    Provides the old API expected by validation scripts
    """
    def __init__(self, k_factor: float = 24, initial_elo: float = 1500,
                 use_scale_factors: bool = True, scale_factors: dict = None):
        # Create underlying calculator
        self.calculator = ScaleFactorEloCalculator(
            K=k_factor,
            initial_elo=initial_elo,
            scale_factors=scale_factors if use_scale_factors else None
        )
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
        elo1 = self.calculator.get_elo(team1)
        elo2 = self.calculator.get_elo(team2)

        E1 = self.calculator.expected_score(elo1, elo2)

        return {
            'predicted_winner': team1 if E1 > 0.5 else team2,
            'win_prob': max(E1, 1 - E1)
        }

    def get_elo(self, team: str) -> float:
        """Get current ELO"""
        return self.calculator.get_elo(team)

    def get_rating(self, team: str) -> float:
        """Get current rating (alias for get_elo)"""
        return self.get_elo(team)
