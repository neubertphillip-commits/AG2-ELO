"""
Import player data for tournaments that already have matches imported.
Uses batch queries to efficiently fetch player data from ScoreboardPlayers.

Usage:
    python import_player_data.py --tournament "LEC/2024 Season/Spring Season"
    python import_player_data.py --all
"""

import sys
import os
import argparse
import json
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.leaguepedia_loader import LeaguepediaLoader
from core.database import DatabaseManager
from core.team_resolver import TeamResolver


def load_tournament_name_mapping():
    """
    Load tournament name to URL mapping from discovery results.

    Returns:
        dict: Mapping of tournament name -> URL (with spaces)
    """
    mapping = {}

    # Load major regions discovery results
    major_file = Path(__file__).parent / "major_regions_discovery_results.json"
    if major_file.exists():
        try:
            with open(major_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for tournament in data.get('found_tournaments', []):
                    name = tournament.get('name')
                    url = tournament.get('url')
                    if name and url:
                        mapping[name] = url
        except Exception as e:
            print(f"⚠️  Could not load major_regions_discovery_results.json: {e}")

    # Load minor regions discovery results
    minor_file = Path(__file__).parent / "minor_regions_discovery_results.json"
    if minor_file.exists():
        try:
            with open(minor_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for tournament in data.get('found_tournaments', []):
                    name = tournament.get('name')
                    url = tournament.get('url')
                    if name and url:
                        mapping[name] = url
        except Exception as e:
            print(f"⚠️  Could not load minor_regions_discovery_results.json: {e}")

    return mapping


def chunks(lst, n):
    """Yield successive n-sized chunks from list."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def import_players_for_tournament(tournament_name: str, db: DatabaseManager, loader: LeaguepediaLoader, name_to_url_mapping: dict = None):
    """
    Import player data for a tournament using efficient batch queries.

    Args:
        tournament_name: Tournament name (e.g., "LEC/2024 Season/Spring Season")
        db: DatabaseManager instance
        loader: LeaguepediaLoader instance
        name_to_url_mapping: Optional mapping of tournament name -> URL

    Returns:
        Number of players imported
    """
    print(f"\n{'='*80}")
    print(f"Importing player data for: {tournament_name}")
    print(f"{'='*80}")

    # Initialize team resolver for normalizing team names
    team_resolver = TeamResolver()

    # Step 1: Get all games from ScoreboardGames
    print("\n[1/4] Fetching games from ScoreboardGames...")

    # Try to get URL from mapping first (for tournaments with slashes)
    tournament_url = tournament_name
    if name_to_url_mapping and tournament_name in name_to_url_mapping:
        tournament_url = name_to_url_mapping[tournament_name]
        print(f"📍 Mapped '{tournament_name}' -> '{tournament_url}'")

    # ScoreboardGames uses UNDERSCORES in OverviewPage (like ScoreboardPlayers)
    tournament_name_underscores = tournament_url.replace(' ', '_')

    # Query with pagination support for large tournaments
    all_games = []
    offset = 0
    batch_size = 500

    while True:
        # Note: Some fields like DateTime_UTC and UniqueGame cause internal API errors!
        # Use MatchId instead of UniqueGame - works without errors
        games_batch = loader._query_cargo(
            tables='ScoreboardGames',
            fields='GameId, MatchId, Team1, Team2',
            where=f'OverviewPage="{tournament_name_underscores}"',
            limit=batch_size
        )

        if not games_batch:
            break

        all_games.extend(games_batch)

        print(f"  Fetched {len(games_batch)} games (total: {len(all_games)})")

        if len(games_batch) < batch_size:
            break  # Last page

        # For pagination, would need to add offset support to _query_cargo
        # For now, assuming <500 games per tournament (which is typical)
        break

    if not all_games:
        print(f"⚠️  No games found for {tournament_name}")
        return 0

    print(f"✓ Found {len(all_games)} games")

    # Step 2: Get matches from database for this tournament
    print("\n[2/4] Loading matches from database...")
    matches = db.get_matches_by_tournament(tournament_name)

    if not matches:
        print(f"⚠️  No matches found in database for {tournament_name}")
        print(f"💡 Run the match import first: python major_regions_tournament_import_matchschedule.py")
        return 0

    print(f"✓ Found {len(matches)} matches in database")

    # Create mapping: external_id → match_id
    external_id_to_match = {}
    for match in matches:
        if match['external_id']:
            external_id_to_match[match['external_id']] = match['id']

    print(f"✓ Created mapping for {len(external_id_to_match)} matches with external_id")

    # Step 3: Fetch player data in batches of 50 games (= 500 players max)
    print(f"\n[3/4] Fetching player data in batches...")

    total_players_inserted = 0
    total_players_skipped = 0
    games_without_match = 0
    batch_count = 0

    for game_batch in chunks(all_games, 50):
        batch_count += 1
        game_ids = [g['GameId'] for g in game_batch]

        # Build WHERE clause: GameId IN ("id1", "id2", ...)
        game_ids_quoted = '","'.join(game_ids)
        where_clause = f'GameId IN ("{game_ids_quoted}")'

        # Query player data - only the fields we need
        players = loader._query_cargo(
            tables='ScoreboardPlayers',
            fields='Link, Role, Team, PlayerWin, GameId',
            where=where_clause,
            limit=500  # 50 games × 10 players = 500
        )

        print(f"  Batch {batch_count}: {len(players)} players from {len(game_batch)} games")

        # Step 4: Insert players into database
        for player_data in players:
            game_id = player_data.get('GameId', '')

            # Find the game to get UniqueGame (external_id)
            game = next((g for g in game_batch if g['GameId'] == game_id), None)
            if not game:
                continue

            match_id_from_game = game.get('MatchId', '')

            # Find match in database by external_id
            # MatchId from ScoreboardGames should match external_id in DB
            # (both come from MatchSchedule.UniqueMatch or MatchSchedule.MatchId)
            match_id = None

            # Try exact match first
            if match_id_from_game in external_id_to_match:
                match_id = external_id_to_match[match_id_from_game]
            else:
                # Try prefix match (in case external_id has additional suffix)
                for ext_id, m_id in external_id_to_match.items():
                    if match_id_from_game == ext_id or ext_id.startswith(match_id_from_game):
                        match_id = m_id
                        break

            if not match_id:
                games_without_match += 1
                continue

            # Insert player
            try:
                player_win = player_data.get('PlayerWin', '') == 'Yes'
                player_name = player_data.get('Link', '')
                team_name_raw = player_data.get('Team', '')

                # Normalize team name using team resolver (same as in match import)
                team_name_normalized = team_resolver.resolve(team_name_raw, None)

                inserted_id = db.insert_match_player(
                    match_id=match_id,
                    player_name=player_name,
                    team_name=team_name_normalized,
                    role=player_data.get('Role', ''),
                    champion=None,  # Not needed
                    kills=None,
                    deaths=None,
                    assists=None,
                    gold=None,
                    cs=None,
                    damage_to_champions=None,
                    vision_score=None,
                    items=None,
                    won=player_win
                )

                if inserted_id:
                    total_players_inserted += 1
                else:
                    total_players_skipped += 1

            except Exception as e:
                print(f"  ⚠️  Error inserting player {player_data.get('Link')}: {e}")
                total_players_skipped += 1

    # Summary
    print(f"\n{'='*80}")
    print(f"Import Summary for {tournament_name}")
    print(f"{'='*80}")
    print(f"Games processed:        {len(all_games)}")
    print(f"Players inserted:       {total_players_inserted}")
    print(f"Players skipped:        {total_players_skipped}")
    if games_without_match > 0:
        print(f"Games without match:    {games_without_match}")
    print(f"{'='*80}")

    return total_players_inserted


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Import player data for tournaments')
    parser.add_argument('--tournament', type=str, help='Tournament name (e.g., "LEC/2024 Season/Spring Season")')
    parser.add_argument('--all', action='store_true', help='Import players for all tournaments in database')

    args = parser.parse_args()

    if not args.tournament and not args.all:
        parser.print_help()
        return 1

    # Initialize
    db = DatabaseManager()
    loader = LeaguepediaLoader(db=db)

    try:
        total_imported = 0

        # Load tournament name -> URL mapping from discovery results
        print("Loading tournament name mappings...")
        name_to_url_mapping = load_tournament_name_mapping()
        if name_to_url_mapping:
            print(f"✓ Loaded {len(name_to_url_mapping)} tournament URL mappings")
        else:
            print("⚠️  No tournament mappings found (discovery results not available)")

        if args.all:
            # Get all unique tournaments from database
            print("\nFetching all tournaments from database...")
            tournaments = db.get_all_tournament_names()

            if not tournaments:
                print("No tournaments found in database!")
                return 1

            print(f"Found {len(tournaments)} tournaments")

            for i, tournament_name in enumerate(tournaments, 1):
                print(f"\n[{i}/{len(tournaments)}] Processing: {tournament_name}")
                imported = import_players_for_tournament(tournament_name, db, loader, name_to_url_mapping)
                total_imported += imported

            print(f"\n{'='*80}")
            print(f"TOTAL PLAYERS IMPORTED: {total_imported}")
            print(f"{'='*80}")
        else:
            # Import single tournament
            total_imported = import_players_for_tournament(args.tournament, db, loader, name_to_url_mapping)

        return 0

    finally:
        loader.close()
        db.close()


if __name__ == "__main__":
    exit(main())
