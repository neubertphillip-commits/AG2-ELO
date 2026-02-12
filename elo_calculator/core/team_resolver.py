"""
Team Name Resolution System
Handles team name normalization, aliases, and historical renames
"""

import re
from typing import Dict, Optional, List
from datetime import datetime
from difflib import get_close_matches
import json
from pathlib import Path


class TeamResolver:
    """
    Resolves team names to canonical identifiers

    Uses 3-tier strategy:
    1. Leaguepedia Teams table (official data)
    2. Manual mappings (custom corrections)
    3. Fuzzy matching + normalization (fallback)
    """

    def __init__(self, loader=None, db=None):
        """
        Initialize TeamResolver

        Args:
            loader: LeaguepediaLoader instance (optional, for loading team data)
            db: DatabaseManager instance (optional, for manual mappings)
        """
        self.loader = loader
        self.db = db

        # Cache for resolved names
        self.cache = {}

        # Leaguepedia team data
        self.leaguepedia_teams = {}
        self.team_redirects = {}

        # Manual mappings
        self.manual_mappings = {}

        # Unknown teams log
        self.unknown_teams = set()

        # Load data
        if loader:
            self._load_leaguepedia_teams()
        if db:
            self._load_manual_mappings()

    def _load_leaguepedia_teams(self):
        """Load team data from Leaguepedia"""
        print("Loading Leaguepedia Teams data...")

        try:
            teams = self.loader._query_cargo(
                tables="Teams",
                fields="Name,OverviewPage,RenamedTo,IsDisbanded,Region",
                limit=5000
            )

            for team in teams:
                name = team.get('Name', '')
                overview = team.get('OverviewPage', '')
                renamed_to = team.get('RenamedTo', '')

                if not name:
                    continue

                # Use OverviewPage as canonical ID (e.g., "T1" instead of "SK Telecom T1")
                canonical = overview if overview else name

                self.leaguepedia_teams[name] = canonical

                # Handle renames
                if renamed_to:
                    self.team_redirects[name] = renamed_to

            print(f"  Loaded {len(self.leaguepedia_teams)} teams from Leaguepedia")

        except Exception as e:
            print(f"  Warning: Could not load Leaguepedia teams: {e}")

    def _load_manual_mappings(self):
        """Load manual team mappings from database"""
        try:
            # TODO: Implement database loading
            # For now, load from JSON file if exists
            mappings_file = Path(__file__).parent.parent / "data" / "team_mappings.json"

            if mappings_file.exists():
                with open(mappings_file, 'r') as f:
                    self.manual_mappings = json.load(f)
                print(f"  Loaded {len(self.manual_mappings)} manual mappings")
        except Exception as e:
            print(f"  Warning: Could not load manual mappings: {e}")

    def resolve(self, team_name: str, game_date: Optional[str] = None) -> str:
        """
        Resolve team name to canonical identifier

        Args:
            team_name: Raw team name from game data
            game_date: Date of the game (for handling renames over time)

        Returns:
            Canonical team identifier
        """
        if not team_name:
            return ""

        # Check cache
        if team_name in self.cache:
            return self.cache[team_name]

        # 1. Try Leaguepedia lookup
        canonical = self._leaguepedia_lookup(team_name)
        if canonical:
            self.cache[team_name] = canonical
            return canonical

        # 2. Try manual mapping
        canonical = self._manual_lookup(team_name)
        if canonical:
            self.cache[team_name] = canonical
            return canonical

        # 3. Try normalization + fuzzy matching
        canonical = self._fuzzy_match(team_name)
        if canonical:
            self.cache[team_name] = canonical
            # Save for future (could auto-add to manual mappings)
            return canonical

        # 4. Fallback: use as-is, but log as unknown
        self.unknown_teams.add(team_name)
        normalized = self._normalize_name(team_name)
        self.cache[team_name] = normalized
        return normalized

    def _leaguepedia_lookup(self, team_name: str) -> Optional[str]:
        """Lookup team in Leaguepedia data"""
        # Direct match
        if team_name in self.leaguepedia_teams:
            canonical = self.leaguepedia_teams[team_name]

            # Follow rename chain
            while canonical in self.team_redirects:
                canonical = self.team_redirects[canonical]

            return canonical

        return None

    def _manual_lookup(self, team_name: str) -> Optional[str]:
        """Lookup team in manual mappings"""
        return self.manual_mappings.get(team_name)

    def _fuzzy_match(self, team_name: str) -> Optional[str]:
        """
        Try fuzzy matching against known teams
        """
        normalized = self._normalize_name(team_name)

        # Get all known team names
        all_teams = list(self.leaguepedia_teams.keys()) + list(self.manual_mappings.keys())

        # Normalize all known teams
        normalized_teams = {self._normalize_name(t): t for t in all_teams}

        # Try exact match on normalized names
        if normalized in normalized_teams:
            original = normalized_teams[normalized]
            return self.leaguepedia_teams.get(original) or self.manual_mappings.get(original)

        # Try fuzzy matching
        matches = get_close_matches(normalized, normalized_teams.keys(), n=1, cutoff=0.85)
        if matches:
            original = normalized_teams[matches[0]]
            return self.leaguepedia_teams.get(original) or self.manual_mappings.get(original)

        return None

    def _normalize_name(self, name: str) -> str:
        """
        Normalize team name for comparison

        - Remove whitespace
        - Lowercase
        - Remove sponsor suffixes (e.g., "TSM FTX" → "TSM")
        - Remove special characters
        """
        # Remove leading/trailing whitespace
        name = name.strip()

        # Known sponsor patterns to remove
        sponsor_patterns = [
            r'\s+FTX$',
            r'\s+Gaming$',
            r'\s+Esports?$',
            r'\s+eSports?$',
            r'\s+e-Sports?$',
        ]

        for pattern in sponsor_patterns:
            name = re.sub(pattern, '', name, flags=re.IGNORECASE)

        # Remove special characters except letters, numbers, spaces
        name = re.sub(r'[^\w\s]', '', name)

        # Collapse multiple spaces
        name = re.sub(r'\s+', ' ', name)

        # Lowercase for comparison
        return name.lower().strip()

    def get_unknown_teams(self) -> List[str]:
        """Get list of teams that couldn't be resolved"""
        return sorted(list(self.unknown_teams))

    def add_manual_mapping(self, team_name: str, canonical: str):
        """
        Add a manual team mapping

        Args:
            team_name: Original team name
            canonical: Canonical team identifier
        """
        self.manual_mappings[team_name] = canonical
        self.cache[team_name] = canonical

    def save_unknown_teams(self, filepath: str):
        """Save unknown teams to file for manual review"""
        with open(filepath, 'w') as f:
            f.write("# Unknown Teams - Need Manual Mapping\n")
            f.write("# Add these to data/team_mappings.json\n\n")
            for team in sorted(self.unknown_teams):
                f.write(f"{team}\n")

        print(f"Saved {len(self.unknown_teams)} unknown teams to {filepath}")


# Convenience function
def create_team_resolver(loader=None, db=None) -> TeamResolver:
    """Create and initialize a TeamResolver instance"""
    return TeamResolver(loader=loader, db=db)
