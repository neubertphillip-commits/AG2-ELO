#!/usr/bin/env python3
"""
Export all unique team names from your database for mapping
Works on both Windows and Linux

Usage:
    python export_teams_for_mapping.py path/to/your/database.db
"""

import sys
import sqlite3
import json
from pathlib import Path
from collections import Counter

def export_team_names(db_path):
    """Export all unique team names with their match counts"""

    if not Path(db_path).exists():
        print(f"❌ Database not found: {db_path}")
        print("\nPlease provide the correct path to your database.")
        return

    print(f"📂 Opening database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Try to find team names in common table structures
    tables_to_try = [
        ("teams", "name"),
        ("Teams", "Name"),
        ("TEAMS", "NAME"),
    ]

    team_names = []

    # First, show all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()

    print(f"\n📊 Found {len(tables)} tables in database:")
    for table in tables:
        print(f"  - {table[0]}")

    # Try to find teams
    print("\n🔍 Looking for team names...")

    # Get all team names from matches or teams table
    try:
        # Try team1, team2 columns in matches table
        cursor.execute("""
            SELECT name FROM teams
        """)
        teams = cursor.fetchall()
        team_names = [t[0] for t in teams]

        # Get match counts
        cursor.execute("""
            SELECT t.name, COUNT(*) as match_count
            FROM teams t
            LEFT JOIN matches m ON (m.team1_id = t.id OR m.team2_id = t.id)
            GROUP BY t.name
            ORDER BY match_count DESC
        """)
        teams_with_counts = cursor.fetchall()

    except sqlite3.OperationalError as e:
        print(f"⚠️  Error querying database: {e}")
        print("\nPlease tell me:")
        print("1. What tables does your database have?")
        print("2. Which columns contain team names?")
        return

    conn.close()

    # Export results
    print(f"\n✅ Found {len(team_names)} unique teams")
    print(f"📊 Total matches in database: {sum(count for _, count in teams_with_counts)}")

    # Export to JSON
    export_data = {
        "total_teams": len(team_names),
        "teams": [
            {
                "name": name,
                "match_count": count
            }
            for name, count in teams_with_counts
        ]
    }

    output_file = "teams_to_map.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Exported to: {output_file}")

    # Show top 20 teams
    print(f"\n🏆 TOP 20 TEAMS BY MATCH COUNT:")
    print(f"{'Team Name':<50} {'Matches':>10}")
    print("="*65)

    for name, count in teams_with_counts[:20]:
        print(f"{name:<50} {count:>10}")

    print(f"\n💡 Next step:")
    print(f"   Copy '{output_file}' to the Linux environment or share the team names")
    print(f"   Then I can help you map all {len(team_names)} teams!")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python export_teams_for_mapping.py <database_path>")
        print("\nExample:")
        print("  python export_teams_for_mapping.py db/elo_system.db")
        print("  python export_teams_for_mapping.py C:\\path\\to\\your\\database.db")
        sys.exit(1)

    db_path = sys.argv[1]
    export_team_names(db_path)
