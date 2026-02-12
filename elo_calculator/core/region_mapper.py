"""
Dynamic Regional Offset System - Region Mapper
Maps teams to regions with fallback support
"""

import pandas as pd
import numpy as np
from typing import Dict, List
from collections import defaultdict
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import config


class RegionMapper:
    """Maps teams to regions with hierarchical support"""
    
    def __init__(self, use_fallback: bool = True):
        self.team_to_region = {}
        self.region_hierarchy = {
            'LCK': {'parent': 'LCK'},
            'LPL': {'parent': 'LPL'},
            'LEC': {'parent': 'LEC'},
            'LCP': {'parent': 'LCP'},
            'LTAN': {'parent': 'LTA'},
            'LTAS': {'parent': 'LTA'},
        }
        
        if use_fallback:
            self._use_fallback_mapping()
    
    def _use_fallback_mapping(self):
        """Hardcoded team→region mapping"""
        lck_teams = ['T1', 'GENG', 'GEN', 'DK', 'KT', 'DRX', 'HLE', 'NS', 'DNF', 'BRO', 'KDF']
        lpl_teams = ['WBG', 'BLG', 'JDG', 'TES', 'LNG', 'IG', 'FPX', 'RNG', 'EDG', 'OMG', 'WE', 'TT', 'AL', 'LGD', 'UP', 'NIP', 'BFX', 'BF']
        lec_teams = ['G2', 'FNC', 'MAD', 'VIT', 'TH', 'BDS', 'SK', 'KC', 'GX', 'MKOI', 'NAVI', 'NV']
        lcp_teams = ['PSG', 'CFO', 'GAM', 'VKE','TSW','SHG','DFM','CHF']
        ltan_teams = ['C9', 'TL', 'FLY', '100T', 'DIG', 'SR', 'LYON', 'DSG']
        ltas_teams = [ 'RED', 'PNG', 'FUR', 'VKS', 'LLL', 'FX7M', 'ISG', 'LEV']
        
        for team in lck_teams: self.team_to_region[team.upper()] = 'LCK'
        for team in lpl_teams: self.team_to_region[team.upper()] = 'LPL'
        for team in lec_teams: self.team_to_region[team.upper()] = 'LEC'
        for team in lcp_teams: self.team_to_region[team.upper()] = 'LCP'
        for team in ltan_teams: self.team_to_region[team.upper()] = 'LTAN'
        for team in ltas_teams: self.team_to_region[team.upper()] = 'LTAS'
        
        print(f"✓ Loaded {len(self.team_to_region)} teams (fallback mapping)")
    
    def get_region(self, team: str, detailed: bool = True) -> str:
        region = self.team_to_region.get(team.upper(), 'Unknown')
        if not detailed and region in ['LTAN', 'LTAS']:
            return 'LTA'
        return region
    
    def get_parent_region(self, region: str) -> str:
        return self.region_hierarchy.get(region, {}).get('parent', region)
    
    def is_cross_region(self, team1: str, team2: str, use_parent: bool = False) -> bool:
        r1 = self.get_region(team1, detailed=not use_parent)
        r2 = self.get_region(team2, detailed=not use_parent)
        return r1 != r2 and r1 != 'Unknown' and r2 != 'Unknown'
    
    def get_all_regions(self, include_sub: bool = True) -> List[str]:
        return ['LCK', 'LPL', 'LEC', 'LCP', 'LTAN', 'LTAS'] if include_sub else ['LCK', 'LPL', 'LEC', 'LCP', 'LTA']
    
    def get_region_stats(self) -> Dict:
        region_counts = defaultdict(int)
        for team, region in self.team_to_region.items():
            region_counts[region] += 1
        return {'total_teams': len(self.team_to_region), 'regions': dict(region_counts)}


if __name__ == "__main__":
    mapper = RegionMapper()
    for team in ['T1', 'G2', 'C9', 'LOUD']:
        print(f"{team}: {mapper.get_region(team)} (parent: {mapper.get_parent_region(mapper.get_region(team))})")












