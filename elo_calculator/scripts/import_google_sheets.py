"""
Import Google Sheets data into SQLite database
This ensures existing data is preserved and can be used for deduplication
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import DatabaseManager
from core.data_loader import MatchDataLoader
from datetime import datetime


def import_google_sheets_to_db():
    """
    Import all matches from Google Sheets into SQLite database
    Uses deduplication to avoid inserting duplicates
    """
    print("="*60)
    print("Google Sheets -> SQLite Import")
    print("="*60)

    # Initialize
    print("\nLoading Google Sheets data...")
    loader = MatchDataLoader()
    db = DatabaseManager()

    try:
        # Load matches from Google Sheets
        df = loader.load_matches()
        print(f"[OK] Loaded {len(df)} matches from Google Sheets")

        # Get unique teams
        teams = loader.get_unique_teams()
        print(f"[OK] Found {len(teams)} unique teams")

        # Import matches
        print("\nImporting into SQLite...")
        imported_count = 0
        skipped_count = 0
        error_count = 0

        for idx, row in df.iterrows():
            try:
                match_data = loader.parse_match(row)

                # Convert pandas Timestamp to Python datetime
                match_date = match_data['date']
                if hasattr(match_date, 'to_pydatetime'):
                    match_date = match_date.to_pydatetime()

                # Insert match (with deduplication)
                match_id = db.insert_match(
                    team1_name=match_data['team1'],
                    team2_name=match_data['team2'],
                    team1_score=match_data['score1'],
                    team2_score=match_data['score2'],
                    date=match_date,
                    tournament_name=match_data.get('tournament'),
                    stage=match_data.get('stage'),
                    patch=match_data.get('patch'),
                    tournament_type=match_data.get('tournament_type'),
                    source='google_sheets'
                )

                if match_id:
                    imported_count += 1
                    if imported_count % 100 == 0:
                        print(f"  Progress: {imported_count}/{len(df)}")
                else:
                    skipped_count += 1

            except Exception as e:
                error_count += 1
                print(f"  [WARNING] Error importing row {idx}: {e}")

        # Print summary
        print("\n" + "="*60)
        print("Import Summary")
        print("="*60)
        print(f"[OK] Imported: {imported_count} matches")
        if skipped_count > 0:
            print(f"[SKIP] Skipped (duplicates): {skipped_count} matches")
        if error_count > 0:
            print(f"[ERROR] Errors: {error_count} matches")

        # Database stats
        stats = db.get_stats()
        print(f"\nDatabase Stats:")
        print(f"  Total Matches: {stats['total_matches']}")
        print(f"  Total Teams: {stats['total_teams']}")
        if stats['date_range'][0] and stats['date_range'][1]:
            print(f"  Date Range: {stats['date_range'][0]} to {stats['date_range'][1]}")
        if 'by_source' in stats:
            print(f"  By Source:")
            for source, count in stats['by_source'].items():
                print(f"    - {source}: {count}")

    finally:
        db.close()


if __name__ == "__main__":
    import_google_sheets_to_db()
