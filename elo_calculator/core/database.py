"""
SQLite Database Manager for LOL ELO System
Manages storage of matches, teams, players, and tournaments
"""

import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import json


class DatabaseManager:
    """
    Manages SQLite database for ELO system
    Handles schema creation, data insertion, and deduplication
    """

    def __init__(self, db_path: str = "db/elo_system.db"):
        """
        Initialize database manager

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = None
        self._connect()
        self._initialize_schema()

    def _connect(self):
        """Establish database connection"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # Access columns by name
        # Enable foreign keys
        self.conn.execute("PRAGMA foreign_keys = ON")

    def _initialize_schema(self):
        """Create database schema if not exists"""
        cursor = self.conn.cursor()

        # Teams table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS teams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                region TEXT,
                current_elo REAL DEFAULT 1500.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Tournaments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tournaments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                region TEXT,
                year INTEGER,
                split TEXT,
                tier INTEGER DEFAULT 1,
                tournament_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Matches table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                external_id TEXT UNIQUE,
                date TIMESTAMP NOT NULL,
                team1_id INTEGER NOT NULL,
                team2_id INTEGER NOT NULL,
                team1_score INTEGER NOT NULL,
                team2_score INTEGER NOT NULL,
                winner_id INTEGER NOT NULL,
                tournament_id INTEGER,
                stage TEXT,
                patch TEXT,
                bo_format TEXT,
                game_length TEXT,
                source TEXT DEFAULT 'leaguepedia',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (team1_id) REFERENCES teams(id),
                FOREIGN KEY (team2_id) REFERENCES teams(id),
                FOREIGN KEY (winner_id) REFERENCES teams(id),
                FOREIGN KEY (tournament_id) REFERENCES tournaments(id)
            )
        """)

        # Players table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                current_elo REAL DEFAULT 1500.0,
                role TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Match Players (which players played in which match)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS match_players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER NOT NULL,
                player_id INTEGER NOT NULL,
                team_id INTEGER NOT NULL,
                role TEXT,
                champion TEXT,
                kills INTEGER,
                deaths INTEGER,
                assists INTEGER,
                gold INTEGER,
                cs INTEGER,
                damage_to_champions INTEGER,
                vision_score INTEGER,
                items TEXT,
                won BOOLEAN,
                FOREIGN KEY (match_id) REFERENCES matches(id),
                FOREIGN KEY (player_id) REFERENCES players(id),
                FOREIGN KEY (team_id) REFERENCES teams(id),
                UNIQUE(match_id, player_id)
            )
        """)

        # ELO Configurations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS elo_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                variant TEXT NOT NULL,
                k_factor REAL NOT NULL,
                use_scale_factors BOOLEAN DEFAULT 0,
                scale_factors TEXT,
                parameters TEXT,
                config_hash TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ELO Ratings table (snapshot after each match)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS elo_ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                config_id INTEGER NOT NULL,
                team_id INTEGER NOT NULL,
                match_id INTEGER NOT NULL,
                elo_value REAL NOT NULL,
                matches_played INTEGER NOT NULL,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                date TIMESTAMP NOT NULL,
                FOREIGN KEY (config_id) REFERENCES elo_configs(id),
                FOREIGN KEY (team_id) REFERENCES teams(id),
                FOREIGN KEY (match_id) REFERENCES matches(id),
                UNIQUE(config_id, team_id, match_id)
            )
        """)

        # Indices for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_matches_date ON matches(date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_matches_tournament ON matches(tournament_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_matches_teams ON matches(team1_id, team2_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_matches_external_id ON matches(external_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_elo_ratings_config ON elo_ratings(config_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_elo_ratings_team ON elo_ratings(team_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_elo_ratings_date ON elo_ratings(date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_elo_configs_hash ON elo_configs(config_hash)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_match_players_match ON match_players(match_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_match_players_player ON match_players(player_id)")

        self.conn.commit()

    def get_or_create_team(self, name: str, region: str = None) -> int:
        """
        Get team ID or create new team

        Args:
            name: Team name
            region: Team region (EU, CN, KR, NA, etc.)

        Returns:
            Team ID
        """
        cursor = self.conn.cursor()

        # Try to find existing team
        cursor.execute("SELECT id FROM teams WHERE name = ?", (name,))
        result = cursor.fetchone()

        if result:
            return result[0]

        # Create new team
        cursor.execute(
            "INSERT INTO teams (name, region) VALUES (?, ?)",
            (name, region)
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_or_create_tournament(self, name: str, region: str = None,
                                  year: int = None, split: str = None,
                                  tier: int = 1, tournament_type: str = None) -> int:
        """
        Get tournament ID or create new tournament

        Args:
            name: Tournament name (e.g. "LEC 2024 Summer")
            region: Region (EU, CN, KR, NA, International)
            year: Year
            split: Split (Spring, Summer, etc.)
            tier: Tier (1 for top leagues)
            tournament_type: Type (Regular Season, Playoffs, International)

        Returns:
            Tournament ID
        """
        cursor = self.conn.cursor()

        # Try to find existing tournament
        cursor.execute("SELECT id FROM tournaments WHERE name = ?", (name,))
        result = cursor.fetchone()

        if result:
            return result[0]

        # Create new tournament
        cursor.execute(
            """INSERT INTO tournaments (name, region, year, split, tier, tournament_type)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (name, region, year, split, tier, tournament_type)
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_or_create_player(self, name: str, role: str = None) -> int:
        """
        Get player ID or create new player

        Args:
            name: Player name
            role: Role (Top, Jungle, Mid, ADC, Support)

        Returns:
            Player ID
        """
        cursor = self.conn.cursor()

        # Try to find existing player
        cursor.execute("SELECT id FROM players WHERE name = ?", (name,))
        result = cursor.fetchone()

        if result:
            return result[0]

        # Create new player
        cursor.execute(
            "INSERT INTO players (name, role) VALUES (?, ?)",
            (name, role)
        )
        self.conn.commit()
        return cursor.lastrowid

    def match_exists(self, external_id: str = None,
                     team1: str = None, team2: str = None,
                     date: datetime = None) -> bool:
        """
        Check if match already exists in database

        Args:
            external_id: External match ID (from Leaguepedia)
            team1: Team 1 name
            team2: Team 2 name
            date: Match date

        Returns:
            True if match exists
        """
        cursor = self.conn.cursor()

        # Check by external ID (most reliable for Leaguepedia data)
        # If external_id is provided, ONLY use this for duplicate check
        if external_id:
            cursor.execute(
                "SELECT id FROM matches WHERE external_id = ?",
                (external_id,)
            )
            return cursor.fetchone() is not None

        # Fallback: Check by teams + date (for Google Sheets data without external_id)
        if team1 and team2 and date:
            cursor.execute("""
                SELECT m.id FROM matches m
                JOIN teams t1 ON m.team1_id = t1.id
                JOIN teams t2 ON m.team2_id = t2.id
                WHERE (t1.name = ? AND t2.name = ? OR t1.name = ? AND t2.name = ?)
                  AND DATE(m.date) = DATE(?)
            """, (team1, team2, team2, team1, date))
            return cursor.fetchone() is not None

        return False

    def insert_match(self,
                     team1_name: str,
                     team2_name: str,
                     team1_score: int,
                     team2_score: int,
                     date: datetime,
                     tournament_name: str = None,
                     stage: str = None,
                     patch: str = None,
                     bo_format: str = None,
                     external_id: str = None,
                     source: str = "leaguepedia",
                     region: str = None,
                     tournament_type: str = None) -> Optional[int]:
        """
        Insert match into database

        Args:
            team1_name: Team 1 name
            team2_name: Team 2 name
            team1_score: Team 1 score
            team2_score: Team 2 score
            date: Match date
            tournament_name: Tournament name
            stage: Stage (Regular Season, Playoffs, etc.)
            patch: Patch version
            bo_format: Best-of format (Bo1, Bo3, Bo5) - auto-detected if not provided
            external_id: External match ID
            source: Data source (leaguepedia, google_sheets)
            region: Region
            tournament_type: Tournament type (Regular Season, Playoffs, International)

        Returns:
            Match ID or None if duplicate
        """
        # Convert pandas Timestamp to Python datetime if needed
        if hasattr(date, 'to_pydatetime'):
            date = date.to_pydatetime()

        # Check for duplicates
        if self.match_exists(external_id, team1_name, team2_name, date):
            return None

        cursor = self.conn.cursor()

        # Get or create teams
        team1_id = self.get_or_create_team(team1_name, region)
        team2_id = self.get_or_create_team(team2_name, region)

        # Determine winner
        winner_id = team1_id if team1_score > team2_score else team2_id

        # Get or create tournament
        tournament_id = None
        if tournament_name:
            tournament_id = self.get_or_create_tournament(
                tournament_name,
                region=region,
                tournament_type=tournament_type
            )

        # Determine Bo format if not provided
        if bo_format is None:
            max_score = max(team1_score, team2_score)
            if max_score == 1:
                bo_format = "Bo1"
            elif max_score <= 2:
                bo_format = "Bo3"
            else:
                bo_format = "Bo5"

        # Insert match
        cursor.execute("""
            INSERT INTO matches
            (external_id, date, team1_id, team2_id, team1_score, team2_score,
             winner_id, tournament_id, stage, patch, bo_format, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (external_id, date, team1_id, team2_id, team1_score, team2_score,
              winner_id, tournament_id, stage, patch, bo_format, source))

        self.conn.commit()
        return cursor.lastrowid

    def insert_match_player(self, match_id: int, player_name: str,
                           team_name: str, role: str = None,
                           champion: str = None, kills: int = None,
                           deaths: int = None, assists: int = None,
                           gold: int = None, cs: int = None,
                           damage_to_champions: int = None,
                           vision_score: int = None,
                           items: List[str] = None,
                           won: bool = None) -> Optional[int]:
        """
        Insert player participation in match

        Args:
            match_id: Match ID
            player_name: Player name
            team_name: Team name
            role: Player role
            champion: Champion played
            kills, deaths, assists: KDA
            gold: Gold earned
            cs: Creep score
            damage_to_champions: Damage dealt
            vision_score: Vision score
            items: List of items
            won: Whether player won

        Returns:
            Record ID or None if duplicate
        """
        cursor = self.conn.cursor()

        # Get player and team IDs
        player_id = self.get_or_create_player(player_name, role)

        cursor.execute("SELECT id FROM teams WHERE name = ?", (team_name,))
        team_result = cursor.fetchone()
        if not team_result:
            return None
        team_id = team_result[0]

        # Check if already exists
        cursor.execute(
            "SELECT id FROM match_players WHERE match_id = ? AND player_id = ?",
            (match_id, player_id)
        )
        if cursor.fetchone():
            return None

        # Convert items list to JSON string
        items_json = json.dumps(items) if items else None

        # Insert
        cursor.execute("""
            INSERT INTO match_players
            (match_id, player_id, team_id, role, champion, kills, deaths, assists,
             gold, cs, damage_to_champions, vision_score, items, won)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (match_id, player_id, team_id, role, champion, kills, deaths, assists,
              gold, cs, damage_to_champions, vision_score, items_json, won))

        self.conn.commit()
        return cursor.lastrowid

    def get_all_matches(self, limit: int = None) -> List[Dict]:
        """
        Get all matches from database

        Args:
            limit: Optional limit on number of matches

        Returns:
            List of match dictionaries
        """
        cursor = self.conn.cursor()

        query = """
            SELECT
                m.id, m.external_id, m.date, m.team1_score, m.team2_score,
                t1.name as team1_name, t2.name as team2_name,
                tw.name as winner_name,
                tour.name as tournament_name,
                m.stage, m.patch, m.bo_format, m.source
            FROM matches m
            JOIN teams t1 ON m.team1_id = t1.id
            JOIN teams t2 ON m.team2_id = t2.id
            JOIN teams tw ON m.winner_id = tw.id
            LEFT JOIN tournaments tour ON m.tournament_id = tour.id
            ORDER BY m.date
        """

        if limit:
            query += f" LIMIT {limit}"

        cursor.execute(query)

        matches = []
        for row in cursor.fetchall():
            matches.append({
                'id': row[0],
                'external_id': row[1],
                'date': row[2],
                'team1_name': row[5],
                'team2_name': row[6],
                'team1_score': row[3],
                'team2_score': row[4],
                'winner': row[7],
                'tournament': row[8],
                'stage': row[9],
                'patch': row[10],
                'bo_format': row[11],
                'source': row[12]
            })

        return matches

    def get_stats(self) -> Dict:
        """
        Get database statistics

        Returns:
            Dictionary with counts
        """
        cursor = self.conn.cursor()

        stats = {}

        cursor.execute("SELECT COUNT(*) FROM matches")
        stats['total_matches'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM teams")
        stats['total_teams'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM players")
        stats['total_players'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tournaments")
        stats['total_tournaments'] = cursor.fetchone()[0]

        cursor.execute("SELECT MIN(date), MAX(date) FROM matches")
        result = cursor.fetchone()
        stats['date_range'] = (result[0], result[1])

        cursor.execute("SELECT source, COUNT(*) FROM matches GROUP BY source")
        stats['by_source'] = {row[0]: row[1] for row in cursor.fetchall()}

        return stats

    def get_matches_by_tournament(self, tournament_name: str) -> List[Dict]:
        """
        Get all matches for a specific tournament

        Args:
            tournament_name: Tournament name

        Returns:
            List of match dictionaries with id and external_id
        """
        cursor = self.conn.cursor()

        query = """
            SELECT
                m.id, m.external_id, m.date,
                t1.name as team1_name, t2.name as team2_name,
                m.team1_score, m.team2_score
            FROM matches m
            JOIN teams t1 ON m.team1_id = t1.id
            JOIN teams t2 ON m.team2_id = t2.id
            LEFT JOIN tournaments tour ON m.tournament_id = tour.id
            WHERE tour.name = ?
            ORDER BY m.date
        """

        cursor.execute(query, (tournament_name,))

        matches = []
        for row in cursor.fetchall():
            matches.append({
                'id': row[0],
                'external_id': row[1],
                'date': row[2],
                'team1_name': row[3],
                'team2_name': row[4],
                'team1_score': row[5],
                'team2_score': row[6]
            })

        return matches

    def get_all_tournament_names(self) -> List[str]:
        """
        Get all unique tournament names from database

        Returns:
            List of tournament names
        """
        cursor = self.conn.cursor()

        query = """
            SELECT DISTINCT name
            FROM tournaments
            ORDER BY name
        """

        cursor.execute(query)

        return [row[0] for row in cursor.fetchall()]

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


if __name__ == "__main__":
    # Test database creation
    print("Creating database...")

    db = DatabaseManager()

    print("\n✓ Database created successfully!")
    print(f"✓ Location: {db.db_path.absolute()}")

    # Test inserting a match
    print("\nTesting match insertion...")
    match_id = db.insert_match(
        team1_name="T1",
        team2_name="Gen.G",
        team1_score=3,
        team2_score=2,
        date=datetime.now(),
        tournament_name="LCK 2024 Summer Playoffs",
        stage="Finals",
        patch="14.15",
        region="KR",
        source="test"
    )

    if match_id:
        print(f"✓ Match inserted with ID: {match_id}")

        # Test player insertion
        db.insert_match_player(
            match_id=match_id,
            player_name="Faker",
            team_name="T1",
            role="Mid",
            champion="Azir",
            kills=5,
            deaths=1,
            assists=8,
            won=True
        )
        print("✓ Player data inserted")

    # Get stats
    stats = db.get_stats()
    print(f"\n📊 Database Stats:")
    print(f"  Matches: {stats['total_matches']}")
    print(f"  Teams: {stats['total_teams']}")
    print(f"  Players: {stats['total_players']}")
    print(f"  Tournaments: {stats['total_tournaments']}")

    db.close()
