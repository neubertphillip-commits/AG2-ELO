#!/usr/bin/env python3
"""
Bulk Team Name Mapping Generator
Für große Datenmengen (13,000+ matches)

Features:
- Automatische Erkennung von häufigen Team-Namen-Variationen
- Pattern-basierte Gruppierung (z.B. "T1" vs "SK Telecom T1")
- Batch-Processing für schnelle Mapping-Erstellung
- Export/Import von Mappings
"""

import json
import re
import sys
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict, Counter
from difflib import SequenceMatcher
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class BulkMappingGenerator:
    """
    Generiert automatisch Team-Mappings für große Datenmengen
    """

    def __init__(self, db_path: str = "db/elo_system.db"):
        self.db_path = Path(db_path)

        # Common patterns
        self.suffix_patterns = [
            r'\s+LoL$',
            r'\s+Esports$',
            r'\s+E-Sports$',
            r'\s+Gaming$',
            r'\s+e\.V\.$',
            r'\s+GmbH$',
            r'\s+Inc\.$',
            r'\s+Team$',
        ]

        self.known_rebrands = {
            # Old name -> New name
            'SK Telecom T1': 'T1',
            'Samsung Galaxy': 'Gen.G',
            'KSV': 'Gen.G',
            'Longzhu Gaming': 'KingZone DragonX',
            'KingZone DragonX': 'DragonX',
            'Moscow Five': 'Gambit Gaming',
            'Team SoloMid': 'TSM',
            'Counter Logic Gaming': 'CLG',
            'Evil Geniuses': 'EG',
            'Invictus Gaming': 'iG',
            'FunPlus Phoenix': 'FPX',
            'Suning': 'Weibo Gaming',
            'Snake Esports': 'LNG Esports',
        }

    def get_all_teams_with_frequency(self) -> List[Tuple[str, int]]:
        """
        Hole alle Teams mit ihrer Match-Häufigkeit

        Returns:
            List of (team_name, match_count) sorted by frequency
        """
        if not self.db_path.exists():
            print(f"⚠️  Database not found: {self.db_path}")
            return []

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT t.name,
                   COUNT(*) as match_count
            FROM teams t
            LEFT JOIN matches m ON (m.team1_id = t.id OR m.team2_id = t.id)
            GROUP BY t.id, t.name
            ORDER BY match_count DESC
        """)

        teams = cursor.fetchall()
        conn.close()

        return teams

    def normalize_team_name(self, name: str) -> str:
        """
        Normalisiere Team-Namen für Vergleich

        Args:
            name: Team name

        Returns:
            Normalized name
        """
        normalized = name

        # Remove common suffixes
        for pattern in self.suffix_patterns:
            normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)

        # Normalize spaces
        normalized = ' '.join(normalized.split())

        # Remove special characters but keep alphanumeric and spaces
        normalized = re.sub(r'[^\w\s-]', '', normalized)

        return normalized.strip()

    def find_name_clusters(self, teams: List[Tuple[str, int]]) -> Dict[str, List[Tuple[str, int]]]:
        """
        Gruppiere ähnliche Team-Namen

        Args:
            teams: List of (team_name, match_count)

        Returns:
            Dict of normalized_name -> list of (original_name, match_count)
        """
        clusters = defaultdict(list)

        for team_name, match_count in teams:
            normalized = self.normalize_team_name(team_name)

            # Map to cluster
            clusters[normalized].append((team_name, match_count))

        return dict(clusters)

    def auto_generate_mappings(self, min_matches: int = 10) -> List[Dict]:
        """
        Automatische Generierung von Mappings

        Args:
            min_matches: Minimum matches for a team to be included

        Returns:
            List of mapping entries
        """
        print("\n🔍 Analysiere Team-Namen aus Datenbank...")

        teams = self.get_all_teams_with_frequency()
        print(f"   Gefunden: {len(teams)} unique teams")

        # Filter by minimum matches
        teams = [(name, count) for name, count in teams if count >= min_matches]
        print(f"   Nach Filterung (>={min_matches} matches): {len(teams)} teams")

        # Cluster similar names
        print("\n📦 Gruppiere ähnliche Namen...")
        clusters = self.find_name_clusters(teams)
        print(f"   {len(clusters)} Cluster gefunden")

        # Generate mappings
        mappings = []

        for normalized, variants in clusters.items():
            if len(variants) == 1:
                # Single variant - create simple mapping
                team_name, match_count = variants[0]

                mapping = {
                    'canonical_name': team_name,
                    'aliases': [],
                    'region': self._guess_region(team_name),
                    'notes': f'{match_count} matches'
                }
                mappings.append(mapping)

            else:
                # Multiple variants - pick canonical and create aliases
                # Sort by match count, highest becomes canonical
                variants = sorted(variants, key=lambda x: x[1], reverse=True)

                canonical = variants[0][0]
                aliases = [name for name, _ in variants[1:]]

                # Check for known rebrands
                for old, new in self.known_rebrands.items():
                    if any(old.lower() in v[0].lower() for v in variants):
                        canonical = new
                        aliases = [v[0] for v in variants if v[0] != new]
                        break

                total_matches = sum(count for _, count in variants)

                mapping = {
                    'canonical_name': canonical,
                    'aliases': aliases,
                    'region': self._guess_region(canonical),
                    'notes': f'{len(variants)} variants, {total_matches} total matches'
                }
                mappings.append(mapping)

        return mappings

    def _guess_region(self, team_name: str) -> str:
        """Rate Region"""
        name_lower = team_name.lower()

        # CN teams
        if any(x in name_lower for x in ['edg', 'edward gaming', 'rng', 'royal never',
                                           'jdg', 'jd gaming', 'blg', 'bilibili',
                                           'tes', 'top esports', 'fpx', 'funplus',
                                           'lng', 'we', 'team we', 'ig', 'invictus',
                                           'omg', 'oh my god', 'lgd', 'suning',
                                           'weibo', 'victory five', 'anyone', 'ultra prime']):
            return 'CN'

        # KR teams
        if any(x in name_lower for x in ['t1', 'skt', 'sk telecom', 'gen.g', 'geng',
                                           'samsung', 'drx', 'dragonx', 'kt rolster',
                                           'hle', 'hanwha', 'dwg', 'damwon', 'kz',
                                           'kingzone', 'longzhu', 'afreeca', 'af',
                                           'rox', 'koo', 'tigers', 'griffin', 'jin air',
                                           'mvp', 'najin', 'cj entus', 'azubu']):
            return 'KR'

        # EU teams
        if any(x in name_lower for x in ['fnatic', 'fnc', 'g2', 'g2 esports',
                                           'mad lions', 'mad', 'rogue', 'rge',
                                           'vitality', 'vit', 'sk gaming', 'sk',
                                           'misfits', 'msf', 'excel', 'xl',
                                           'origen', 'og', 'splyce', 'spy',
                                           'h2k', 'unicorns of love', 'uol',
                                           'schalke', 's04', 'alliance']):
            return 'EU'

        # NA teams
        if any(x in name_lower for x in ['tsm', 'team solomid', 'cloud9', 'c9',
                                           'team liquid', 'tl', 'liquid',
                                           '100 thieves', '100t', 'flyquest', 'fly',
                                           'eg', 'evil geniuses', 'clg', 'counter logic',
                                           'dignitas', 'dig', 'immortals', 'imt',
                                           'golden guardians', 'gg', 'optic', 'echo fox']):
            return 'NA'

        # BR teams
        if any(x in name_lower for x in ['loud', 'lll', 'pain', 'png', 'kabum',
                                           'red canids', 'red', 'flamengo', 'intz',
                                           'vivo keyd', 'keyd', 'liberty']):
            return 'BR'

        # Other regions
        if any(x in name_lower for x in ['psg', 'talon', 'flash wolves', 'ahq', 'j team']):
            return 'TW'
        if any(x in name_lower for x in ['gam', 'saigon', 'vikings', 'lowkey']):
            return 'VN'
        if any(x in name_lower for x in ['dfm', 'detonation', 'v3', 'sengoku']):
            return 'JP'
        if any(x in name_lower for x in ['beyond', 'pentanet', 'chiefs', 'legacy']):
            return 'OCE'

        return 'Unknown'

    def detect_historical_teams(self, teams: List[Tuple[str, int]]) -> List[Dict]:
        """
        Erkenne historische Teams und ihre Rebrands

        Args:
            teams: List of (team_name, match_count)

        Returns:
            List of rebrand mappings
        """
        rebrands = []

        team_names = {name for name, _ in teams}

        for old_name, new_name in self.known_rebrands.items():
            # Check if both old and new name exist in database
            old_exists = any(old_name.lower() in name.lower() for name in team_names)
            new_exists = any(new_name.lower() in name.lower() for name in team_names)

            if old_exists:
                rebrands.append({
                    'old_name': old_name,
                    'new_name': new_name,
                    'both_exist': new_exists,
                    'action': 'merge' if new_exists else 'rename'
                })

        return rebrands

    def export_mappings(self, mappings: List[Dict], filename: str = "generated_mappings.json"):
        """
        Exportiere generierte Mappings

        Args:
            mappings: List of mapping entries
            filename: Output filename
        """
        output = {
            '_comment': 'Auto-generated team name mappings',
            '_generated_at': str(Path(self.db_path).stat().st_mtime),
            'mappings': mappings,
            'fuzzy_matching_rules': {
                'enabled': True,
                'similarity_threshold': 0.85,
                'ignore_case': True,
                'remove_suffixes': ['LoL', 'Esports', 'Gaming', 'E-Sports'],
                'normalize_spaces': True
            }
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        print(f"\n✓ Mappings exportiert nach: {filename}")
        print(f"   Total entries: {len(mappings)}")

    def merge_with_existing(self, new_mappings: List[Dict],
                           existing_file: str = "config/team_name_mappings.json") -> List[Dict]:
        """
        Merge neue Mappings mit existierenden

        Args:
            new_mappings: New mappings to add
            existing_file: Path to existing mappings file

        Returns:
            Merged mappings
        """
        existing_path = Path(existing_file)

        if not existing_path.exists():
            print(f"⚠️  Existing file not found: {existing_file}")
            return new_mappings

        with open(existing_path, 'r', encoding='utf-8') as f:
            existing = json.load(f)

        existing_canonicals = {m['canonical_name'] for m in existing.get('mappings', [])}

        # Only add new teams
        merged = existing.get('mappings', [])
        added = 0

        for mapping in new_mappings:
            canonical = mapping['canonical_name']

            if canonical not in existing_canonicals:
                merged.append(mapping)
                added += 1
            else:
                # Team already exists, maybe merge aliases
                for existing_mapping in merged:
                    if existing_mapping['canonical_name'] == canonical:
                        # Add new aliases
                        for alias in mapping['aliases']:
                            if alias not in existing_mapping['aliases']:
                                existing_mapping['aliases'].append(alias)

        print(f"\n✓ Merged mappings:")
        print(f"   Existing: {len(existing_canonicals)}")
        print(f"   New: {added}")
        print(f"   Total: {len(merged)}")

        return merged

    def print_summary(self, mappings: List[Dict]):
        """
        Drucke Zusammenfassung der generierten Mappings

        Args:
            mappings: List of mappings
        """
        print("\n" + "="*80)
        print("GENERATED MAPPINGS SUMMARY")
        print("="*80)

        # Count by region
        by_region = defaultdict(int)
        total_aliases = 0

        for mapping in mappings:
            by_region[mapping.get('region', 'Unknown')] += 1
            total_aliases += len(mapping.get('aliases', []))

        print(f"\n📊 STATISTICS:")
        print(f"   Total canonical teams: {len(mappings)}")
        print(f"   Total aliases:         {total_aliases}")
        print(f"   Average aliases/team:  {total_aliases/len(mappings):.1f}")

        print(f"\n🌍 BY REGION:")
        for region, count in sorted(by_region.items(), key=lambda x: x[1], reverse=True):
            percentage = count / len(mappings) * 100
            print(f"   {region:8s}: {count:3d} teams ({percentage:5.1f}%)")

        # Show examples
        print(f"\n📝 EXAMPLES (top 10 by alias count):")
        sorted_mappings = sorted(mappings, key=lambda x: len(x.get('aliases', [])), reverse=True)

        for i, mapping in enumerate(sorted_mappings[:10], 1):
            canonical = mapping['canonical_name']
            aliases = mapping.get('aliases', [])
            region = mapping.get('region', '??')

            print(f"\n   {i}. {canonical} ({region})")
            if aliases:
                print(f"      Aliases: {', '.join(aliases[:5])}")
                if len(aliases) > 5:
                    print(f"      ... und {len(aliases)-5} weitere")
            print(f"      {mapping.get('notes', '')}")


def main():
    """Main entry point"""
    print("="*80)
    print("BULK TEAM NAME MAPPING GENERATOR")
    print("="*80)

    db_path = Path("db/elo_system.db")
    if not db_path.exists():
        print(f"\n⚠️  Database not found: {db_path}")
        print("\nBitte führe zuerst einen Import aus")
        return

    generator = BulkMappingGenerator()

    # Get statistics
    teams = generator.get_all_teams_with_frequency()
    total_teams = len(teams)
    total_matches = sum(count for _, count in teams)

    print(f"\n📊 DATABASE STATISTICS:")
    print(f"   Total unique teams: {total_teams}")
    print(f"   Total matches:      {total_matches}")

    if teams:
        print(f"\n🏆 TOP 10 TEAMS BY MATCHES:")
        for i, (name, count) in enumerate(teams[:10], 1):
            print(f"   {i:2d}. {name:40s} {count:5d} matches")

    # Ask for minimum matches
    min_input = input(f"\nMinimum matches für Mapping (default: 10): ").strip()
    min_matches = int(min_input) if min_input else 10

    print(f"\n🔧 Generiere Mappings für Teams mit >= {min_matches} matches...")
    mappings = generator.auto_generate_mappings(min_matches=min_matches)

    # Print summary
    generator.print_summary(mappings)

    # Detect rebrands
    print(f"\n🔄 ERKANNTE REBRANDS:")
    rebrands = generator.detect_historical_teams(teams)
    if rebrands:
        for rebrand in rebrands:
            action_symbol = "🔀" if rebrand['action'] == 'merge' else "➡️"
            print(f"   {action_symbol} {rebrand['old_name']} → {rebrand['new_name']}")
            print(f"      Action: {rebrand['action']}")
    else:
        print("   Keine bekannten Rebrands gefunden")

    # Ask what to do
    print("\n" + "="*80)
    print("Was möchtest du tun?")
    print("  1) Exportiere als neue Datei (generated_mappings.json)")
    print("  2) Merge mit existierenden Mappings")
    print("  3) Beides")
    print("  4) Abbrechen")

    choice = input("\nWähle [1/2/3/4]: ").strip()

    if choice == '1' or choice == '3':
        generator.export_mappings(mappings)

    if choice == '2' or choice == '3':
        merged = generator.merge_with_existing(mappings)

        save = input(f"\nMerged mappings in config/team_name_mappings.json speichern? [y/n]: ").strip().lower()
        if save == 'y':
            config = {
                '_comment': 'Maps team names from different sources to canonical names',
                '_sources': {
                    'lolesports': 'Official Lolesports API',
                    'leaguepedia': 'Leaguepedia/LOL Fandom Wiki',
                    'google_sheets': 'Manual Google Sheets data'
                },
                'mappings': merged,
                'fuzzy_matching_rules': {
                    'enabled': True,
                    'similarity_threshold': 0.85,
                    'ignore_case': True,
                    'remove_suffixes': ['LoL', 'Esports', 'Gaming', 'E-Sports'],
                    'normalize_spaces': True
                },
                'regional_hints': {
                    'LEC': 'EU',
                    'LCS': 'NA',
                    'LPL': 'CN',
                    'LCK': 'KR',
                    'CBLOL': 'BR',
                    'PCS': 'TW',
                    'VCS': 'VN',
                    'LJL': 'JP'
                }
            }

            with open('config/team_name_mappings.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            print(f"\n✓ Gespeichert in config/team_name_mappings.json")

    print("\n✓ Fertig!")


if __name__ == "__main__":
    main()
