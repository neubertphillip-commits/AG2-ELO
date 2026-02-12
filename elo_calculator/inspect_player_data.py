"""
Quick script to inspect player data in the database
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.database import DatabaseManager


def main():
    db = DatabaseManager()

    try:
        # Show table schema
        print("=" * 80)
        print("MATCH_PLAYERS TABLE SCHEMA")
        print("=" * 80)
        cursor = db.conn.execute("PRAGMA table_info(match_players)")
        schema = cursor.fetchall()
        for col in schema:
            print(f"{col[1]:25} {col[2]:15} {'NOT NULL' if col[3] else ''} {'PRIMARY KEY' if col[5] else ''}")

        # Count total players
        print("\n" + "=" * 80)
        print("STATISTICS")
        print("=" * 80)
        cursor = db.conn.execute("SELECT COUNT(*) FROM match_players")
        total = cursor.fetchone()[0]
        print(f"Total players in database: {total}")

        # Count by tournament
        cursor = db.conn.execute("""
            SELECT tour.name, COUNT(*) as player_count
            FROM match_players mp
            JOIN matches m ON mp.match_id = m.id
            JOIN tournaments tour ON m.tournament_id = tour.id
            GROUP BY tour.name
            ORDER BY player_count DESC
        """)
        print("\nPlayers per tournament:")
        for row in cursor.fetchall():
            print(f"  {row[0]:60} {row[1]:5} players")

        # Show sample data from LEC 2024 Spring
        print("\n" + "=" * 80)
        print("SAMPLE DATA: LEC 2024 Spring Season (first 20 records)")
        print("=" * 80)
        cursor = db.conn.execute("""
            SELECT
                mp.id,
                p.name as player_name,
                t.name as team_name,
                mp.role,
                mp.won,
                m.date,
                t1.name as team1,
                t2.name as team2,
                m.team1_score || '-' || m.team2_score as score
            FROM match_players mp
            JOIN players p ON mp.player_id = p.id
            JOIN teams t ON mp.team_id = t.id
            JOIN matches m ON mp.match_id = m.id
            JOIN teams t1 ON m.team1_id = t1.id
            JOIN teams t2 ON m.team2_id = t2.id
            JOIN tournaments tour ON m.tournament_id = tour.id
            WHERE tour.name = 'LEC/2024 Season/Spring Season'
            ORDER BY m.date, mp.id
            LIMIT 20
        """)

        print(f"{'ID':<5} {'Player':<20} {'Team':<25} {'Role':<8} {'Won':<5} {'Date':<12} {'Match':<30}")
        print("-" * 120)
        for row in cursor.fetchall():
            won_str = "✓" if row[4] else "✗"
            match_str = f"{row[6]} vs {row[7]} ({row[8]})"
            print(f"{row[0]:<5} {row[1]:<20} {row[2]:<25} {row[3]:<8} {won_str:<5} {row[5]:<12} {match_str:<30}")

        # Show player win/loss stats
        print("\n" + "=" * 80)
        print("PLAYER WIN/LOSS STATS (LEC 2024 Spring, Top 10 by games played)")
        print("=" * 80)
        cursor = db.conn.execute("""
            SELECT
                p.name as player_name,
                COUNT(*) as games_played,
                SUM(CASE WHEN mp.won = 1 THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN mp.won = 0 THEN 1 ELSE 0 END) as losses,
                ROUND(100.0 * SUM(CASE WHEN mp.won = 1 THEN 1 ELSE 0 END) / COUNT(*), 1) as win_rate
            FROM match_players mp
            JOIN players p ON mp.player_id = p.id
            JOIN matches m ON mp.match_id = m.id
            JOIN tournaments tour ON m.tournament_id = tour.id
            WHERE tour.name = 'LEC/2024 Season/Spring Season'
            GROUP BY p.name
            ORDER BY games_played DESC
            LIMIT 10
        """)

        print(f"{'Player':<20} {'Games':<8} {'Wins':<6} {'Losses':<8} {'Win Rate':<10}")
        print("-" * 60)
        for row in cursor.fetchall():
            print(f"{row[0]:<20} {row[1]:<8} {row[2]:<6} {row[3]:<8} {row[4]}%")

        # Show team compositions for one match
        print("\n" + "=" * 80)
        print("EXAMPLE: Full team rosters for one match")
        print("=" * 80)
        cursor = db.conn.execute("""
            SELECT
                m.date,
                t1.name as team1,
                t2.name as team2,
                m.team1_score || '-' || m.team2_score as score,
                p.name as player_name,
                t.name as team_name,
                mp.role,
                mp.won
            FROM match_players mp
            JOIN players p ON mp.player_id = p.id
            JOIN teams t ON mp.team_id = t.id
            JOIN matches m ON mp.match_id = m.id
            JOIN teams t1 ON m.team1_id = t1.id
            JOIN teams t2 ON m.team2_id = t2.id
            JOIN tournaments tour ON m.tournament_id = tour.id
            WHERE tour.name = 'LEC/2024 Season/Spring Season'
            ORDER BY m.date
            LIMIT 10
        """)

        rows = cursor.fetchall()
        if rows:
            match_info = rows[0]
            print(f"Match: {match_info[1]} vs {match_info[2]} on {match_info[0]}")
            print(f"Score: {match_info[3]}")
            print(f"\nTeam 1 ({match_info[1]}):")
            for row in rows[:5]:
                won_str = "WON" if row[7] else "LOST"
                print(f"  {row[6]:<8} {row[4]:<20} ({won_str})")
            print(f"\nTeam 2 ({match_info[2]}):")
            for row in rows[5:10]:
                won_str = "WON" if row[7] else "LOST"
                print(f"  {row[6]:<8} {row[4]:<20} ({won_str})")

    finally:
        db.close()


if __name__ == "__main__":
    main()
