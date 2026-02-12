"""
Check Import Status - Shows what data is in the database
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import DatabaseManager


def check_status():
    """Check and display database import status"""
    db = DatabaseManager()
    cursor = db.conn.cursor()

    print('=' * 70)
    print('LEAGUEPEDIA DATA IMPORT STATUS')
    print('=' * 70)

    # Total matches
    cursor.execute('SELECT COUNT(*) FROM matches')
    total = cursor.fetchone()[0]
    print(f'\n📊 Total Matches: {total}')

    # Matches by year
    print('\n' + '=' * 70)
    print('Matches by Year:')
    print('=' * 70)
    cursor.execute('''
        SELECT strftime('%Y', date) as year, COUNT(*) as count
        FROM matches
        GROUP BY year
        ORDER BY year DESC
    ''')

    for row in cursor.fetchall():
        year = row[0] if row[0] else 'Unknown'
        count = row[1]
        bar = '█' * (count // 50)  # Simple bar chart
        print(f'  {year}: {count:4d} matches {bar}')

    # Matches by tournament
    print('\n' + '=' * 70)
    print('Matches by Tournament:')
    print('=' * 70)
    cursor.execute('''
        SELECT t.name, COUNT(m.id) as count
        FROM matches m
        LEFT JOIN tournaments t ON m.tournament_id = t.id
        GROUP BY t.name
        ORDER BY count DESC
        LIMIT 20
    ''')

    for row in cursor.fetchall():
        tournament = row[0] if row[0] else 'Unknown'
        count = row[1]
        print(f'  {tournament:40s}: {count:4d} matches')

    # Teams in database
    print('\n' + '=' * 70)
    print('Unique Teams:')
    print('=' * 70)
    cursor.execute('SELECT COUNT(*) FROM teams')
    team_count = cursor.fetchone()[0]
    print(f'  Total unique teams: {team_count}')

    # Sample teams
    cursor.execute('SELECT name FROM teams ORDER BY name LIMIT 20')
    teams = cursor.fetchall()
    print('\n  Sample teams:')
    for team in teams:
        print(f'    - {team[0]}')
    if team_count > 20:
        print(f'    ... and {team_count - 20} more')

    # Date range
    print('\n' + '=' * 70)
    print('Date Range:')
    print('=' * 70)
    cursor.execute('SELECT MIN(date), MAX(date) FROM matches')
    min_date, max_date = cursor.fetchone()
    print(f'  Earliest match: {min_date}')
    print(f'  Latest match: {max_date}')

    print('\n' + '=' * 70)


if __name__ == "__main__":
    check_status()
