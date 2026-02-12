"""
Import ALL Tier 1 League Data from 2013-2025
Includes LEC, LPL, LCK, LCS and all international tournaments (MSI, Worlds)
"""

import sys
from pathlib import Path
from datetime import datetime
import os

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.leaguepedia_loader import LeaguepediaLoader
from core.database import DatabaseManager


def print_status():
    """Print current database status"""
    db = DatabaseManager()
    cursor = db.conn.cursor()

    cursor.execute('SELECT COUNT(*) FROM matches')
    total = cursor.fetchone()[0]

    cursor.execute('''
        SELECT strftime('%Y', date) as year, COUNT(*) as count
        FROM matches
        GROUP BY year
        ORDER BY year DESC
    ''')

    print('\n' + '=' * 70)
    print(f'DATABASE STATUS: {total} total matches')
    print('=' * 70)
    print('\nMatches per year:')
    for row in cursor.fetchall():
        year = row[0] if row[0] else 'Unknown'
        count = row[1]
        print(f'  {year}: {count:4d} matches')
    print('=' * 70)


def import_all_data():
    """Import all historical data from 2013-2025"""

    print('=' * 70)
    print('COMPLETE HISTORICAL DATA IMPORT: 2013-2025')
    print('=' * 70)
    print('\nLeagues: LEC, LPL, LCK, LCS')
    print('International: MSI (2015+), Worlds (2013+)')
    print('Player Data: No (for speed)')
    print('\nBot Authentication: Required')
    print('  Set LEAGUEPEDIA_BOT_USERNAME and LEAGUEPEDIA_BOT_PASSWORD')
    print('=' * 70)

    # Check for credentials
    if not os.getenv('LEAGUEPEDIA_BOT_USERNAME') or not os.getenv('LEAGUEPEDIA_BOT_PASSWORD'):
        print('\n[ERROR] Bot credentials not set!')
        print('Please set environment variables:')
        print('  LEAGUEPEDIA_BOT_USERNAME')
        print('  LEAGUEPEDIA_BOT_PASSWORD')
        sys.exit(1)

    # Initialize loader
    loader = LeaguepediaLoader()
    print()

    if not loader.authenticated:
        print('[ERROR] Authentication failed!')
        sys.exit(1)

    # Print current status
    print_status()

    # Define leagues and years
    regional_leagues = {
        'LEC': {'start': 2013, 'splits': ['Spring', 'Summer']},
        'LPL': {'start': 2013, 'splits': ['Spring', 'Summer']},
        'LCK': {'start': 2013, 'splits': ['Spring', 'Summer']},
        'LCS': {'start': 2013, 'splits': ['Spring', 'Summer']},
    }

    international_tournaments = {
        'MSI': {'start': 2015, 'splits': ['Main Event']},
        'WORLDS': {'start': 2013, 'splits': ['Main Event']},
    }

    end_year = 2024  # Current year
    total_imported = 0
    start_time = datetime.now()

    # Import regional leagues
    print('\n' + '=' * 70)
    print('PHASE 1: Regional Leagues (LEC, LPL, LCK, LCS)')
    print('=' * 70)

    for league, config in regional_leagues.items():
        print(f'\n{"=" * 70}')
        print(f'Importing {league}')
        print(f'{"=" * 70}')

        for year in range(config['start'], end_year + 1):
            for split in config['splits']:
                try:
                    print(f'\n  {league} {year} {split}')

                    imported = loader.import_league_season(
                        league=league,
                        year=year,
                        split=split,
                        include_playoffs=True,
                        include_players=False  # Skip players for speed
                    )

                    total_imported += imported

                    if imported > 0:
                        print(f'  ✓ Imported: {imported} matches')
                    else:
                        print(f'  ⊘ No data found')

                except Exception as e:
                    print(f'  ✗ Error: {e}')
                    continue

    # Import international tournaments
    print('\n' + '=' * 70)
    print('PHASE 2: International Tournaments (MSI, Worlds)')
    print('=' * 70)

    for tournament, config in international_tournaments.items():
        print(f'\n{"=" * 70}')
        print(f'Importing {tournament}')
        print(f'{"=" * 70}')

        for year in range(config['start'], end_year + 1):
            for split in config['splits']:
                try:
                    print(f'\n  {tournament} {year}')

                    imported = loader.import_league_season(
                        league=tournament,
                        year=year,
                        split=split,
                        include_playoffs=False,  # International tournaments don't have separate playoffs
                        include_players=False
                    )

                    total_imported += imported

                    if imported > 0:
                        print(f'  ✓ Imported: {imported} matches')
                    else:
                        print(f'  ⊘ No data found')

                except Exception as e:
                    print(f'  ✗ Error: {e}')
                    continue

    # Final summary
    elapsed = datetime.now() - start_time

    print('\n' + '=' * 70)
    print('IMPORT COMPLETE!')
    print('=' * 70)
    print(f'Total imported: {total_imported} matches')
    print(f'Time elapsed: {elapsed}')
    print('=' * 70)

    # Print final status
    print_status()


if __name__ == "__main__":
    import_all_data()
