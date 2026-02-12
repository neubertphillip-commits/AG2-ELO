"""
Import Tier 1 League Data from Leaguepedia
Imports LEC, LPL, LCK, LCS and international tournaments from 2013-present
Includes automatic deduplication against existing data
"""

import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import DatabaseManager
from core.leaguepedia_loader import LeaguepediaLoader


def import_tier1_historical_data(start_year: int = 2013,
                                 end_year: int = None,
                                 include_players: bool = True,
                                 leagues: list = None):
    """
    Import historical Tier 1 league data

    Args:
        start_year: Starting year (default: 2013)
        end_year: Ending year (default: current year)
        include_players: Whether to import player data
        leagues: List of leagues to import (default: all Tier 1)
    """
    if end_year is None:
        end_year = datetime.now().year

    if leagues is None:
        leagues = ['LEC', 'LPL', 'LCK', 'LCS', 'WORLDS', 'MSI']

    print("="*70)
    print(f"Tier 1 League Data Import: {start_year}-{end_year}")
    print("="*70)
    print(f"\nLeagues: {', '.join(leagues)}")
    print(f"Player Data: {'Yes' if include_players else 'No'}")
    print(f"Time Range: {start_year} - {end_year}")

    # Initialize
    loader = LeaguepediaLoader()
    db = loader.db

    # Statistics
    total_stats = {
        'total_matches': 0,
        'by_league': {},
        'start_time': datetime.now()
    }

    # Import each league
    for league in leagues:
        print(f"\n{'='*70}")
        print(f"[IMPORT] Importing {league}")
        print(f"{'='*70}")

        league_stats = {
            'total': 0,
            'by_year': {}
        }

        # Get league configuration (case-insensitive match)
        league_upper = league.upper()
        if league_upper not in loader.TIER1_LEAGUES:
            print(f"  [WARNING] Unknown league: {league}")
            print(f"  Available leagues: {', '.join(loader.TIER1_LEAGUES.keys())}")
            continue

        config = loader.TIER1_LEAGUES[league_upper]
        league_start = max(start_year, config['start_year'])

        # Import each year and split
        for year in range(league_start, end_year + 1):
            year_total = 0

            for split in config['splits']:
                try:
                    print(f"\n  {league_upper} {year} {split}")

                    imported = loader.import_league_season(
                        league=league_upper,
                        year=year,
                        split=split,
                        include_playoffs=True,
                        include_players=include_players
                    )

                    year_total += imported
                    league_stats['total'] += imported

                except Exception as e:
                    print(f"    [WARNING] Error: {e}")
                    continue

            if year_total > 0:
                league_stats['by_year'][year] = year_total
                print(f"  [OK] {year} Total: {year_total} matches")

        # Update total stats
        total_stats['by_league'][league_upper] = league_stats['total']
        total_stats['total_matches'] += league_stats['total']

        print(f"\n[OK] {league_upper} Complete: {league_stats['total']} matches imported")

    # Final summary
    duration = datetime.now() - total_stats['start_time']

    print("\n" + "="*70)
    print("IMPORT COMPLETE")
    print("="*70)

    print(f"\n[STATS] Import Statistics:")
    print(f"  Total Matches Imported: {total_stats['total_matches']}")
    print(f"  Duration: {duration}")

    print(f"\n  By League:")
    for league, count in total_stats['by_league'].items():
        print(f"    {league:10s}: {count:5d} matches")

    # Database final stats
    db_stats = db.get_stats()
    print(f"\n[DATABASE] Final Database Stats:")
    print(f"  Total Matches: {db_stats['total_matches']}")
    print(f"  Total Teams: {db_stats['total_teams']}")
    print(f"  Total Players: {db_stats['total_players']}")
    print(f"  Total Tournaments: {db_stats['total_tournaments']}")

    if db_stats['date_range'][0] and db_stats['date_range'][1]:
        print(f"  Date Range: {db_stats['date_range'][0]} to {db_stats['date_range'][1]}")

    if 'by_source' in db_stats:
        print(f"\n  By Source:")
        for source, count in db_stats['by_source'].items():
            print(f"    {source:15s}: {count:5d} matches")

    loader.close()

    return total_stats


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Import Tier 1 League Data')
    parser.add_argument('--start-year', type=int, default=2013,
                       help='Starting year (default: 2013)')
    parser.add_argument('--end-year', type=int, default=None,
                       help='Ending year (default: current year)')
    parser.add_argument('--no-players', action='store_true',
                       help='Skip player data import (MUCH faster, avoids rate limits)')
    parser.add_argument('--leagues', nargs='+',
                       default=['LEC', 'LPL', 'LCK', 'LCS', 'WORLDS', 'MSI'],
                       help='Leagues to import (default: all Tier 1)')
    parser.add_argument('--test', action='store_true',
                       help='Test mode: only import 2024 data')

    args = parser.parse_args()

    if args.test:
        print("\n[TEST] TEST MODE: Importing 2024 data only\n")
        args.start_year = 2024
        args.end_year = 2024
        # IMPORTANT: Disable players in test mode to avoid rate limiting!
        if not args.no_players:
            print("[INFO] Disabling player data in test mode to avoid rate limits")
            print("[INFO] Use --no-players flag to disable this warning\n")
            args.no_players = True

    import_tier1_historical_data(
        start_year=args.start_year,
        end_year=args.end_year,
        include_players=not args.no_players,
        leagues=args.leagues
    )
