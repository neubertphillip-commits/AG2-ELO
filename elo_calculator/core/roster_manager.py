"""
Roster Manager - Efficient player-to-team mapping using roster data
Instead of querying player data per game, we query rosters once and infer players
"""

from typing import Dict, List, Optional, Set
from datetime import datetime
from collections import defaultdict
import requests
import time


class RosterManager:
    """
    Manages player-to-team mappings using roster data

    Approach:
    1. Query Rosters table for all teams (1 query per team)
    2. Query RosterChanges for transactions
    3. Build mapping: (team, role, date) → player
    4. Infer players for each game without additional queries
    """

    def __init__(self, api_endpoint: str, session: requests.Session, rate_limit_delay: float = 5.0):
        """Initialize roster manager"""
        self.api_endpoint = api_endpoint
        self.session = session
        self.rate_limit_delay = rate_limit_delay

        # Mappings
        self.team_rosters = {}  # team -> [(player, role, start_date, end_date)]
        self.active_rosters = defaultdict(dict)  # team -> {role: player}

    def _query_cargo(self, tables: str, fields: str, where: str = None,
                     limit: int = 500) -> List[Dict]:
        """Query Cargo API"""
        params = {
            'action': 'cargoquery',
            'format': 'json',
            'tables': tables,
            'fields': fields,
            'limit': min(limit, 500)
        }

        if where:
            params['where'] = where

        try:
            response = self.session.get(self.api_endpoint, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if 'error' in data:
                print(f"    [ERROR] Roster query error: {data['error'].get('info', '')}")
                return []

            if 'cargoquery' in data:
                return [item['title'] for item in data['cargoquery']]

            return []

        except requests.exceptions.RequestException as e:
            print(f"    [ERROR] Roster query failed: {e}")
            return []
        finally:
            time.sleep(self.rate_limit_delay)

    def load_tournament_rosters(self, tournament_name: str, teams: Set[str]) -> None:
        """
        Load rosters for all teams in a tournament

        Args:
            tournament_name: Tournament identifier
            teams: Set of team names in the tournament
        """
        print(f"\n[ROSTER] Loading rosters for {len(teams)} teams...")

        # Query Rosters table
        # Fields: Player (link), Role, Team, StartDate, EndDate
        for team in teams:
            roster_data = self._query_cargo(
                tables="Rosters",
                fields="Player, Role, Team, StartDate, EndDate",
                where=f"Rosters.Team='{team}'",
                limit=50  # Max 10 players per team
            )

            if roster_data:
                self.team_rosters[team] = []
                for entry in roster_data:
                    player = entry.get('Player', '')
                    role = entry.get('Role', '')
                    start_date = entry.get('StartDate', '')
                    end_date = entry.get('EndDate', '')

                    self.team_rosters[team].append({
                        'player': player,
                        'role': role,
                        'start_date': start_date,
                        'end_date': end_date
                    })

                print(f"  [OK] {team}: {len(roster_data)} roster entries")

        print(f"[ROSTER] Loaded rosters for {len(self.team_rosters)} teams")

    def get_players_for_game(self, team: str, game_date: datetime,
                            roles: List[str] = None) -> Dict[str, str]:
        """
        Get players for a team at a specific date

        Args:
            team: Team name
            game_date: Date of the game
            roles: List of roles (default: Top, Jungle, Mid, Bot, Support)

        Returns:
            Dict mapping role -> player name
        """
        if roles is None:
            roles = ['Top', 'Jungle', 'Mid', 'Bot', 'Support']

        if team not in self.team_rosters:
            return {}

        players = {}

        for role in roles:
            # Find active player for this role at game_date
            for roster_entry in self.team_rosters[team]:
                if roster_entry['role'] != role:
                    continue

                # Check date range
                start_date = roster_entry.get('start_date', '')
                end_date = roster_entry.get('end_date', '')

                # Parse dates (format: YYYY-MM-DD)
                try:
                    if start_date:
                        start = datetime.strptime(start_date, '%Y-%m-%d')
                        if game_date < start:
                            continue

                    if end_date:
                        end = datetime.strptime(end_date, '%Y-%m-%d')
                        if game_date > end:
                            continue

                    # This player was active for this role at this date
                    players[role] = roster_entry['player']
                    break

                except ValueError:
                    # Date parsing failed, skip
                    continue

        return players

    def get_roster_summary(self) -> Dict[str, int]:
        """Get summary of loaded rosters"""
        return {
            'teams': len(self.team_rosters),
            'total_entries': sum(len(roster) for roster in self.team_rosters.values())
        }


class RosterChangeManager:
    """
    Manages roster changes/transactions
    Tracks player movements between teams
    """

    def __init__(self, api_endpoint: str, session: requests.Session, rate_limit_delay: float = 5.0):
        """Initialize roster change manager"""
        self.api_endpoint = api_endpoint
        self.session = session
        self.rate_limit_delay = rate_limit_delay
        self.changes = []

    def load_roster_changes(self, start_date: str, end_date: str, teams: Set[str]) -> None:
        """
        Load roster changes for a period

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            teams: Set of team names to track
        """
        # Query RosterChanges table
        # This would contain transfers, substitutions, etc.
        # Implementation depends on Leaguepedia's RosterChanges table structure
        pass


if __name__ == "__main__":
    # Test roster loading
    from core.leaguepedia_loader import LeaguepediaLoader

    loader = LeaguepediaLoader()
    roster_mgr = RosterManager(
        api_endpoint=loader.API_ENDPOINT,
        session=loader.session,
        rate_limit_delay=loader.RATE_LIMIT_DELAY
    )

    # Test with a few LEC teams
    test_teams = {'G2 Esports', 'Fnatic', 'MAD Lions KOI'}
    roster_mgr.load_tournament_rosters('LEC/2024 Season/Summer Season', test_teams)

    # Get summary
    summary = roster_mgr.get_roster_summary()
    print(f"\n[SUMMARY] Loaded {summary['teams']} teams, {summary['total_entries']} roster entries")

    # Test player lookup
    test_date = datetime(2024, 7, 1)
    for team in test_teams:
        players = roster_mgr.get_players_for_game(team, test_date)
        print(f"\n{team} roster on {test_date.date()}:")
        for role, player in players.items():
            print(f"  {role}: {player}")
