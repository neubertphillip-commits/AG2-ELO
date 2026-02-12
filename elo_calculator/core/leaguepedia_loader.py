"""
Leaguepedia API Loader for LOL ELO System
Fetches match data from Leaguepedia for Tier 1 leagues
"""

import requests
from datetime import datetime
from typing import Dict, List, Optional, Set
from urllib.parse import urlencode
import time
from core.database import DatabaseManager


class LeaguepediaLoader:
    """
    Loads match data from Leaguepedia API
    Supports LEC, LPL, LCK, LCS and international tournaments

    Implementation follows Leaguepedia API best practices:
    - Uses 3 second delay between requests (recommended: 1-2s)
    - Limits queries to 500 results (API maximum for non-admins)
    - Uses ScoreboardGames/ScoreboardPlayers tables (not Players directly)
    - Uses GameId for joins (not row IDs which change on Cargo rebuild)
    - Uses __full suffix for list-type fields (e.g., Items__full)

    See: https://lol.fandom.com/wiki/Help:Leaguepedia_API
    """

    # Tier 1 League configurations (2013-present)
    TIER1_LEAGUES = {
        # European leagues
        'LEC': {
            'region': 'EU',
            'names': ['LEC', 'EU LCS'],  # EU LCS was renamed to LEC in 2019
            'splits': ['Spring', 'Summer'],
            'start_year': 2013
        },
        # Chinese league
        'LPL': {
            'region': 'CN',
            'names': ['LPL'],
            'splits': ['Spring', 'Summer'],
            'start_year': 2013
        },
        # Korean league
        'LCK': {
            'region': 'KR',
            'names': ['LCK', 'Champions'],  # Champions was renamed to LCK
            'splits': ['Spring', 'Summer'],
            'start_year': 2013
        },
        # North American league
        'LCS': {
            'region': 'NA',
            'names': ['LCS', 'NA LCS'],  # NA LCS was renamed to LCS
            'splits': ['Spring', 'Summer'],
            'start_year': 2013
        },
        # International tournaments
        'WORLDS': {
            'region': 'International',
            'names': ['World Championship', 'Worlds'],
            'splits': ['Main Event'],
            'start_year': 2013
        },
        'MSI': {
            'region': 'International',
            'names': ['Mid-Season Invitational', 'MSI'],
            'splits': ['Main Event'],
            'start_year': 2015  # MSI started in 2015
        }
    }

    API_ENDPOINT = "https://lol.fandom.com/api.php"
    RATE_LIMIT_DELAY = 3.0  # seconds between requests (optimal with bot auth)
    MAX_RETRIES = 10  # number of retries for rate-limited requests

    def __init__(self, db: DatabaseManager = None, bot_username: str = None, bot_password: str = None):
        """
        Initialize Leaguepedia loader

        Args:
            db: DatabaseManager instance (creates new if None)
            bot_username: Bot username from Special:BotPasswords (optional, for higher rate limits)
            bot_password: Bot password from Special:BotPasswords (optional)
        """
        self.db = db or DatabaseManager()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'LOL-ELO-System/1.0 (Educational Research)'
        })

        # Bot authentication (optional - reduces rate limiting)
        self.authenticated = False
        if bot_username and bot_password:
            self._login(bot_username, bot_password)
        else:
            # Try to get credentials from environment variables
            import os
            env_username = os.getenv('LEAGUEPEDIA_BOT_USERNAME')
            env_password = os.getenv('LEAGUEPEDIA_BOT_PASSWORD')
            if env_username and env_password:
                self._login(env_username, env_password)
            else:
                print("[INFO] Running without authentication - rate limits may apply")
                print("[INFO] To authenticate, set LEAGUEPEDIA_BOT_USERNAME and LEAGUEPEDIA_BOT_PASSWORD")
                print("[INFO] or create bot credentials at: https://lol.fandom.com/wiki/Special:BotPasswords")

    def _login(self, username: str, password: str) -> bool:
        """
        Authenticate with Leaguepedia using bot credentials

        Args:
            username: Bot username (e.g., 'YourName@BotName')
            password: Bot password from Special:BotPasswords

        Returns:
            True if authentication successful
        """
        try:
            # Step 1: Get login token
            token_params = {
                'action': 'query',
                'meta': 'tokens',
                'type': 'login',
                'format': 'json'
            }

            response = self.session.get(self.API_ENDPOINT, params=token_params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if 'query' not in data or 'tokens' not in data['query']:
                print(f"[ERROR] Failed to get login token: {data}")
                return False

            login_token = data['query']['tokens']['logintoken']

            # Step 2: Login with credentials
            login_params = {
                'action': 'login',
                'lgname': username,
                'lgpassword': password,
                'lgtoken': login_token,
                'format': 'json'
            }

            response = self.session.post(self.API_ENDPOINT, data=login_params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if 'login' in data:
                result = data['login'].get('result', '')
                if result == 'Success':
                    self.authenticated = True
                    print(f"[OK] Authenticated as {username}")
                    return True
                else:
                    print(f"[ERROR] Login failed: {result}")
                    if 'reason' in data['login']:
                        print(f"[ERROR] Reason: {data['login']['reason']}")
                    return False
            else:
                print(f"[ERROR] Unexpected login response: {data}")
                return False

        except Exception as e:
            print(f"[ERROR] Authentication failed: {e}")
            return False

    def _query_cargo(self, tables: str, fields: str, where: str = None,
                     join_on: str = None, order_by: str = None,
                     limit: int = 500, debug: bool = False) -> List[Dict]:
        """
        Query Leaguepedia Cargo database

        Args:
            tables: Table name(s) to query
            fields: Fields to retrieve
            where: WHERE clause
            join_on: JOIN conditions
            order_by: ORDER BY clause
            limit: Result limit (max 500 for non-admins)
            debug: Print debug information

        Returns:
            List of result dictionaries
        """
        params = {
            'action': 'cargoquery',
            'format': 'json',
            'tables': tables,
            'fields': fields,
            'limit': min(limit, 500)
        }

        if where:
            params['where'] = where
        if join_on:
            params['join_on'] = join_on
        if order_by:
            params['order_by'] = order_by

        # Retry logic for rate limiting
        for attempt in range(self.MAX_RETRIES):
            try:
                if debug:
                    print(f"    DEBUG: Query params: {params}")

                response = self.session.get(self.API_ENDPOINT, params=params, timeout=30)
                response.raise_for_status()

                data = response.json()

                if debug:
                    print(f"    DEBUG: Response status: {response.status_code}")
                    print(f"    DEBUG: Response keys: {data.keys()}")
                    if 'error' in data:
                        print(f"    DEBUG ERROR: {data['error']}")
                    if 'cargoquery' in data:
                        print(f"    DEBUG: Found {len(data['cargoquery'])} results")

                # Check for API errors (e.g., rate limiting)
                if 'error' in data:
                    error_code = data['error'].get('code', '')
                    error_info = data['error'].get('info', '')

                    if error_code == 'ratelimited':
                        if attempt < self.MAX_RETRIES - 1:
                            # Exponential backoff: wait longer on each retry
                            wait_time = self.RATE_LIMIT_DELAY * (2 ** attempt)
                            print(f" [RETRY {attempt + 1}/{self.MAX_RETRIES}, waiting {int(wait_time)}s]", end="")
                            time.sleep(wait_time)
                            continue  # Retry
                        else:
                            print(f" [FAILED after {self.MAX_RETRIES} retries]", end="")
                            return []
                    else:
                        print(f"    [ERROR] API Error: {error_code} - {error_info}")
                        return []

                if 'cargoquery' in data:
                    results = [item['title'] for item in data['cargoquery']]
                    if not results and debug:
                        print(f"    DEBUG: Query returned 0 results (not an error, just no matching data)")
                    return results

                return []

            except requests.exceptions.RequestException as e:
                if attempt < self.MAX_RETRIES - 1:
                    wait_time = self.RATE_LIMIT_DELAY * (2 ** attempt)
                    print(f"    [WARNING] Request failed: {e} - retrying in {wait_time}s")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"    [ERROR] API request failed after {self.MAX_RETRIES} retries: {e}")
                    return []

            finally:
                # Rate limiting - always wait between requests
                if attempt == self.MAX_RETRIES - 1 or 'data' in locals():
                    time.sleep(self.RATE_LIMIT_DELAY)

    def _build_tournament_name(self, league: str, year: int, split: str) -> str:
        """
        Build tournament name for query

        Args:
            league: League name (LEC, LPL, etc.)
            year: Calendar year
            split: Split (Spring, Summer, Main Event)

        Returns:
            Tournament name for Leaguepedia
        """
        config = self.TIER1_LEAGUES.get(league)
        if not config:
            return f"{league}/{year} Season/{split} Season"

        # Handle name variations
        primary_name = config['names'][0]

        # Special cases for league rebranding
        if league == 'LEC' and year < 2019:
            primary_name = 'EU LCS'
        elif league == 'LCS' and year < 2018:
            primary_name = 'NA LCS'

        # International tournaments use "YEAR Tournament-Name" format
        # MSI: "2024 Mid-Season Invitational"
        # Worlds: "2024 Season World Championship/Main Event"
        if league in ['MSI', 'WORLDS']:
            if league == 'WORLDS':
                # Worlds uses: "YEAR Season World Championship/Main Event"
                return f"{year} Season {primary_name}/{split}"
            else:
                # MSI uses: "YEAR Mid-Season Invitational"
                return f"{year} {primary_name}"
        else:
            # Regional leagues use: "LEC/2024 Season/Summer Season"
            return f"{primary_name}/{year} Season/{split} Season"

    def get_tournament_matches(self, tournament_name: str,
                               include_players: bool = True,
                               stage_filter: str = None,
                               use_roster_inference: bool = True) -> int:
        """
        Load matches from a specific tournament

        Args:
            tournament_name: Tournament name (e.g. "LEC/2024 Season/Summer")
            include_players: Whether to fetch player data
            stage_filter: Optional stage filter (e.g. "Playoffs")
            use_roster_inference: Use roster data to infer players (MUCH faster!)
                                 True: ~10 queries per tournament (recommended)
                                 False: ~150 queries per tournament (old method)

        Returns:
            Number of matches imported
        """
        print(f"\n[LOADING] Fetching matches from: {tournament_name}")

        if include_players and use_roster_inference:
            print(f"[INFO] Using roster inference for player data (efficient mode)")
        elif include_players and not use_roster_inference:
            print(f"[WARNING] Using per-game player queries (slow, may cause rate limiting!)")

        # Build WHERE clause
        # IMPORTANT: Don't use table prefixes in WHERE - causes MWException
        where_parts = [f"OverviewPage='{tournament_name}'"]
        if stage_filter:
            where_parts.append(f"Tab='{stage_filter}'")

        where = " AND ".join(where_parts)

        # Query ScoreboardGames
        # IMPORTANT: Don't use table prefixes - causes MWException with WHERE clauses
        # IMPORTANT: "Tab" field causes MWException - cannot be queried!
        fields = [
            "GameId",
            "Team1",
            "Team2",
            "Team1Score",
            "Team2Score",
            "Winner",
            "DateTime_UTC",
            "OverviewPage",
            # "Tab",  # REMOVED: Causes MWException
            "Patch",
            "Gamelength"
        ]

        games = self._query_cargo(
            tables="ScoreboardGames",
            fields=", ".join(fields),
            where=where,
            order_by="DateTime_UTC",
            limit=500
        )

        print(f"  Found {len(games)} games in API")

        matches_by_id = {}
        imported_count = 0
        skipped_count = 0

        # Process games and aggregate to matches
        for game in games:
            try:
                # Extract game data
                game_id = game.get('GameId')
                team1 = game.get('Team1')
                team2 = game.get('Team2')
                winner = int(game.get('Winner', 0))
                date_str = game.get('DateTime UTC')
                # Tab field cannot be queried (causes MWException)
                # Infer stage from tournament_name instead
                stage = 'Playoffs' if 'Playoff' in tournament_name else 'Regular Season'
                patch = game.get('Patch')

                # Parse date
                if date_str:
                    try:
                        date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        # Try alternative format
                        date = datetime.strptime(date_str, "%Y-%m-%d")
                else:
                    print(f"  [WARNING] Skipping game {game_id}: no date")
                    continue

                # Extract match ID (games are part of matches)
                # Format: "ESPORTSTMNT01_1234567_1" -> match is "ESPORTSTMNT01_1234567"
                if game_id and '_' in game_id:
                    parts = game_id.rsplit('_', 1)
                    match_id = parts[0]
                    game_number = int(parts[1]) if len(parts) > 1 else 1
                else:
                    match_id = game_id
                    game_number = 1

                # Aggregate games into matches
                if match_id not in matches_by_id:
                    matches_by_id[match_id] = {
                        'team1': team1,
                        'team2': team2,
                        'team1_score': 0,
                        'team2_score': 0,
                        'date': date,
                        'tournament': tournament_name,
                        'stage': stage,
                        'patch': patch,
                        'games': []
                    }

                # Update score based on winner
                if winner == 1:
                    matches_by_id[match_id]['team1_score'] += 1
                elif winner == 2:
                    matches_by_id[match_id]['team2_score'] += 1

                # Store game for player data
                matches_by_id[match_id]['games'].append({
                    'game_id': game_id,
                    'game_number': game_number
                })

            except Exception as e:
                print(f"  [WARNING] Error processing game: {e}")
                continue

        print(f"  Aggregated into {len(matches_by_id)} matches")

        # Load roster data if using inference method
        roster_mgr = None
        if include_players and use_roster_inference:
            # Extract all unique teams from matches
            all_teams = set()
            for match_data in matches_by_id.values():
                all_teams.add(match_data['team1'])
                all_teams.add(match_data['team2'])

            # Load rosters for all teams (N queries where N = number of teams)
            from core.roster_manager import RosterManager
            roster_mgr = RosterManager(
                api_endpoint=self.API_ENDPOINT,
                session=self.session,
                rate_limit_delay=self.RATE_LIMIT_DELAY
            )
            roster_mgr.load_tournament_rosters(tournament_name, all_teams)

            summary = roster_mgr.get_roster_summary()
            print(f"  [ROSTER] Loaded {summary['total_entries']} roster entries for {summary['teams']} teams")
            print(f"  [EFFICIENCY] Using roster inference: ~{summary['teams']} queries instead of ~{len(games)} queries!")

        # Insert matches into database
        for match_id, match_data in matches_by_id.items():
            try:
                # Extract region from tournament name
                region = None
                for league, config in self.TIER1_LEAGUES.items():
                    if any(name in tournament_name for name in config['names']):
                        region = config['region']
                        break

                db_match_id = self.db.insert_match(
                    team1_name=match_data['team1'],
                    team2_name=match_data['team2'],
                    team1_score=match_data['team1_score'],
                    team2_score=match_data['team2_score'],
                    date=match_data['date'],
                    tournament_name=tournament_name,
                    stage=match_data['stage'],
                    patch=match_data['patch'],
                    external_id=match_id,
                    source='leaguepedia',
                    region=region
                )

                if db_match_id:
                    imported_count += 1

                    # Import player data using one of two methods:
                    if include_players:
                        if use_roster_inference and roster_mgr:
                            # METHOD 1: Roster Inference (EFFICIENT)
                            # Infer players from roster data (no API queries!)
                            self._infer_players_from_roster(
                                db_match_id, match_data, roster_mgr
                            )
                        else:
                            # METHOD 2: Per-Game Queries (SLOW)
                            # WARNING: Makes MANY API queries (1 per game)
                            # This will cause rate limiting for large tournaments
                            for game in match_data['games']:
                                self._fetch_game_players(
                                    db_match_id, game['game_id'],
                                    match_data['team1'],
                                    match_data['team2']
                                )
                else:
                    skipped_count += 1

            except Exception as e:
                print(f"  [WARNING] Error inserting match {match_id}: {e}")
                continue

        print(f"  [OK] Imported: {imported_count} matches")
        if skipped_count > 0:
            print(f"  [SKIP] Skipped (duplicates): {skipped_count} matches")

        return imported_count

    def _infer_players_from_roster(self, match_id: int, match_data: Dict,
                                   roster_mgr) -> None:
        """
        Infer player lineup from roster data (no API queries!)

        This is MUCH more efficient than querying per game:
        - Uses pre-loaded roster data
        - Assumes roster stability between transactions
        - No additional API calls needed

        Args:
            match_id: Database match ID
            match_data: Match data dict with team1, team2, date
            roster_mgr: RosterManager instance with loaded roster data
        """
        roles = ['Top', 'Jungle', 'Mid', 'Bot', 'Support']

        # Get players for team1
        team1_players = roster_mgr.get_players_for_game(
            team=match_data['team1'],
            game_date=match_data['date'],
            roles=roles
        )

        # Get players for team2
        team2_players = roster_mgr.get_players_for_game(
            team=match_data['team2'],
            game_date=match_data['date'],
            roles=roles
        )

        # Insert team1 players
        for role, player_name in team1_players.items():
            if player_name:  # Only insert if we have a player
                try:
                    self.db.insert_match_player(
                        match_id=match_id,
                        player_name=player_name,
                        team_name=match_data['team1'],
                        role=role,
                        # Note: We don't have game statistics from roster data
                        # These would require per-game queries
                        champion=None,
                        kills=None,
                        deaths=None,
                        assists=None,
                        gold=None,
                        cs=None,
                        damage_to_champions=None,
                        vision_score=None,
                        items=None,
                        won=None
                    )
                except Exception as e:
                    print(f"    [WARNING] Error inserting player {player_name} (Team1): {e}")

        # Insert team2 players
        for role, player_name in team2_players.items():
            if player_name:  # Only insert if we have a player
                try:
                    self.db.insert_match_player(
                        match_id=match_id,
                        player_name=player_name,
                        team_name=match_data['team2'],
                        role=role,
                        # Note: We don't have game statistics from roster data
                        champion=None,
                        kills=None,
                        deaths=None,
                        assists=None,
                        gold=None,
                        cs=None,
                        damage_to_champions=None,
                        vision_score=None,
                        items=None,
                        won=None
                    )
                except Exception as e:
                    print(f"    [WARNING] Error inserting player {player_name} (Team2): {e}")

    def _fetch_game_players(self, match_id: int, game_id: str,
                           team1_name: str, team2_name: str) -> None:
        """
        Fetch player data for a specific game

        Note: We query ScoreboardPlayers.Link (not Players table directly)
        as recommended by Leaguepedia API docs. The Link field handles
        player name disambiguation automatically.

        For advanced player tracking with renames, would need to join:
        ScoreboardPlayers -> PlayerRedirects -> Players

        Args:
            match_id: Database match ID
            game_id: Leaguepedia game ID
            team1_name: Team 1 name
            team2_name: Team 2 name
        """
        fields = [
            "ScoreboardPlayers.Link",
            "ScoreboardPlayers.Team",
            "ScoreboardPlayers.Role",
            "ScoreboardPlayers.Champion",
            "ScoreboardPlayers.Kills",
            "ScoreboardPlayers.Deaths",
            "ScoreboardPlayers.Assists",
            "ScoreboardPlayers.Gold",
            "ScoreboardPlayers.CS",
            "ScoreboardPlayers.DamageToChampions",
            "ScoreboardPlayers.VisionScore",
            "ScoreboardPlayers.Items__full",  # Use __full suffix for list fields
            "ScoreboardPlayers.PlayerWin"
        ]

        players = self._query_cargo(
            tables="ScoreboardPlayers",
            fields=", ".join(fields),
            where=f"ScoreboardPlayers.GameId='{game_id}'",
            limit=10  # 5 players per team
        )

        for player_data in players:
            try:
                self.db.insert_match_player(
                    match_id=match_id,
                    player_name=player_data.get('Link', ''),
                    team_name=player_data.get('Team', ''),
                    role=player_data.get('Role'),
                    champion=player_data.get('Champion'),
                    kills=int(player_data.get('Kills', 0)) if player_data.get('Kills') else None,
                    deaths=int(player_data.get('Deaths', 0)) if player_data.get('Deaths') else None,
                    assists=int(player_data.get('Assists', 0)) if player_data.get('Assists') else None,
                    gold=int(player_data.get('Gold', 0)) if player_data.get('Gold') else None,
                    cs=int(player_data.get('CS', 0)) if player_data.get('CS') else None,
                    damage_to_champions=int(player_data.get('DamageToChampions', 0)) if player_data.get('DamageToChampions') else None,
                    vision_score=int(player_data.get('VisionScore', 0)) if player_data.get('VisionScore') else None,
                    # Items__full returns as "Items full" in response
                    items=player_data.get('Items full', '').split(';') if player_data.get('Items full') else None,
                    won=player_data.get('PlayerWin') == 'Yes'
                )
            except Exception as e:
                print(f"    [WARNING] Error inserting player {player_data.get('Link')}: {e}")

    def import_league_season(self, league: str, year: int, split: str,
                            include_playoffs: bool = True,
                            include_players: bool = True) -> int:
        """
        Import entire league season (regular + playoffs)

        Args:
            league: League code (LEC, LPL, LCK, LCS, etc.)
            year: Year
            split: Split (Spring, Summer)
            include_playoffs: Whether to import playoffs
            include_players: Whether to fetch player data

        Returns:
            Total matches imported
        """
        tournament_name = self._build_tournament_name(league, year, split)
        total_imported = 0

        # Import regular season
        print(f"\n[LEAGUE] Importing {league} {year} {split}")
        imported = self.get_tournament_matches(
            tournament_name=tournament_name,
            include_players=include_players
        )
        total_imported += imported

        # Import playoffs if requested
        # International tournaments (MSI, Worlds) don't have separate playoffs
        if include_playoffs and league not in ['MSI', 'WORLDS']:
            # Playoffs are usually separate pages (e.g., "LEC/2024 Season/Summer Playoffs")
            # Remove " Season" suffix and add " Playoffs"
            if " Season" in tournament_name:
                playoff_tournament = tournament_name.replace(" Season", " Playoffs")
            else:
                playoff_tournament = f"{tournament_name} Playoffs"

            try:
                imported = self.get_tournament_matches(
                    tournament_name=playoff_tournament,
                    include_players=include_players
                )
                total_imported += imported
            except Exception as e:
                # Some tournaments might not have separate playoffs page
                print(f"  [INFO] No separate playoffs found ({e})")
                pass

        return total_imported

    def import_all_tier1(self, start_year: int = 2013, end_year: int = None,
                        include_players: bool = True) -> Dict[str, int]:
        """
        Import all Tier 1 leagues from start_year to end_year

        Args:
            start_year: Starting year (default: 2013)
            end_year: Ending year (default: current year)
            include_players: Whether to fetch player data

        Returns:
            Dictionary with import statistics
        """
        if end_year is None:
            end_year = datetime.now().year

        stats = {
            'total_matches': 0,
            'by_league': {}
        }

        print(f"\n[START] Starting Tier 1 import: {start_year}-{end_year}")

        for league, config in self.TIER1_LEAGUES.items():
            league_start = max(start_year, config['start_year'])
            league_total = 0

            for year in range(league_start, end_year + 1):
                for split in config['splits']:
                    try:
                        imported = self.import_league_season(
                            league=league,
                            year=year,
                            split=split,
                            include_players=include_players
                        )
                        league_total += imported

                    except Exception as e:
                        print(f"  [WARNING] Error importing {league} {year} {split}: {e}")
                        continue

            stats['by_league'][league] = league_total
            stats['total_matches'] += league_total

        return stats

    def close(self):
        """Close session and database"""
        self.session.close()
        if self.db:
            self.db.close()


if __name__ == "__main__":
    # Test loading
    print("Testing Leaguepedia Loader...")

    loader = LeaguepediaLoader()

    # Test single tournament
    print("\n--- Test: LEC 2024 Summer ---")
    loader.import_league_season(
        league='LEC',
        year=2024,
        split='Summer',
        include_players=True
    )

    # Show stats
    stats = loader.db.get_stats()
    print(f"\n[STATS] Database Stats:")
    print(f"  Total Matches: {stats['total_matches']}")
    print(f"  Total Teams: {stats['total_teams']}")
    print(f"  Total Players: {stats['total_players']}")

    loader.close()
