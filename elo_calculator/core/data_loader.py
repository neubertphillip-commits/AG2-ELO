"""
Data Loader for LOL ELO System
Loads match data from Google Sheets with validation
"""

import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
import config


class MatchDataLoader:
    """
    Loads and validates match data from Google Sheets
    """
    
    def __init__(self, sheet_id: str = None):
        """
        Initialize data loader
        
        Args:
            sheet_id: Google Sheets ID (uses config default if not provided)
        """
        self.sheet_id = sheet_id or config.SHEET_ID
        self.matches_url = f"https://docs.google.com/spreadsheets/d/{self.sheet_id}/gviz/tq?tqx=out:csv&sheet={config.MATCHES_SHEET}"
        self._cache = None
    
    def load_matches(self, force_reload: bool = False) -> pd.DataFrame:
        """
        Load matches from Google Sheets
        
        Args:
            force_reload: If True, bypass cache and reload from source
            
        Returns:
            DataFrame with validated match data
            
        Raises:
            ValueError: If required columns are missing or data is invalid
        """
        # Return cached data if available
        if self._cache is not None and not force_reload:
            return self._cache.copy()
        
        try:
            # Load from Google Sheets
            df = pd.read_csv(self.matches_url)
            
            # Validate structure
            self._validate_columns(df)
            
            # Clean and parse data
            df = self._clean_data(df)
            
            # Sort chronologically
            df = df.sort_values('Date').reset_index(drop=True)
            
            # Cache the result
            self._cache = df.copy()
            
            return df
        
        except Exception as e:
            raise ValueError(f"Failed to load matches: {str(e)}")
    
    def _validate_columns(self, df: pd.DataFrame) -> None:
        """
        Validate that required columns exist
        
        Args:
            df: DataFrame to validate
            
        Raises:
            ValueError: If required columns are missing
        """
        required_cols = [
            'Date', 'Team 1', 'team 2', 'score', 
            'Elo Team 1', 'elo team 2'
        ]
        
        missing = set(required_cols) - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
    
    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and parse data
        
        Args:
            df: Raw DataFrame
            
        Returns:
            Cleaned DataFrame
        """
        # Parse dates (handle multiple formats)
        df['Date'] = pd.to_datetime(df['Date'], format='mixed', dayfirst=True, errors='coerce')
        
        # Drop rows without date
        df = df.dropna(subset=['Date'])
        
        # Parse ELO values
        df['Elo Team 1'] = pd.to_numeric(df['Elo Team 1'], errors='coerce')
        df['elo team 2'] = pd.to_numeric(df['elo team 2'], errors='coerce')
        
        # Drop rows without teams or score
        df = df.dropna(subset=['Team 1', 'team 2', 'score'])
        
        # Ensure score is string
        df['score'] = df['score'].astype(str)
        
        return df
    
    def parse_match(self, row: pd.Series) -> Dict:
        """
        Convert DataFrame row to standardized match dictionary

        Args:
            row: DataFrame row

        Returns:
            Dictionary with match data
        """
        score_parts = str(row['score']).split('-')

        if len(score_parts) != 2:
            raise ValueError(f"Invalid score format: {row['score']}")

        score1 = int(score_parts[0])
        score2 = int(score_parts[1])

        match_dict = {
            'date': row['Date'],
            'team1': row['Team 1'],
            'team2': row['team 2'],
            'team1_elo': row['Elo Team 1'],
            'team2_elo': row['elo team 2'],
            'score1': score1,
            'score2': score2,
            'winner': row['Team 1'] if score1 > score2 else row['team 2'],
            'is_bo1': max(score1, score2) == 1,
            'is_bo3': max(score1, score2) <= 2,
            'is_bo5': max(score1, score2) <= 3,
            'games_played': score1 + score2
        }

        # Add optional fields if they exist in the row
        optional_fields = ['Tournament', 'Stage', 'Tournament Type', 'Patch']
        for field in optional_fields:
            if field in row.index and pd.notna(row[field]):
                # Normalize field names to lowercase with underscores
                normalized_field = field.lower().replace(' ', '_')
                match_dict[normalized_field] = row[field]

        return match_dict
    
    def get_matches_as_dicts(self, force_reload: bool = False) -> List[Dict]:
        """
        Load matches as list of dictionaries
        
        Args:
            force_reload: If True, bypass cache
            
        Returns:
            List of match dictionaries
        """
        df = self.load_matches(force_reload=force_reload)
        return [self.parse_match(row) for _, row in df.iterrows()]
    
    def get_unique_teams(self, force_reload: bool = False) -> set:
        """
        Get set of all unique team names
        
        Args:
            force_reload: If True, bypass cache
            
        Returns:
            Set of team names
        """
        df = self.load_matches(force_reload=force_reload)
        teams = set()
        teams.update(df['Team 1'].unique())
        teams.update(df['team 2'].unique())
        return teams
    
    def clear_cache(self):
        """Clear cached data"""
        self._cache = None


# Convenience function for quick loading
def load_matches(force_reload: bool = False) -> pd.DataFrame:
    """
    Quick function to load matches
    
    Args:
        force_reload: If True, bypass cache
        
    Returns:
        DataFrame with match data
    """
    loader = MatchDataLoader()
    return loader.load_matches(force_reload=force_reload)


if __name__ == "__main__":
    # Test loading
    print("Loading matches from Google Sheets...")
    
    loader = MatchDataLoader()
    df = loader.load_matches()
    
    print(f"\n✓ Loaded {len(df)} matches")
    print(f"✓ Date range: {df['Date'].min()} to {df['Date'].max()}")
    print(f"✓ Unique teams: {len(loader.get_unique_teams())}")
    
    # Test parsing
    print("\nFirst match:")
    first_match = loader.parse_match(df.iloc[0])
    for key, value in first_match.items():
        print(f"  {key}: {value}")
