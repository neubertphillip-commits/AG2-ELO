"""
Diagnose tool for duplicate detection in Google Sheets import
Helps identify false positives in duplicate detection
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import DatabaseManager
from core.data_loader import MatchDataLoader
from datetime import datetime

def analyze_duplicates():
    """
    Analyze why matches are being marked as duplicates
    """
    print("="*70)
    print("DUPLICATE DETECTION ANALYSIS")
    print("="*70)

    # Load Google Sheets data
    loader = MatchDataLoader()
    df = loader.load_matches()

    print(f"\n[STATS] Google Sheets: {len(df)} matches")

    # Check database
    db = DatabaseManager()
    stats = db.get_stats()

    print(f"📦 Database: {stats['total_matches']} matches")

    if 'by_source' in stats:
        print(f"\n📋 By Source:")
        for source, count in stats['by_source'].items():
            print(f"  {source}: {count}")

    # Analyze potential duplicates
    print(f"\n🔍 Analyzing potential duplicates...")

    duplicates = []
    matches_to_insert = []

    for idx, row in df.iterrows():
        try:
            match_data = loader.parse_match(row)

            # Convert date
            match_date = match_data['date']
            if hasattr(match_date, 'to_pydatetime'):
                match_date = match_date.to_pydatetime()

            # Check if exists
            is_duplicate = db.match_exists(
                external_id=None,  # Google Sheets has no external ID
                team1=match_data['team1'],
                team2=match_data['team2'],
                date=match_date
            )

            if is_duplicate:
                duplicates.append({
                    'row': idx,
                    'date': match_date,
                    'team1': match_data['team1'],
                    'team2': match_data['team2'],
                    'score': f"{match_data['score1']}-{match_data['score2']}"
                })
            else:
                matches_to_insert.append(match_data)

        except Exception as e:
            print(f"  [WARNING] Error parsing row {idx}: {e}")

    # Report
    print(f"\n" + "="*70)
    print("RESULTS")
    print("="*70)

    print(f"\n✅ New matches to import: {len(matches_to_insert)}")
    print(f"[SKIP] Detected duplicates: {len(duplicates)}")

    if len(duplicates) > 0:
        print(f"\n📋 First 10 'duplicates':")
        for i, dup in enumerate(duplicates[:10]):
            print(f"\n  {i+1}. Row {dup['row']}")
            print(f"     Date: {dup['date']}")
            print(f"     Match: {dup['team1']} vs {dup['team2']}")
            print(f"     Score: {dup['score']}")

            # Check what's in database
            cursor = db.conn.cursor()
            cursor.execute("""
                SELECT m.id, m.date, m.team1_score, m.team2_score, m.source,
                       t1.name as team1_name, t2.name as team2_name
                FROM matches m
                JOIN teams t1 ON m.team1_id = t1.id
                JOIN teams t2 ON m.team2_id = t2.id
                WHERE (t1.name = ? AND t2.name = ? OR t1.name = ? AND t2.name = ?)
                  AND DATE(m.date) = DATE(?)
            """, (dup['team1'], dup['team2'], dup['team2'], dup['team1'], dup['date']))

            existing = cursor.fetchall()
            if existing:
                print(f"     DB Match:")
                for match in existing:
                    print(f"       - ID {match[0]}: {match[5]} {match[2]}-{match[3]} {match[6]}")
                    print(f"         Date: {match[1]}, Source: {match[4]}")

    # Check for date-only duplicates (same teams, same day, different times)
    print(f"\n🔍 Checking for same-day duplicates (Bo3/Bo5 series)...")

    from collections import defaultdict
    same_day_matches = defaultdict(list)

    for idx, row in df.iterrows():
        try:
            match_data = loader.parse_match(row)
            match_date = match_data['date']
            if hasattr(match_date, 'to_pydatetime'):
                match_date = match_date.to_pydatetime()

            key = (
                match_date.date(),
                frozenset([match_data['team1'], match_data['team2']])
            )
            same_day_matches[key].append({
                'row': idx,
                'team1': match_data['team1'],
                'team2': match_data['team2'],
                'score': f"{match_data['score1']}-{match_data['score2']}",
                'datetime': match_date
            })
        except:
            pass

    multi_matches = {k: v for k, v in same_day_matches.items() if len(v) > 1}

    if multi_matches:
        print(f"\n[WARNING] Found {len(multi_matches)} days with multiple matches between same teams:")
        for (date, teams), matches in list(multi_matches.items())[:5]:
            print(f"\n  {date}: {list(teams)[0]} vs {list(teams)[1]}")
            for m in matches:
                print(f"    - Row {m['row']}: {m['score']} at {m['datetime'].time()}")
    else:
        print(f"  [OK] No same-day duplicates found")

    db.close()

    # Recommendations
    print(f"\n" + "="*70)
    print("RECOMMENDATIONS")
    print("="*70)

    if len(duplicates) == 0:
        print("\n✅ No duplicates detected - safe to import!")
    elif len(duplicates) == len(df):
        print("\n[WARNING] ALL matches marked as duplicates!")
        print("   Possible causes:")
        print("   1. Database already contains all Google Sheets data")
        print("   2. Data was imported previously")
        print("   Action: Check database stats above")
    else:
        print(f"\n[WARNING] {len(duplicates)}/{len(df)} matches marked as duplicates")
        print(f"   {len(matches_to_insert)} new matches would be imported")
        print(f"\n   Review the duplicate list above to verify:")
        print(f"   - Are these truly duplicates?")
        print(f"   - Or are they different matches on same day?")

if __name__ == "__main__":
    analyze_duplicates()
