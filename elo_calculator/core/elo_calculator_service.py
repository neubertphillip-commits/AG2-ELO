"""
ELO Calculator Service
Calculates and caches ELO ratings in database
Provides instant access to pre-calculated ratings
"""

import hashlib
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from core.database import DatabaseManager


class EloCalculatorService:
    """
    Service for calculating and caching ELO ratings

    Architecture:
    - Matches table: Source of truth (immutable)
    - ELO configs table: Which calculation method was used
    - ELO ratings table: Calculated results (cached)

    Usage:
        service = EloCalculatorService()
        ratings = service.calculate_or_load_elos(
            variant='tournament_context',
            k_factor=24,
            use_scale_factors=True
        )
    """

    def __init__(self, db: DatabaseManager = None):
        """Initialize service"""
        self.db = db or DatabaseManager()
        self._close_db_on_exit = db is None

    def calculate_or_load_elos(self,
                                variant: str = 'tournament_context',
                                k_factor: float = 24,
                                use_scale_factors: bool = True,
                                use_regional_offsets: bool = False,
                                scale_factors: Dict = None,
                                force_recalculate: bool = False) -> Tuple[int, Dict]:
        """
        Calculate or load ELO ratings

        Args:
            variant: ELO variant ('base', 'scale_factor', 'dynamic_offset', 'tournament_context')
            k_factor: K-factor
            use_scale_factors: Whether to use scale factors
            use_regional_offsets: Whether to apply regional offsets to the base variant
            scale_factors: Scale factor configuration
            force_recalculate: If True, recalculate even if cached

        Returns:
            Tuple of (config_id, ratings_dict)
            ratings_dict: {team_name: {'elo': float, 'matches': int, 'wins': int, 'losses': int}}
        """
        # Default scale factors
        if scale_factors is None:
            scale_factors = {
                '1-0': 1.00,
                '2-0': 1.00, '2-1': 0.50,
                '3-0': 1.00, '3-1': 0.90, '3-2': 0.80,
            }

        # Create config
        config = {
            'variant': variant,
            'k_factor': k_factor,
            'use_scale_factors': use_scale_factors,
            'use_regional_offsets': use_regional_offsets,
            'scale_factors': scale_factors if use_scale_factors else None
        }

        # Generate config hash
        config_hash = self._hash_config(config)

        # Check if already calculated
        config_id = self._get_config_id(config_hash)

        if config_id and not force_recalculate:
            print(f"[CACHE] Loading ELOs for {variant} K={k_factor}")
            return config_id, self._load_ratings_from_db(config_id)

        # Need to calculate
        print(f"[CALC] Calculating ELOs for {variant} K={k_factor}")

        # Save or get config
        if not config_id:
            config_id = self._save_config(config, config_hash)
        else:
            # Clear old ratings for this config
            self._clear_ratings_for_config(config_id)

        # Calculate ELOs
        ratings = self._calculate_elos(config)

        # Save to database
        self._save_ratings_to_db(config_id, ratings)

        return config_id, ratings

    def _hash_config(self, config: Dict) -> str:
        """Generate hash for config"""
        config_str = json.dumps(config, sort_keys=True)
        return hashlib.md5(config_str.encode()).hexdigest()

    def _get_config_id(self, config_hash: str) -> Optional[int]:
        """Get config ID if exists"""
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT id FROM elo_configs WHERE config_hash = ?", (config_hash,))
        result = cursor.fetchone()
        return result[0] if result else None

    def _save_config(self, config: Dict, config_hash: str) -> int:
        """Save config to database"""
        cursor = self.db.conn.cursor()

        name = f"{config['variant'].replace('_', ' ').title()} (K={config['k_factor']})"

        cursor.execute("""
            INSERT INTO elo_configs
            (name, variant, k_factor, use_scale_factors, scale_factors, parameters, config_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            name,
            config['variant'],
            config['k_factor'],
            config['use_scale_factors'],
            json.dumps(config['scale_factors']) if config['scale_factors'] else None,
            json.dumps(config),
            config_hash
        ))

        self.db.conn.commit()
        return cursor.lastrowid

    def _clear_ratings_for_config(self, config_id: int):
        """Clear all ratings for a config"""
        cursor = self.db.conn.cursor()
        cursor.execute("DELETE FROM elo_ratings WHERE config_id = ?", (config_id,))
        self.db.conn.commit()

    def _calculate_elos(self, config: Dict) -> Dict:
        """Calculate ELO ratings for all matches"""
        # Import ELO variant
        variant = config['variant']
        use_regional_offsets = config.get('use_regional_offsets', False)

        # Choose base variant
        if variant == 'base':
            if use_regional_offsets:
                # Base + Regional Offsets = DynamicOffsetElo without scale factors
                from variants.with_dynamic_offsets import DynamicOffsetElo
                elo = DynamicOffsetElo(
                    k_factor=config['k_factor'],
                    use_scale_factors=False,
                    scale_factors=None
                )
            else:
                from variants.base_elo import BaseElo
                elo = BaseElo(k_factor=config['k_factor'])
        elif variant == 'scale_factor':
            if use_regional_offsets:
                # Scale Factor + Regional Offsets = DynamicOffsetElo (already uses scale factors)
                from variants.with_dynamic_offsets import DynamicOffsetElo
                elo = DynamicOffsetElo(
                    k_factor=config['k_factor'],
                    use_scale_factors=config['use_scale_factors'],
                    scale_factors=config['scale_factors']
                )
            else:
                from variants.with_scale_factor import ScaleFactorElo
                elo = ScaleFactorElo(
                    k_factor=config['k_factor'],
                    use_scale_factors=config['use_scale_factors'],
                    scale_factors=config['scale_factors']
                )
        elif variant == 'dynamic_offset':
            # Always includes regional offsets
            from variants.with_dynamic_offsets import DynamicOffsetElo
            elo = DynamicOffsetElo(
                k_factor=config['k_factor'],
                use_scale_factors=config['use_scale_factors'],
                scale_factors=config['scale_factors']
            )
        elif variant == 'tournament_context':
            # Always includes regional offsets (extends DynamicOffsetElo)
            from variants.with_tournament_context import TournamentContextElo
            elo = TournamentContextElo(
                k_factor=config['k_factor'],
                use_scale_factors=config['use_scale_factors'],
                scale_factors=config['scale_factors']
            )
        else:
            raise ValueError(f"Unknown variant: {variant}")

        # Load matches chronologically
        matches = self.db.get_all_matches(limit=None)

        # Track ratings after each match
        ratings_history = []
        team_stats = {}

        for match in matches:
            team1 = match['team1_name']
            team2 = match['team2_name']

            # Initialize teams if needed
            if team1 not in team_stats:
                team_stats[team1] = {'matches': 0, 'wins': 0, 'losses': 0}
            if team2 not in team_stats:
                team_stats[team2] = {'matches': 0, 'wins': 0, 'losses': 0}

            # Update ratings
            if variant == 'tournament_context':
                elo.update_ratings(
                    team1, team2,
                    match['team1_score'], match['team2_score'],
                    tournament=match.get('tournament'),
                    stage=match.get('stage')
                )
            else:
                elo.update_ratings(
                    team1, team2,
                    match['team1_score'], match['team2_score']
                )

            # Update stats
            team_stats[team1]['matches'] += 1
            team_stats[team2]['matches'] += 1

            if match['winner'] == team1:
                team_stats[team1]['wins'] += 1
                team_stats[team2]['losses'] += 1
            else:
                team_stats[team2]['wins'] += 1
                team_stats[team1]['losses'] += 1

            # Save snapshot
            ratings_history.append({
                'match_id': match['id'],
                'date': match['date'],
                'team1': team1,
                'team2': team2,
                'elo1': elo.get_rating(team1),
                'elo2': elo.get_rating(team2),
                'matches1': team_stats[team1]['matches'],
                'matches2': team_stats[team2]['matches'],
                'wins1': team_stats[team1]['wins'],
                'wins2': team_stats[team2]['wins'],
                'losses1': team_stats[team1]['losses'],
                'losses2': team_stats[team2]['losses'],
            })

        # Build final ratings dict (latest ELO for each team)
        final_ratings = {}

        # Get regional offsets if using any variant with offsets
        # Note: dynamic_offset and tournament_context always use offsets
        # base and scale_factor can optionally use offsets
        using_offsets = (variant in ['dynamic_offset', 'tournament_context']) or use_regional_offsets

        regional_offsets = {}
        team_regions = {}
        if using_offsets and hasattr(elo, 'calculator'):
            # Get offsets from the calculator
            regional_offsets = dict(elo.calculator.offsets)
            # Map teams to regions
            from core.region_mapper import RegionMapper
            mapper = RegionMapper()
            for team in team_stats.keys():
                team_regions[team] = mapper.get_region(team, detailed=False)

        for team, stats in team_stats.items():
            base_elo = elo.get_rating(team)

            # Apply regional offset if using offsets
            if using_offsets and team in team_regions:
                region = team_regions[team]
                offset = regional_offsets.get(region, 0.0)
                final_elo = base_elo + offset
            else:
                final_elo = base_elo

            final_ratings[team] = {
                'elo': final_elo,
                'base_elo': base_elo if using_offsets else None,
                'regional_offset': regional_offsets.get(team_regions.get(team), 0.0) if using_offsets else None,
                'region': team_regions.get(team) if using_offsets else None,
                'matches': stats['matches'],
                'wins': stats['wins'],
                'losses': stats['losses']
            }

        # Store history for database save
        final_ratings['_history'] = ratings_history

        return final_ratings

    def _save_ratings_to_db(self, config_id: int, ratings: Dict):
        """Save ratings to database"""
        cursor = self.db.conn.cursor()

        history = ratings.pop('_history')

        # Batch insert for performance
        for snapshot in history:
            # Team 1
            team1_id = self._get_team_id(snapshot['team1'])
            if team1_id:
                cursor.execute("""
                    INSERT OR REPLACE INTO elo_ratings
                    (config_id, team_id, match_id, elo_value, matches_played, wins, losses, date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    config_id,
                    team1_id,
                    snapshot['match_id'],
                    snapshot['elo1'],
                    snapshot['matches1'],
                    snapshot['wins1'],
                    snapshot['losses1'],
                    snapshot['date']
                ))

            # Team 2
            team2_id = self._get_team_id(snapshot['team2'])
            if team2_id:
                cursor.execute("""
                    INSERT OR REPLACE INTO elo_ratings
                    (config_id, team_id, match_id, elo_value, matches_played, wins, losses, date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    config_id,
                    team2_id,
                    snapshot['match_id'],
                    snapshot['elo2'],
                    snapshot['matches2'],
                    snapshot['wins2'],
                    snapshot['losses2'],
                    snapshot['date']
                ))

        self.db.conn.commit()
        print(f"  [OK] Saved {len(history)} match snapshots to database")

    def _load_ratings_from_db(self, config_id: int) -> Dict:
        """Load latest ratings from database"""
        cursor = self.db.conn.cursor()

        # Get latest rating for each team
        cursor.execute("""
            SELECT
                t.name,
                r.elo_value,
                r.matches_played,
                r.wins,
                r.losses
            FROM elo_ratings r
            JOIN teams t ON r.team_id = t.id
            WHERE r.config_id = ?
            AND r.id IN (
                SELECT MAX(id)
                FROM elo_ratings
                WHERE config_id = ?
                GROUP BY team_id
            )
            ORDER BY r.elo_value DESC
        """, (config_id, config_id))

        ratings = {}
        for row in cursor.fetchall():
            ratings[row[0]] = {
                'elo': row[1],
                'matches': row[2],
                'wins': row[3],
                'losses': row[4]
            }

        return ratings

    def _get_team_id(self, team_name: str) -> Optional[int]:
        """Get team ID by name"""
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT id FROM teams WHERE name = ?", (team_name,))
        result = cursor.fetchone()
        return result[0] if result else None

    def get_available_configs(self) -> List[Dict]:
        """Get list of available ELO configs"""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT
                id, name, variant, k_factor, use_scale_factors,
                created_at,
                (SELECT COUNT(*) FROM elo_ratings WHERE config_id = elo_configs.id) as rating_count
            FROM elo_configs
            ORDER BY created_at DESC
        """)

        configs = []
        for row in cursor.fetchall():
            configs.append({
                'id': row[0],
                'name': row[1],
                'variant': row[2],
                'k_factor': row[3],
                'use_scale_factors': bool(row[4]),
                'created_at': row[5],
                'rating_count': row[6]
            })

        return configs

    def delete_config(self, config_id: int):
        """Delete a config and all its ratings"""
        cursor = self.db.conn.cursor()
        cursor.execute("DELETE FROM elo_ratings WHERE config_id = ?", (config_id,))
        cursor.execute("DELETE FROM elo_configs WHERE id = ?", (config_id,))
        self.db.conn.commit()

    def close(self):
        """Close database connection"""
        if self._close_db_on_exit and self.db:
            self.db.close()

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


if __name__ == "__main__":
    # Test the service
    print("="*70)
    print("ELO CALCULATOR SERVICE TEST")
    print("="*70)

    with EloCalculatorService() as service:
        # Calculate Tournament Context ELO
        print("\n1. Calculating Tournament Context ELO...")
        config_id, ratings = service.calculate_or_load_elos(
            variant='tournament_context',
            k_factor=24,
            use_scale_factors=True
        )

        print(f"\nConfig ID: {config_id}")
        print(f"Teams: {len(ratings)}")

        # Show top 10
        print("\nTop 10 Teams:")
        sorted_teams = sorted(ratings.items(), key=lambda x: x[1]['elo'], reverse=True)
        for i, (team, stats) in enumerate(sorted_teams[:10], 1):
            print(f"  {i}. {team}: {stats['elo']:.1f} ({stats['wins']}-{stats['losses']})")

        # Load again (should be cached)
        print("\n2. Loading from cache...")
        config_id2, ratings2 = service.calculate_or_load_elos(
            variant='tournament_context',
            k_factor=24,
            use_scale_factors=True
        )

        print(f"Same config? {config_id == config_id2}")

        # Show available configs
        print("\n3. Available configs:")
        configs = service.get_available_configs()
        for config in configs:
            print(f"  - {config['name']} (ID: {config['id']}, Ratings: {config['rating_count']})")
