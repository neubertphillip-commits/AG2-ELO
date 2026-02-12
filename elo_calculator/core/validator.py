"""
Data Validation for LOL ELO System
Ensures data quality and catches issues early
"""

import pandas as pd
from typing import Dict, List, Tuple
from datetime import datetime


class DataValidator:
    """
    Validates match data for quality issues
    """
    
    @staticmethod
    def validate_match_dict(match: Dict) -> Tuple[bool, List[str]]:
        """
        Validate a single match dictionary
        
        Args:
            match: Match dictionary
            
        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        
        # Required fields
        required_fields = [
            'date', 'team1', 'team2', 'team1_elo', 'team2_elo',
            'score1', 'score2', 'winner'
        ]
        
        for field in required_fields:
            if field not in match:
                errors.append(f"Missing required field: {field}")
        
        if errors:
            return False, errors
        
        # Team names must be different
        if match['team1'] == match['team2']:
            errors.append(f"Same team playing itself: {match['team1']}")
        
        # Scores must be non-negative
        if match['score1'] < 0 or match['score2'] < 0:
            errors.append(f"Negative score: {match['score1']}-{match['score2']}")
        
        # Scores must not be tied
        if match['score1'] == match['score2']:
            errors.append(f"Tied score not allowed: {match['score1']}-{match['score2']}")
        
        # Winner must match score
        expected_winner = match['team1'] if match['score1'] > match['score2'] else match['team2']
        if match['winner'] != expected_winner:
            errors.append(f"Winner {match['winner']} doesn't match score {match['score1']}-{match['score2']}")
        
        # ELO must be positive
        if match['team1_elo'] <= 0 or match['team2_elo'] <= 0:
            errors.append(f"Invalid ELO: {match['team1_elo']}, {match['team2_elo']}")
        
        # Date must be valid
        if not isinstance(match['date'], (datetime, pd.Timestamp)):
            errors.append(f"Invalid date type: {type(match['date'])}")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_dataframe(df: pd.DataFrame) -> Dict:
        """
        Validate entire DataFrame
        
        Args:
            df: DataFrame to validate
            
        Returns:
            Dictionary with validation results
        """
        results = {
            'total_rows': len(df),
            'valid_rows': 0,
            'errors': [],
            'warnings': []
        }
        
        # Check for duplicates
        duplicates = df.duplicated(subset=['Date', 'Team 1', 'team 2']).sum()
        if duplicates > 0:
            results['warnings'].append(f"Found {duplicates} potential duplicate matches")
        
        # Check for NaN values
        for col in df.columns:
            nan_count = df[col].isna().sum()
            if nan_count > 0:
                results['warnings'].append(f"Column '{col}' has {nan_count} NaN values")
        
        # Check date ordering
        if not df['Date'].is_monotonic_increasing:
            results['warnings'].append("Dates are not in chronological order")
        
        # Check for outlier ELO values
        all_elos = pd.concat([df['Elo Team 1'], df['elo team 2']])
        q1 = all_elos.quantile(0.25)
        q3 = all_elos.quantile(0.75)
        iqr = q3 - q1
        outliers = ((all_elos < (q1 - 3 * iqr)) | (all_elos > (q3 + 3 * iqr))).sum()
        
        if outliers > 0:
            results['warnings'].append(f"Found {outliers} potential ELO outliers")
        
        results['valid_rows'] = len(df)
        
        return results
    
    @staticmethod
    def check_team_consistency(df: pd.DataFrame) -> Dict:
        """
        Check for team name consistency issues
        
        Args:
            df: DataFrame to check
            
        Returns:
            Dictionary with consistency check results
        """
        teams_team1 = set(df['Team 1'].unique())
        teams_team2 = set(df['team 2'].unique())
        
        all_teams = teams_team1.union(teams_team2)
        
        # Find potential typos (similar names)
        similar_teams = []
        team_list = sorted(all_teams)
        
        for i, team1 in enumerate(team_list):
            for team2 in team_list[i+1:]:
                # Simple similarity check (Levenshtein distance would be better)
                if len(team1) > 3 and len(team2) > 3:
                    if team1.lower() in team2.lower() or team2.lower() in team1.lower():
                        similar_teams.append((team1, team2))
        
        return {
            'total_teams': len(all_teams),
            'teams_only_team1': list(teams_team1 - teams_team2),
            'teams_only_team2': list(teams_team2 - teams_team1),
            'similar_teams': similar_teams
        }


def validate_and_report(df: pd.DataFrame) -> None:
    """
    Validate DataFrame and print report
    
    Args:
        df: DataFrame to validate
    """
    print("="*60)
    print("DATA VALIDATION REPORT")
    print("="*60)
    
    # Overall validation
    results = DataValidator.validate_dataframe(df)
    
    print(f"\nTotal rows: {results['total_rows']}")
    print(f"Valid rows: {results['valid_rows']}")
    
    if results['errors']:
        print(f"\n❌ ERRORS ({len(results['errors'])}):")
        for error in results['errors']:
            print(f"  - {error}")
    
    if results['warnings']:
        print(f"\n⚠️  WARNINGS ({len(results['warnings'])}):")
        for warning in results['warnings']:
            print(f"  - {warning}")
    
    if not results['errors'] and not results['warnings']:
        print("\n✓ No issues found!")
    
    # Team consistency
    team_check = DataValidator.check_team_consistency(df)
    
    print(f"\n📊 TEAM CONSISTENCY:")
    print(f"  Total unique teams: {team_check['total_teams']}")
    
    if team_check['similar_teams']:
        print(f"\n  ⚠️  Similar team names (potential typos):")
        for team1, team2 in team_check['similar_teams']:
            print(f"    - {team1} vs {team2}")
    
    print("="*60)


if __name__ == "__main__":
    # Test with sample data
    from core.data_loader import load_matches
    
    print("Loading matches...")
    df = load_matches()
    
    print(f"Loaded {len(df)} matches\n")
    
    validate_and_report(df)
