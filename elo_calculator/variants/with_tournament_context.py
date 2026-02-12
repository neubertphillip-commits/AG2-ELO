"""
Tournament Context ELO Variant
Uses different K-factors based on tournament importance
Higher stakes tournaments = higher K-factor = bigger rating changes
"""

from typing import Dict, Optional
from variants.with_dynamic_offsets import DynamicOffsetCalculator

# Use DynamicOffsetCalculator as base (backwards compatible with old name)
DynamicOffsetElo = DynamicOffsetCalculator


class TournamentContextElo(DynamicOffsetCalculator):
    """
    ELO system with tournament-context-aware K-factors

    Rationale:
    - Worlds/MSI: Highest stakes, teams prepare more → bigger swings (K=32)
    - Playoffs: High stakes → moderate increase (K=28)
    - Regular Season: Standard stakes → baseline (K=24)
    - First Stand/Low tier: Lower stakes → reduced (K=20)
    """

    # Tournament-specific K-factors
    TOURNAMENT_K_FACTORS = {
        # International tournaments (highest stakes)
        'worlds': 32,
        'world_championship': 32,
        'msi': 32,
        'mid-season_invitational': 32,

        # Playoffs (high stakes)
        'playoffs': 28,
        'finals': 28,
        'championship': 28,

        # Regular season (baseline)
        'regular_season': 24,
        'regular': 24,

        # Lower stakes
        'first_stand': 20,
        'promotion': 20,
    }

    def __init__(self, k_factor: float = 24, initial_elo: float = 1500,
                 use_scale_factors: bool = True, scale_factors: Dict = None):
        """
        Initialize Tournament Context ELO

        Args:
            k_factor: Baseline K-factor (used if tournament not recognized)
            initial_elo: Starting ELO rating
            use_scale_factors: Whether to use match closeness adjustments
            scale_factors: Scale factor configuration
        """
        # Call parent with correct parameters (it only takes K and scale_factors)
        super().__init__(
            K=k_factor,
            scale_factors=scale_factors if use_scale_factors else None
        )
        self.baseline_k = k_factor
        self.initial_elo = initial_elo

    def get_tournament_k_factor(self, tournament: Optional[str], stage: Optional[str]) -> float:
        """
        Determine K-factor based on tournament and stage

        Args:
            tournament: Tournament name
            stage: Tournament stage (e.g., "Playoffs", "Regular Season")

        Returns:
            Appropriate K-factor
        """
        # Normalize strings
        tournament_lower = str(tournament).lower() if tournament else ""
        stage_lower = str(stage).lower() if stage else ""

        # Check tournament name first
        for keyword, k_factor in self.TOURNAMENT_K_FACTORS.items():
            if keyword in tournament_lower:
                return k_factor

        # Check stage
        for keyword, k_factor in self.TOURNAMENT_K_FACTORS.items():
            if keyword in stage_lower:
                return k_factor

        # Default to baseline
        return self.baseline_k

    def update_ratings(self, team1: str, team2: str, score1: int, score2: int,
                       tournament: Optional[str] = None, stage: Optional[str] = None,
                       **kwargs):
        """
        Update ratings with tournament context

        Args:
            team1: First team name
            team2: Second team name
            score1: First team score
            score2: Second team score
            tournament: Tournament name
            stage: Tournament stage
            **kwargs: Additional parameters
        """
        # Get context-appropriate K-factor
        k_factor = self.get_tournament_k_factor(tournament, stage)

        # Temporarily override K-factor in base calculator
        original_k = self.base_calc.K
        self.base_calc.K = k_factor

        try:
            # Call parent's update method with match dict
            match = {
                'team1': team1,
                'team2': team2,
                'score1': score1,
                'score2': score2,
                'winner': team1 if score1 > score2 else team2
            }
            super().update(match)
        finally:
            # Restore original K-factor
            self.base_calc.K = original_k

    def get_match_importance(self, tournament: Optional[str], stage: Optional[str]) -> str:
        """
        Get human-readable importance level

        Args:
            tournament: Tournament name
            stage: Tournament stage

        Returns:
            Importance level string
        """
        k_factor = self.get_tournament_k_factor(tournament, stage)

        if k_factor >= 32:
            return "Highest (International)"
        elif k_factor >= 28:
            return "High (Playoffs)"
        elif k_factor >= 24:
            return "Standard (Regular Season)"
        else:
            return "Low (Lower Tier)"

    def expected_score(self, elo1: float, elo2: float) -> float:
        """
        Calculate expected win probability for team 1

        Args:
            elo1: ELO rating of team 1
            elo2: ELO rating of team 2

        Returns:
            Win probability for team 1 (0.0 to 1.0)
        """
        return 1 / (1 + 10 ** ((elo2 - elo1) / 400))

    def update_ratings_with_context(self, elo1: float, elo2: float,
                                     score1: float, score2: float,
                                     context: str = 'regular_season') -> tuple:
        """
        Update ratings with tournament context (simplified API)

        Args:
            elo1: Current ELO of team 1
            elo2: Current ELO of team 2
            score1: 1 if team1 won, 0 if lost
            score2: 1 if team2 won, 0 if lost
            context: Tournament context (worlds, playoffs, regular_season, msi)

        Returns:
            Tuple of (new_elo1, new_elo2)
        """
        # Map context to K-factor
        tournament_k_factors = {
            'worlds': 32,
            'msi': 30,
            'playoffs': 28,
            'regular_season': 24,
        }

        k = tournament_k_factors.get(context, self.baseline_k)

        # Calculate expected scores
        E1 = self.expected_score(elo1, elo2)
        E2 = 1 - E1

        # Update ratings
        new_elo1 = elo1 + k * (score1 - E1)
        new_elo2 = elo2 + k * (score2 - E2)

        return new_elo1, new_elo2

    def get_elo(self, team: str) -> float:
        """Get current ELO (delegates to base calculator)"""
        return self.base_calc.get_elo(team)

    def get_rating(self, team: str) -> float:
        """Get current rating (alias for get_elo)"""
        return self.get_elo(team)


if __name__ == "__main__":
    # Test the tournament context system
    print("="*70)
    print("TOURNAMENT CONTEXT ELO - TEST")
    print("="*70)

    elo = TournamentContextElo()

    # Test different tournament contexts
    test_cases = [
        ("LEC 2024 Summer", "Regular Season", "T1", "Gen.G", 2, 1),
        ("LEC 2024 Summer", "Playoffs", "T1", "Gen.G", 3, 2),
        ("World Championship 2024", "Knockout", "T1", "Gen.G", 3, 1),
        ("MSI 2024", "Finals", "T1", "Gen.G", 3, 0),
        ("First Stand 2024", "Regular", "Team A", "Team B", 1, 0),
    ]

    print("\n📊 Testing K-Factor Assignment:\n")
    print(f"{'Tournament':<30} {'Stage':<20} {'K-Factor':<10} {'Importance':<25}")
    print("-"*85)

    for tournament, stage, t1, t2, s1, s2 in test_cases:
        k_factor = elo.get_tournament_k_factor(tournament, stage)
        importance = elo.get_match_importance(tournament, stage)

        print(f"{tournament:<30} {stage:<20} {k_factor:<10.0f} {importance:<25}")

    # Simulate a season with mixed tournaments
    print("\n" + "="*70)
    print("SIMULATION: TEAM RATING CHANGES BY TOURNAMENT TYPE")
    print("="*70)

    elo = TournamentContextElo()

    # Start both teams at 1500
    print("\nInitial Ratings:")
    print(f"  T1: {elo.get_rating('T1'):.0f}")
    print(f"  Gen.G: {elo.get_rating('Gen.G'):.0f}")

    # Regular season win
    print("\n1. Regular Season: T1 beats Gen.G 2-1")
    elo.update_ratings('T1', 'Gen.G', 2, 1,
                      tournament="LEC 2024 Summer", stage="Regular Season")
    print(f"  T1: {elo.get_rating('T1'):.0f} (change: +{elo.get_rating('T1') - 1500:.0f})")
    print(f"  Gen.G: {elo.get_rating('Gen.G'):.0f} (change: {elo.get_rating('Gen.G') - 1500:.0f})")

    # Reset
    elo.ratings = {'T1': 1500.0, 'Gen.G': 1500.0}

    # Playoffs win
    print("\n2. Playoffs: T1 beats Gen.G 3-2")
    elo.update_ratings('T1', 'Gen.G', 3, 2,
                      tournament="LEC 2024 Summer", stage="Playoffs")
    print(f"  T1: {elo.get_rating('T1'):.0f} (change: +{elo.get_rating('T1') - 1500:.0f})")
    print(f"  Gen.G: {elo.get_rating('Gen.G'):.0f} (change: {elo.get_rating('Gen.G') - 1500:.0f})")

    # Reset
    elo.ratings = {'T1': 1500.0, 'Gen.G': 1500.0}

    # Worlds win
    print("\n3. Worlds Finals: T1 beats Gen.G 3-1")
    elo.update_ratings('T1', 'Gen.G', 3, 1,
                      tournament="World Championship 2024", stage="Finals")
    print(f"  T1: {elo.get_rating('T1'):.0f} (change: +{elo.get_rating('T1') - 1500:.0f})")
    print(f"  Gen.G: {elo.get_rating('Gen.G'):.0f} (change: {elo.get_rating('Gen.G') - 1500:.0f})")

    print("\n💡 Notice: Worlds produces bigger rating changes than regular season!")


# Wrapper class for backwards compatibility with validation scripts
class TournamentContextEloWrapper:
    """
    Backwards-compatible wrapper for TournamentContextElo
    Provides the old API expected by validation scripts
    """
    def __init__(self, k_factor: float = 24, initial_elo: float = 1500,
                 use_scale_factors: bool = True, scale_factors: dict = None):
        # Create underlying calculator
        self.calculator = TournamentContextElo(
            k_factor=k_factor,
            initial_elo=initial_elo,
            use_scale_factors=use_scale_factors,
            scale_factors=scale_factors
        )
        self.k_factor = k_factor
        self.initial_elo = initial_elo

    def update_ratings(self, team1: str, team2: str, score1: int, score2: int,
                       tournament: str = None, stage: str = None):
        """Update ratings with tournament context"""
        self.calculator.update_ratings(team1, team2, score1, score2,
                                      tournament=tournament, stage=stage)

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
