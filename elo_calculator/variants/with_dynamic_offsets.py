"""
Dynamic Regional Offset Calculator - FIXED VERSION
Compatible with temporal validation framework
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from collections import defaultdict
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.region_mapper import RegionMapper
from variants.with_scale_factor import ScaleFactorEloCalculator
import config


class DynamicOffsetCalculator:
    """
    ELO Calculator with dynamic regional offsets
    FIXED: Tighter priors, offset caps, validation-compatible
    """
    
    def __init__(self, K: float = 24, scale_factors: Dict = None):
        """Initialize with base calculator"""
        # Base calculator
        self.base_calc = ScaleFactorEloCalculator(
            K=K,
            scale_factors=scale_factors or {
                '1-0': 1.00, '2-0': 1.00, '2-1': 0.50,
                '3-0': 1.00, '3-1': 0.90, '3-2': 0.80,
            }
        )
        
        # Region mapper
        self.region_mapper = RegionMapper()
        
        # Offsets
        self.offsets = defaultdict(float)
        self.confidence = defaultdict(float)
        self.sample_counts = defaultdict(int)
        
        # History
        self.history = []
        
        # FIXED: Much tighter regularization to match Excel
        self.prior_mean = 0.0
        self.prior_std = 5.0  # Very tight prior - offsets should be small
        self.max_offset = 50.0  # Lower cap to match Excel range
        self.min_samples_for_confidence = 20  # Higher threshold
    
    def get_elo(self, team: str) -> float:
        """Get ELO (delegates to base calculator)"""
        return self.base_calc.get_elo(team)
    
    def _get_region_pair_key(self, region1: str, region2: str) -> str:
        """Consistent key for region pairs"""
        return '<->'.join(sorted([region1, region2]))
    
    def _bayesian_update(self, region: str, observation: float,
                        uncertainty: float, sample_count: int) -> Tuple[float, float]:
        """
        SIMPLIFIED Bayesian update - much more conservative like Excel
        """
        current_offset = self.offsets[region]
        current_confidence = self.confidence[region]

        # Simple weighted update with moderate learning rate
        # Like Excel, we make steady adjustments based on evidence
        learning_rate = 0.15  # 15% of evidence is applied per update

        # Reduce learning rate for low sample counts
        if sample_count < 20:
            learning_rate *= (sample_count / 20)

        # Calculate change: move offset toward observation
        change = learning_rate * (observation - current_offset)
        new_offset = current_offset + change

        # Very gentle pull toward zero (regularization)
        regularization_strength = 0.005  # 0.5% pull to zero each update
        new_offset = new_offset * (1 - regularization_strength)

        # Hard cap
        new_offset = np.clip(new_offset, -self.max_offset, self.max_offset)

        # Update confidence (slower growth)
        new_confidence = min(1.0, current_confidence + 0.002)

        return new_offset, new_confidence
    
    def update(self, match: Dict) -> Dict:
        """
        Process match and update offsets
        FIXED: Compatible with validation framework
        """
        team1 = match['team1']
        team2 = match['team2']
        winner = match['winner']
        
        # Get regions (use detailed=True to separate LTAN/LTAS like in Excel)
        region1 = self.region_mapper.get_region(team1, detailed=True)
        region2 = self.region_mapper.get_region(team2, detailed=True)
        
        # Get ELOs
        elo1 = self.get_elo(team1)
        elo2 = self.get_elo(team2)

        # Update base ELO WITHOUT offsets (like Excel)
        # Offsets are ONLY used for prediction, NOT for ELO updates
        base_update = self.base_calc.update(match)

        # Check cross-region
        is_cross_region = (region1 != region2 and
                          region1 != 'Unknown' and
                          region2 != 'Unknown')

        update_record = {
            **base_update,
            'region1': region1,
            'region2': region2,
            'is_cross_region': is_cross_region,
            'offset1': self.offsets.get(region1, 0.0),
            'offset2': self.offsets.get(region2, 0.0),
        }

        # For non-cross-regional matches, still store current offsets for ALL regions
        # This prevents gaps in the history
        if not is_cross_region:
            all_regions = self.region_mapper.get_all_regions(include_sub=True)
            for region in all_regions:
                update_record[f'offset_{region}'] = self.offsets.get(region, 0.0)

            self.history.append(update_record)
            return update_record
        
        # Cross-region: Update offsets
        pair_key = self._get_region_pair_key(region1, region2)
        self.sample_counts[pair_key] += 1
        sample_count = self.sample_counts[pair_key]

        # Calculate residual WITH offsets (to see if offsets need adjustment)
        offset1 = self.offsets.get(region1, 0.0)
        offset2 = self.offsets.get(region2, 0.0)
        adjusted_elo1 = elo1 + offset1
        adjusted_elo2 = elo2 + offset2

        expected = 1 / (1 + 10 ** ((adjusted_elo2 - adjusted_elo1) / 400))
        actual = 1.0 if winner == team1 else 0.0
        residual = actual - expected

        # Offset evidence
        offset_evidence = residual * 400 / np.log(10)
        
        # Uncertainty calculation
        sample_uncertainty = 30.0 / np.sqrt(max(1, sample_count))
        elo_diff = abs(elo1 - elo2)
        elo_uncertainty = min(20.0, elo_diff / 20)
        score_diff = abs(match.get('score1', 1) - match.get('score2', 0))
        score_uncertainty = 15.0 / max(1, score_diff)
        
        total_uncertainty = np.sqrt(sample_uncertainty**2 + 
                                    elo_uncertainty**2 + 
                                    score_uncertainty**2)
        
        # Update offsets
        winner_region = region1 if winner == team1 else region2
        loser_region = region2 if winner == team1 else region1

        # Bayesian update: observation is the NEW absolute value we observe
        # The Bayesian formula will weight current vs new observation
        new_offset_winner, new_conf_winner = self._bayesian_update(
            winner_region,
            self.offsets[winner_region] + abs(offset_evidence),  # New observed value
            total_uncertainty,
            sample_count
        )

        new_offset_loser, new_conf_loser = self._bayesian_update(
            loser_region,
            self.offsets[loser_region] - abs(offset_evidence),  # New observed value
            total_uncertainty,
            sample_count
        )
        
        self.offsets[winner_region] = new_offset_winner
        self.offsets[loser_region] = new_offset_loser
        self.confidence[winner_region] = new_conf_winner
        self.confidence[loser_region] = new_conf_loser

        # Normalize
        self._normalize_offsets()

        # FIXED: Store ALL region offsets after normalization
        # This ensures we can track how normalization affected all regions
        all_regions = self.region_mapper.get_all_regions(include_sub=True)
        for region in all_regions:
            update_record[f'offset_{region}'] = self.offsets.get(region, 0.0)

        # Keep original offset1/offset2 for backward compatibility
        update_record['offset1'] = self.offsets.get(region1, 0.0)
        update_record['offset2'] = self.offsets.get(region2, 0.0)

        self.history.append(update_record)
        return update_record
    
    def _normalize_offsets(self):
        """Zero-sum normalization across all 6 regions (LCK, LPL, LEC, LCP, LTAN, LTAS)"""
        regions = self.region_mapper.get_all_regions(include_sub=True)
        total = sum(self.offsets.get(r, 0.0) for r in regions)
        mean_offset = total / len(regions)
        for region in regions:
            self.offsets[region] -= mean_offset
    
    def predict(self, team1: str, team2: str) -> Dict:
        """Predict with offsets"""
        base_pred = self.base_calc.predict(team1, team2)

        region1 = self.region_mapper.get_region(team1, detailed=True)
        region2 = self.region_mapper.get_region(team2, detailed=True)
        
        offset1 = self.offsets.get(region1, 0.0) if region1 != region2 else 0.0
        offset2 = self.offsets.get(region2, 0.0) if region1 != region2 else 0.0
        
        adjusted_elo1 = base_pred['team1_elo'] + offset1
        adjusted_elo2 = base_pred['team2_elo'] + offset2
        
        adjusted_prob1 = 1 / (1 + 10 ** ((adjusted_elo2 - adjusted_elo1) / 400))
        adjusted_prob2 = 1 - adjusted_prob1
        
        predicted_winner = team1 if adjusted_prob1 > 0.5 else team2
        
        return {
            **base_pred,
            'offset1': offset1,
            'offset2': offset2,
            'adjusted_elo1': adjusted_elo1,
            'adjusted_elo2': adjusted_elo2,
            'team1_win_prob': adjusted_prob1,
            'team2_win_prob': adjusted_prob2,
            'predicted_winner': predicted_winner,
            'confidence_value': max(adjusted_prob1, adjusted_prob2)
        }
    
    def get_current_offsets(self) -> pd.DataFrame:
        """Get offsets as DataFrame (all 6 regions)"""
        regions = self.region_mapper.get_all_regions(include_sub=True)
        
        data = []
        for region in sorted(regions):
            data.append({
                'Region': region,
                'Offset': self.offsets.get(region, 0.0),
                'Confidence': self.confidence.get(region, 0.0),
                'Sample_Count': sum(self.sample_counts[k] 
                                   for k in self.sample_counts 
                                   if region in k)
            })
        
        return pd.DataFrame(data)
    
    def get_accuracy(self) -> float:
        """Calculate accuracy"""
        if not self.history:
            return 0.0
        correct = sum(1 for h in self.history if h['correct'])
        return correct / len(self.history)
    
    def get_statistics(self) -> Dict:
        """Get statistics"""
        if not self.history:
            return {'total_matches': 0, 'accuracy': 0.0}
        
        deltas = [abs(h['delta1']) for h in self.history]
        
        return {
            'total_matches': len(self.history),
            'total_teams': len(self.base_calc.ratings),
            'accuracy': self.get_accuracy(),
            'mean_elo_change': np.mean(deltas),
            'cross_region_matches': sum(1 for h in self.history if h['is_cross_region'])
        }
    
    def reset(self):
        """Reset calculator"""
        self.base_calc.reset()
        self.offsets.clear()
        self.confidence.clear()
        self.sample_counts.clear()
        self.history.clear()


if __name__ == "__main__":
    from core.data_loader import MatchDataLoader
    
    print("="*60)
    print("DYNAMIC OFFSET CALCULATOR - FIXED VERSION TEST")
    print("="*60)
    
    loader = MatchDataLoader()
    matches = loader.get_matches_as_dicts()
    print(f"\n✓ Loaded {len(matches)} matches")
    
    calc = DynamicOffsetCalculator()
    
    for match in matches:
        calc.update(match)
    
    print(f"\n📊 FINAL REGIONAL OFFSETS (FIXED):")
    print(calc.get_current_offsets().to_string(index=False))
    
    stats = calc.get_statistics()
    print(f"\n✓ Processed {stats['cross_region_matches']} cross-region matches")
    print(f"✓ Overall accuracy: {stats['accuracy']:.2%}")


# Wrapper class for backwards compatibility with validation scripts
class DynamicOffsetElo:
    """
    Backwards-compatible wrapper for DynamicOffsetCalculator
    Provides the old API expected by validation scripts
    """
    def __init__(self, k_factor: float = 24, initial_elo: float = 1500,
                 use_scale_factors: bool = True, scale_factors: dict = None):
        # Create underlying calculator
        self.calculator = DynamicOffsetCalculator(
            K=k_factor,
            scale_factors=scale_factors if use_scale_factors else None
        )
        self.k_factor = k_factor
        self.initial_elo = initial_elo

    def update_ratings(self, team1: str, team2: str, score1: int, score2: int):
        """Update ratings (delegates to calculator)"""
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

        # Expected score
        E1 = 1 / (1 + 10 ** ((elo2 - elo1) / 400))

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
