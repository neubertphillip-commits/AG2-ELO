"""
Interactive database viewer for LOL ELO System
Browse matches, teams, players, and statistics
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import DatabaseManager
import sqlite3

def print_stats(db):
    """Print database statistics"""
    stats = db.get_stats()

    print("\n" + "="*70)
    print("DATABASE STATISTICS")
    print("="*70)

    print(f"\n[STATS] Overview:")
    print(f"  Total Matches: {stats['total_matches']}")
    print(f"  Total Teams: {stats['total_teams']}")
    print(f"  Total Players: {stats['total_players']}")
    print(f"  Total Tournaments: {stats['total_tournaments']}")

    if stats['date_range'][0] and stats['date_range'][1]:
        print(f"\n📅 Date Range:")
        print(f"  From: {stats['date_range'][0]}")
        print(f"  To:   {stats['date_range'][1]}")

    if 'by_source' in stats:
        print(f"\n📋 By Source:")
        for source, count in stats['by_source'].items():
            print(f"  {source:20s}: {count:5d} matches")

def print_recent_matches(db, limit=10):
    """Print recent matches"""
    matches = db.get_all_matches(limit=limit)

    print(f"\n" + "="*70)
    print(f"RECENT {limit} MATCHES")
    print("="*70)

    for m in matches:
        score = f"{m['team1_score']}-{m['team2_score']}"
        winner_mark = "[OK]" if m['winner'] == m['team1_name'] else " "
        loser_mark = "[OK]" if m['winner'] == m['team2_name'] else " "

        print(f"\n{m['date'][:10]} | {m['tournament'] or 'Unknown Tournament'}")
        print(f"  {winner_mark} {m['team1_name']:30s} {score:5s} {m['team2_name']:30s} {loser_mark}")
        if m['stage']:
            print(f"     Stage: {m['stage']}, Patch: {m['patch'] or 'N/A'}, Source: {m['source']}")

def print_teams(db, limit=20, order_by='elo'):
    """Print teams"""
    cursor = db.conn.cursor()

    if order_by == 'elo':
        order_clause = "current_elo DESC"
        title = f"TOP {limit} TEAMS BY ELO"
    elif order_by == 'name':
        order_clause = "name"
        title = f"TEAMS (Alphabetical, limit {limit})"
    else:
        order_clause = "id DESC"
        title = f"RECENT {limit} TEAMS"

    cursor.execute(f"""
        SELECT id, name, region, current_elo
        FROM teams
        ORDER BY {order_clause}
        LIMIT ?
    """, (limit,))

    teams = cursor.fetchall()

    print(f"\n" + "="*70)
    print(title)
    print("="*70)
    print(f"\n{'Rank':5s} {'Team':35s} {'Region':8s} {'ELO':8s}")
    print("-"*70)

    for i, team in enumerate(teams, 1):
        region = team[2] or 'N/A'
        elo = f"{team[3]:.0f}"
        print(f"{i:5d} {team[1]:35s} {region:8s} {elo:8s}")

def print_players(db, limit=20, order_by='elo'):
    """Print players"""
    cursor = db.conn.cursor()

    if order_by == 'elo':
        order_clause = "current_elo DESC"
        title = f"TOP {limit} PLAYERS BY ELO"
    else:
        order_clause = "name"
        title = f"PLAYERS (Alphabetical, limit {limit})"

    cursor.execute(f"""
        SELECT id, name, role, current_elo
        FROM players
        ORDER BY {order_clause}
        LIMIT ?
    """, (limit,))

    players = cursor.fetchall()

    print(f"\n" + "="*70)
    print(title)
    print("="*70)
    print(f"\n{'Rank':5s} {'Player':30s} {'Role':10s} {'ELO':8s}")
    print("-"*70)

    for i, player in enumerate(players, 1):
        role = player[2] or 'N/A'
        elo = f"{player[3]:.0f}"
        print(f"{i:5d} {player[1]:30s} {role:10s} {elo:8s}")

def search_team(db, team_name):
    """Search for a team and show details"""
    cursor = db.conn.cursor()

    # Find team
    cursor.execute("""
        SELECT id, name, region, current_elo
        FROM teams
        WHERE name LIKE ?
    """, (f"%{team_name}%",))

    teams = cursor.fetchall()

    if not teams:
        print(f"\n❌ No teams found matching '{team_name}'")
        return

    print(f"\n" + "="*70)
    print(f"TEAMS MATCHING '{team_name}'")
    print("="*70)

    for team in teams:
        team_id, name, region, elo = team

        print(f"\n[STATS] {name}")
        print(f"   Region: {region or 'N/A'}")
        print(f"   Current ELO: {elo:.0f}")

        # Recent matches
        cursor.execute("""
            SELECT m.date, m.team1_score, m.team2_score,
                   t1.name as team1, t2.name as team2, tw.name as winner,
                   tour.name as tournament, m.stage
            FROM matches m
            JOIN teams t1 ON m.team1_id = t1.id
            JOIN teams t2 ON m.team2_id = t2.id
            JOIN teams tw ON m.winner_id = tw.id
            LEFT JOIN tournaments tour ON m.tournament_id = tour.id
            WHERE t1.id = ? OR t2.id = ?
            ORDER BY m.date DESC
            LIMIT 10
        """, (team_id, team_id))

        matches = cursor.fetchall()

        if matches:
            print(f"\n   Recent 10 Matches:")
            for match in matches:
                date, score1, score2, t1, t2, winner, tournament, stage = match
                is_team1 = t1 == name
                opp = t2 if is_team1 else t1
                result = "W" if winner == name else "L"
                score = f"{score1}-{score2}" if is_team1 else f"{score2}-{score1}"

                print(f"   {date[:10]} {result} vs {opp:30s} ({score}) - {tournament or 'Unknown'}")

        # Match stats
        cursor.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN winner_id = ? THEN 1 ELSE 0 END) as wins
            FROM matches
            WHERE team1_id = ? OR team2_id = ?
        """, (team_id, team_id, team_id))

        total, wins = cursor.fetchone()
        win_rate = (wins / total * 100) if total > 0 else 0

        print(f"\n   Overall Record: {wins}-{total - wins} ({win_rate:.1f}% win rate)")

def search_player(db, player_name):
    """Search for a player and show details"""
    cursor = db.conn.cursor()

    cursor.execute("""
        SELECT id, name, role, current_elo
        FROM players
        WHERE name LIKE ?
    """, (f"%{player_name}%",))

    players = cursor.fetchall()

    if not players:
        print(f"\n❌ No players found matching '{player_name}'")
        return

    print(f"\n" + "="*70)
    print(f"PLAYERS MATCHING '{player_name}'")
    print("="*70)

    for player in players:
        player_id, name, role, elo = player

        print(f"\n🎮 {name}")
        print(f"   Role: {role or 'N/A'}")
        print(f"   Current ELO: {elo:.0f}")

        # Game count
        cursor.execute("""
            SELECT COUNT(*) FROM match_players WHERE player_id = ?
        """, (player_id,))

        games = cursor.fetchone()[0]
        print(f"   Games Played: {games}")

        if games > 0:
            # Average stats
            cursor.execute("""
                SELECT
                    AVG(kills) as avg_kills,
                    AVG(deaths) as avg_deaths,
                    AVG(assists) as avg_assists,
                    SUM(CASE WHEN won = 1 THEN 1 ELSE 0 END) as wins
                FROM match_players
                WHERE player_id = ?
            """, (player_id,))

            avg_k, avg_d, avg_a, wins = cursor.fetchone()
            win_rate = (wins / games * 100) if games > 0 else 0

            if avg_k is not None:
                kda = ((avg_k + avg_a) / avg_d) if avg_d and avg_d > 0 else 0
                print(f"\n   Stats:")
                print(f"     KDA: {avg_k:.1f}/{avg_d:.1f}/{avg_a:.1f} ({kda:.2f})")
                print(f"     Win Rate: {win_rate:.1f}% ({wins}W-{games-wins}L)")

def interactive_menu():
    """Interactive menu for browsing database"""
    db = DatabaseManager()

    while True:
        print("\n" + "="*70)
        print("DATABASE VIEWER - INTERACTIVE MENU")
        print("="*70)
        print("\n1. Show Statistics")
        print("2. Show Recent Matches")
        print("3. Show Top Teams (by ELO)")
        print("4. Show All Teams (alphabetical)")
        print("5. Show Top Players (by ELO)")
        print("6. Search Team")
        print("7. Search Player")
        print("8. Custom SQL Query")
        print("9. Exit")

        choice = input("\nSelect option (1-9): ").strip()

        if choice == '1':
            print_stats(db)
        elif choice == '2':
            limit = input("How many matches? (default 10): ").strip()
            limit = int(limit) if limit.isdigit() else 10
            print_recent_matches(db, limit)
        elif choice == '3':
            limit = input("How many teams? (default 20): ").strip()
            limit = int(limit) if limit.isdigit() else 20
            print_teams(db, limit, order_by='elo')
        elif choice == '4':
            limit = input("How many teams? (default 50): ").strip()
            limit = int(limit) if limit.isdigit() else 50
            print_teams(db, limit, order_by='name')
        elif choice == '5':
            limit = input("How many players? (default 20): ").strip()
            limit = int(limit) if limit.isdigit() else 20
            print_players(db, limit, order_by='elo')
        elif choice == '6':
            team_name = input("Enter team name (partial match): ").strip()
            if team_name:
                search_team(db, team_name)
        elif choice == '7':
            player_name = input("Enter player name (partial match): ").strip()
            if player_name:
                search_player(db, player_name)
        elif choice == '8':
            print("\n[WARNING]  Warning: Use with caution!")
            query = input("Enter SQL query: ").strip()
            if query:
                try:
                    cursor = db.conn.cursor()
                    cursor.execute(query)
                    results = cursor.fetchall()

                    if results:
                        print(f"\nResults ({len(results)} rows):")
                        for row in results[:50]:  # Limit to 50 rows
                            print(row)
                        if len(results) > 50:
                            print(f"\n... and {len(results) - 50} more rows")
                    else:
                        print("\nNo results")
                except Exception as e:
                    print(f"\n❌ Error: {e}")
        elif choice == '9':
            print("\n👋 Goodbye!")
            db.close()
            break
        else:
            print("\n❌ Invalid option")

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # Command line mode
        db = DatabaseManager()
        command = sys.argv[1].lower()

        if command == 'stats':
            print_stats(db)
        elif command == 'matches':
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            print_recent_matches(db, limit)
        elif command == 'teams':
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
            print_teams(db, limit)
        elif command == 'players':
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
            print_players(db, limit)
        elif command == 'team':
            if len(sys.argv) > 2:
                search_team(db, ' '.join(sys.argv[2:]))
            else:
                print("Usage: python view_database.py team <team_name>")
        elif command == 'player':
            if len(sys.argv) > 2:
                search_player(db, ' '.join(sys.argv[2:]))
            else:
                print("Usage: python view_database.py player <player_name>")
        else:
            print("Unknown command. Available: stats, matches, teams, players, team <name>, player <name>")

        db.close()
    else:
        # Interactive mode
        interactive_menu()
