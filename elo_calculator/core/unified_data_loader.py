"""
Unified Data Loader
Loads match data from both Google Sheets and SQLite Database
Provides unified interface for Elo calculation scripts
"""

from typing import List, Dict, Optional
from datetime import datetime
import pandas as pd

from core.data_loader import MatchDataLoader as GoogleSheetsLoader
from core.database import DatabaseManager


class UnifiedDataLoader:
    """
    Unified interface for loading match data from multiple sources
    Prioritizes database, falls back to Google Sheets
    """

    def __init__(self, prefer_database: bool = True):
        """
        Initialize unified loader

        Args:
            prefer_database: If True, use database when available
        """
        self.prefer_database = prefer_database
        self.google_sheets_loader = GoogleSheetsLoader()
        self.db = None

        # Try to connect to database
        try:
            self.db = DatabaseManager()
            db_stats = self.db.get_stats()
            self.has_database = db_stats['total_matches'] > 0
        except Exception as e:
            print(f"[WARNING] Database not available: {e}")
            self.has_database = False

    def load_matches(self, source: str = 'auto') -> pd.DataFrame:
        """
        Load matches as DataFrame (compatible with existing scripts)

        Args:
            source: 'auto', 'database', or 'google_sheets'

        Returns:
            DataFrame with match data
        """
        if source == 'auto':
            source = 'database' if (self.has_database and self.prefer_database) else 'google_sheets'

        print(f"Loading data from: {source}")

        if source == 'database' and self.has_database:
            return self._load_from_database()
        else:
            return self._load_from_google_sheets()

    def _load_from_database(self) -> pd.DataFrame:
        """Load matches from database"""
        matches = self.db.get_all_matches(limit=None)

        # Convert to DataFrame format compatible with existing scripts
        df_data = []
        for m in matches:
            df_data.append({
                'date': pd.Timestamp(m['date']),
                'team1': m['team1_name'],
                'team2': m['team2_name'],
                'score': f"{m['team1_score']}-{m['team2_score']}",
                'winner': m.get('winner', ''),  # Add winner field
                'elo_team1': 1500,  # Will be calculated
                'elo_team2': 1500,  # Will be calculated
                'tournament': m.get('tournament', ''),
                'stage': m.get('stage', ''),
                'patch': m.get('patch', ''),
                'source': m.get('source', 'database')
            })

        df = pd.DataFrame(df_data)

        # Sort chronologically
        df = df.sort_values('date').reset_index(drop=True)

        print(f"  [OK] Loaded {len(df)} matches from database")
        return df

    def _load_from_google_sheets(self) -> pd.DataFrame:
        """Load matches from Google Sheets"""
        df = self.google_sheets_loader.load_matches()

        # Normalize column names (Team 1 -> team1, team 2 -> team2)
        column_mapping = {
            'Team 1': 'team1',
            'team 2': 'team2',
            'Elo Team 1': 'elo_team1',
            'elo team 2': 'elo_team2',
            'Date': 'date'
        }

        # Rename columns that exist
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})

        # Add empty columns if not present
        if 'tournament' not in df.columns:
            df['tournament'] = ''
        if 'stage' not in df.columns:
            df['stage'] = ''
        if 'patch' not in df.columns:
            df['patch'] = ''

        # Add winner column if not present
        if 'winner' not in df.columns and 'score' in df.columns:
            def get_winner(row):
                try:
                    score_parts = str(row['score']).split('-')
                    if len(score_parts) == 2:
                        score1, score2 = int(score_parts[0]), int(score_parts[1])
                        return row['team1'] if score1 > score2 else row['team2']
                except:
                    pass
                return ''
            df['winner'] = df.apply(get_winner, axis=1)

        df['source'] = 'google_sheets'

        print(f"  [OK] Loaded {len(df)} matches from Google Sheets")
        return df

    def get_matches_as_dicts(self, source: str = 'auto') -> List[Dict]:
        """
        Load matches as list of dictionaries

        Args:
            source: 'auto', 'database', or 'google_sheets'

        Returns:
            List of match dictionaries
        """
        if source == 'auto':
            source = 'database' if (self.has_database and self.prefer_database) else 'google_sheets'

        if source == 'database' and self.has_database:
            matches = self.db.get_all_matches(limit=None)

            # Convert to expected format
            result = []
            for m in matches:
                result.append({
                    'date': pd.Timestamp(m['date']),
                    'team1': m['team1_name'],
                    'team2': m['team2_name'],
                    'team1_elo': 1500,  # Will be calculated
                    'team2_elo': 1500,
                    'score1': m['team1_score'],
                    'score2': m['team2_score'],
                    'winner': m['winner'],
                    'is_bo1': m['bo_format'] == 'Bo1' if m.get('bo_format') else False,
                    'is_bo3': m['bo_format'] == 'Bo3' if m.get('bo_format') else False,
                    'is_bo5': m['bo_format'] == 'Bo5' if m.get('bo_format') else False,
                    'games_played': m['team1_score'] + m['team2_score'],
                    'tournament': m.get('tournament', ''),
                    'stage': m.get('stage', ''),
                    'patch': m.get('patch', '')
                })
            return result
        else:
            return self.google_sheets_loader.get_matches_as_dicts()

    def get_unique_teams(self, source: str = 'auto') -> set:
        """
        Get set of all unique team names

        Args:
            source: 'auto', 'database', or 'google_sheets'

        Returns:
            Set of team names
        """
        if source == 'auto':
            source = 'database' if (self.has_database and self.prefer_database) else 'google_sheets'

        if source == 'database' and self.has_database:
            cursor = self.db.conn.cursor()
            cursor.execute("SELECT DISTINCT name FROM teams")
            return {row[0] for row in cursor.fetchall()}
        else:
            return self.google_sheets_loader.get_unique_teams()

    def get_source_info(self) -> Dict:
        """
        Get information about data sources

        Returns:
            Dictionary with source info
        """
        info = {
            'has_database': self.has_database,
            'prefer_database': self.prefer_database,
            'google_sheets_available': True  # Always available
        }

        if self.has_database:
            stats = self.db.get_stats()
            info['database_stats'] = {
                'total_matches': stats['total_matches'],
                'total_teams': stats['total_teams'],
                'date_range': stats['date_range'],
                'by_source': stats.get('by_source', {})
            }

        return info

    def close(self):
        """Close database connection if open"""
        if self.db:
            self.db.close()

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


# Convenience function (drop-in replacement for old load_matches)
def load_matches(source: str = 'auto', force_reload: bool = False) -> pd.DataFrame:
    """
    Quick function to load matches from any source

    Args:
        source: 'auto', 'database', or 'google_sheets'
        force_reload: Ignored (for backwards compatibility)

    Returns:
        DataFrame with match data
    """
    loader = UnifiedDataLoader()
    df = loader.load_matches(source=source)
    loader.close()
    return df


if __name__ == "__main__":
    # Test the unified loader
    print("="*70)
    print("UNIFIED DATA LOADER TEST")
    print("="*70)

    with UnifiedDataLoader() as loader:
        # Show source info
        info = loader.get_source_info()
        print(f"\nData Source Info:")
        print(f"  Has Database: {info['has_database']}")
        print(f"  Prefers Database: {info['prefer_database']}")

        if info['has_database']:
            print(f"\n  Database Stats:")
            for key, value in info['database_stats'].items():
                if key == 'by_source':
                    print(f"    Sources:")
                    for source, count in value.items():
                        print(f"      {source}: {count}")
                else:
                    print(f"    {key}: {value}")

        # Load matches
        print(f"\nLoading matches (auto)...")
        df = loader.load_matches(source='auto')

        print(f"\n[OK] Loaded {len(df)} matches")
        print(f"  Teams: {len(loader.get_unique_teams())}")

        if len(df) > 0:
            print(f"\n  First match:")
            first = df.iloc[0]
            print(f"    Date: {first['date']}")
            print(f"    {first['team1']} vs {first['team2']}")
            print(f"    Score: {first['score']}")
            if 'source' in first:
                print(f"    Source: {first['source']}")
