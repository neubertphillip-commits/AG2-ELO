#!/usr/bin/env python3
"""
Team Name Mapping Analyzer and Generator
Hilft beim Erstellen und Erweitern von Team-Namen-Mappings

Features:
- Analysiert alle Team-Namen in der Datenbank
- Identifiziert unmapped Teams
- Schlägt Mappings basierend auf Ähnlichkeit vor
- Generiert automatisch Mapping-Einträge
- Aktualisiert config/team_name_mappings.json
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict
from difflib import SequenceMatcher
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.team_name_resolver import TeamNameResolver


class TeamMappingAnalyzer:
    """
    Analysiert Team-Namen und generiert Mapping-Vorschläge
    """

    def __init__(self, db_path: str = "db/elo_system.db"):
        """
        Initialize analyzer

        Args:
            db_path: Path to database file
        """
        self.db_path = Path(db_path)
        self.resolver = TeamNameResolver()

        # Statistics
        self.total_teams = 0
        self.mapped_teams = 0
        self.unmapped_teams = 0
        self.unique_team_names = set()

    def get_all_team_names_from_db(self) -> List[Tuple[str, int]]:
        """
        Hole alle Team-Namen aus der Datenbank

        Returns:
            List of (team_name, occurrence_count) tuples
        """
        if not self.db_path.exists():
            print(f"⚠️  Database not found: {self.db_path}")
            print("   Run import script first to create database with matches")
            return []

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get all unique team names with their occurrence count
        cursor.execute("""
            SELECT name,
                   (SELECT COUNT(*) FROM matches WHERE team1_id = teams.id OR team2_id = teams.id) as match_count
            FROM teams
            ORDER BY match_count DESC, name
        """)

        teams = cursor.fetchall()
        conn.close()

        return teams

    def analyze_mappings(self) -> Dict:
        """
        Analysiere alle Team-Namen und kategorisiere sie

        Returns:
            Dictionary mit Analyse-Ergebnissen
        """
        team_names = self.get_all_team_names_from_db()

        if not team_names:
            return {
                'total': 0,
                'mapped': [],
                'unmapped': [],
                'suggestions': []
            }

        mapped = []
        unmapped = []

        for name, count in team_names:
            self.unique_team_names.add(name)

            # Check if name is mapped
            resolved = self.resolver.resolve(name, source="database")

            if resolved in self.resolver.canonical_teams:
                # Already mapped to canonical name
                mapped.append({
                    'original': name,
                    'canonical': resolved,
                    'match_count': count,
                    'is_exact': (name == resolved)
                })
                self.mapped_teams += 1
            else:
                # Not mapped yet
                unmapped.append({
                    'name': name,
                    'match_count': count,
                    'resolved_to': resolved  # What it currently resolves to
                })
                self.unmapped_teams += 1

        self.total_teams = len(team_names)

        return {
            'total': self.total_teams,
            'mapped': mapped,
            'unmapped': unmapped,
            'suggestions': self._generate_suggestions(unmapped)
        }

    def _generate_suggestions(self, unmapped_teams: List[Dict]) -> List[Dict]:
        """
        Generiere Mapping-Vorschläge für unmapped Teams

        Args:
            unmapped_teams: List of unmapped team dictionaries

        Returns:
            List of suggestions
        """
        suggestions = []

        for team in unmapped_teams:
            name = team['name']

            # Find similar canonical teams
            similar = self._find_similar_teams(name)

            suggestion = {
                'team_name': name,
                'match_count': team['match_count'],
                'similar_canonicals': similar,
                'auto_suggestion': None
            }

            # If very high similarity, auto-suggest
            if similar and similar[0]['similarity'] > 0.90:
                suggestion['auto_suggestion'] = similar[0]['canonical']

            suggestions.append(suggestion)

        return suggestions

    def _find_similar_teams(self, team_name: str, top_n: int = 3) -> List[Dict]:
        """
        Finde ähnliche kanonische Team-Namen

        Args:
            team_name: Team name to match
            top_n: Number of top matches to return

        Returns:
            List of similar teams with similarity scores
        """
        normalized_input = self.resolver.normalize_name(team_name)

        similarities = []

        for canonical in self.resolver.canonical_teams:
            normalized_canonical = self.resolver.normalize_name(canonical)

            # Calculate similarity
            similarity = SequenceMatcher(None, normalized_input, normalized_canonical).ratio()

            if similarity > 0.5:  # Only include reasonable matches
                similarities.append({
                    'canonical': canonical,
                    'similarity': similarity
                })

        # Sort by similarity
        similarities.sort(key=lambda x: x['similarity'], reverse=True)

        return similarities[:top_n]

    def print_analysis_report(self, analysis: Dict):
        """
        Drucke detaillierten Analyse-Report

        Args:
            analysis: Analysis results from analyze_mappings()
        """
        print("\n" + "="*80)
        print("TEAM NAME MAPPING ANALYSIS")
        print("="*80)

        print(f"\n📊 OVERVIEW:")
        print(f"   Total unique teams in database: {analysis['total']}")
        print(f"   ✓ Mapped teams:                 {len(analysis['mapped'])} ({len(analysis['mapped'])/analysis['total']*100:.1f}%)")
        print(f"   ⚠ Unmapped teams:               {len(analysis['unmapped'])} ({len(analysis['unmapped'])/analysis['total']*100:.1f}%)")

        # Mapped teams summary
        if analysis['mapped']:
            print(f"\n✓ MAPPED TEAMS (showing top 10):")
            print(f"   {'Original Name':<35} {'→ Canonical':<25} {'Matches':<10}")
            print(f"   {'-'*75}")

            for team in sorted(analysis['mapped'], key=lambda x: x['match_count'], reverse=True)[:10]:
                symbol = "=" if team['is_exact'] else "→"
                print(f"   {team['original']:<35} {symbol} {team['canonical']:<25} {team['match_count']:<10}")

        # Unmapped teams
        if analysis['unmapped']:
            print(f"\n⚠ UNMAPPED TEAMS (showing all):")
            print(f"   {'Team Name':<40} {'Matches':<10} {'Auto-Suggestion':<30}")
            print(f"   {'-'*85}")

            for suggestion in analysis['suggestions']:
                auto = suggestion.get('auto_suggestion', '-')
                confidence = ""
                if auto != '-' and suggestion['similar_canonicals']:
                    confidence = f"({suggestion['similar_canonicals'][0]['similarity']:.0%})"

                print(f"   {suggestion['team_name']:<40} {suggestion['match_count']:<10} {auto:<20} {confidence}")

        # Suggestions with details
        if analysis['suggestions']:
            print(f"\n💡 DETAILED SUGGESTIONS:")

            for i, suggestion in enumerate(analysis['suggestions'][:20], 1):  # Limit to 20 for readability
                print(f"\n   {i}. {suggestion['team_name']} ({suggestion['match_count']} matches)")

                if suggestion['similar_canonicals']:
                    print(f"      Similar canonical teams:")
                    for similar in suggestion['similar_canonicals']:
                        print(f"        - {similar['canonical']:<30} (similarity: {similar['similarity']:.0%})")
                else:
                    print(f"      No similar canonical teams found - new team?")

    def generate_new_mappings(self, analysis: Dict, min_matches: int = 5) -> List[Dict]:
        """
        Generiere neue Mapping-Einträge für häufige unmapped Teams

        Args:
            analysis: Analysis results
            min_matches: Minimum matches to include team

        Returns:
            List of new mapping entries to add
        """
        new_mappings = []

        for suggestion in analysis['suggestions']:
            # Skip low-frequency teams
            if suggestion['match_count'] < min_matches:
                continue

            team_name = suggestion['team_name']

            # If we have a high-confidence auto-suggestion, use it as alias
            if suggestion.get('auto_suggestion'):
                # This is likely an alias of existing team
                print(f"\n   Alias detected: '{team_name}' → '{suggestion['auto_suggestion']}'")
                print(f"   Add this alias to existing '{suggestion['auto_suggestion']}' entry")
                continue

            # Otherwise, create new canonical entry
            mapping = {
                'canonical_name': team_name,
                'aliases': [],
                'region': self._guess_region(team_name),
                'notes': f'Auto-generated from database analysis ({suggestion["match_count"]} matches)'
            }

            new_mappings.append(mapping)

        return new_mappings

    def _guess_region(self, team_name: str) -> str:
        """
        Rate die Region basierend auf Team-Namen

        Args:
            team_name: Team name

        Returns:
            Region code or "Unknown"
        """
        name_lower = team_name.lower()

        # Simple heuristics
        if any(word in name_lower for word in ['lpl', 'edg', 'rng', 'jdg', 'blg', 'tes', 'lng']):
            return 'CN'
        elif any(word in name_lower for word in ['lck', 't1', 'skt', 'gen', 'drx', 'kt', 'hle']):
            return 'KR'
        elif any(word in name_lower for word in ['lec', 'fnatic', 'g2', 'mad', 'rogue']):
            return 'EU'
        elif any(word in name_lower for word in ['lcs', 'tsm', 'c9', 'tl', '100t', 'fly']):
            return 'NA'
        elif any(word in name_lower for word in ['cblol', 'loud', 'pain', 'kabum']):
            return 'BR'
        elif any(word in name_lower for word in ['pcs', 'psg', 'flash wolves']):
            return 'TW'
        elif any(word in name_lower for word in ['vcs', 'gam', 'saigon']):
            return 'VN'
        elif any(word in name_lower for word in ['ljl', 'detonation', 'dfm']):
            return 'JP'

        return 'Unknown'

    def interactive_mapping_mode(self, analysis: Dict):
        """
        Interaktiver Modus zum Erstellen von Mappings

        Args:
            analysis: Analysis results
        """
        print("\n" + "="*80)
        print("INTERACTIVE MAPPING MODE")
        print("="*80)
        print("\nFür jedes unmapped Team kannst du:")
        print("  1) Es als Alias zu einem existierenden Team hinzufügen")
        print("  2) Ein neues kanonisches Team erstellen")
        print("  3) Überspringen")
        print("\nTippe 'q' um zu beenden, 's' um zu speichern\n")

        added_mappings = []

        for suggestion in analysis['suggestions']:
            team_name = suggestion['team_name']
            match_count = suggestion['match_count']

            print(f"\n{'='*80}")
            print(f"Team: {team_name} ({match_count} matches)")

            if suggestion['similar_canonicals']:
                print(f"\nÄhnliche Teams:")
                for i, similar in enumerate(suggestion['similar_canonicals'], 1):
                    print(f"  {i}) {similar['canonical']} (similarity: {similar['similarity']:.0%})")

            choice = input(f"\nWas möchtest du tun? [alias/new/skip/quit/save]: ").strip().lower()

            if choice == 'q' or choice == 'quit':
                break
            elif choice == 's' or choice == 'save':
                self._save_mappings(added_mappings)
                break
            elif choice == 'skip' or choice == '':
                continue
            elif choice == 'alias':
                canonical = input(f"  Zu welchem Team gehört '{team_name}'? ").strip()
                if canonical:
                    added_mappings.append({
                        'type': 'alias',
                        'canonical': canonical,
                        'alias': team_name
                    })
                    print(f"  ✓ Alias hinzugefügt: '{team_name}' → '{canonical}'")
            elif choice == 'new':
                region = input(f"  Region für '{team_name}' (CN/KR/EU/NA/BR/etc.): ").strip().upper()
                aliases_input = input(f"  Weitere Aliases (komma-getrennt, leer für keine): ").strip()

                aliases = [a.strip() for a in aliases_input.split(',') if a.strip()]

                added_mappings.append({
                    'type': 'new',
                    'canonical_name': team_name,
                    'aliases': aliases,
                    'region': region or 'Unknown',
                    'notes': f'Added manually ({match_count} matches)'
                })
                print(f"  ✓ Neues Team erstellt: '{team_name}'")

        # Offer to save at the end
        if added_mappings:
            save = input(f"\n{len(added_mappings)} Mappings hinzugefügt. Jetzt speichern? [y/n]: ").strip().lower()
            if save == 'y':
                self._save_mappings(added_mappings)

    def _save_mappings(self, new_mappings: List[Dict]):
        """
        Speichere neue Mappings in config/team_name_mappings.json

        Args:
            new_mappings: List of new mappings to add
        """
        if not new_mappings:
            print("Keine Mappings zum Speichern")
            return

        # Load current mappings
        config_path = Path("config/team_name_mappings.json")
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # Process each new mapping
        for mapping in new_mappings:
            if mapping['type'] == 'alias':
                # Find canonical team and add alias
                canonical = mapping['canonical']
                alias = mapping['alias']

                found = False
                for team in config['mappings']:
                    if team['canonical_name'] == canonical:
                        if alias not in team['aliases']:
                            team['aliases'].append(alias)
                            print(f"  ✓ Alias '{alias}' hinzugefügt zu '{canonical}'")
                        found = True
                        break

                if not found:
                    print(f"  ⚠️  Canonical team '{canonical}' nicht gefunden!")

            elif mapping['type'] == 'new':
                # Add new canonical team
                new_team = {
                    'canonical_name': mapping['canonical_name'],
                    'aliases': mapping['aliases'],
                    'region': mapping['region'],
                    'notes': mapping['notes']
                }
                config['mappings'].append(new_team)
                print(f"  ✓ Neues Team '{mapping['canonical_name']}' hinzugefügt")

        # Save back to file
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        print(f"\n✓ Mappings gespeichert in {config_path}")


def main():
    """Main entry point"""
    print("="*80)
    print("TEAM NAME MAPPING ANALYZER")
    print("="*80)

    # Check if database exists
    db_path = Path("db/elo_system.db")
    if not db_path.exists():
        print(f"\n⚠️  Database not found: {db_path}")
        print("\nBitte führe zuerst einen Import-Script aus:")
        print("  - python major_regions_tournament_import_matchschedule.py")
        print("  - python minor_regions_tournament_import_matchschedule.py")
        return

    analyzer = TeamMappingAnalyzer()

    print("\n🔍 Analysiere Team-Namen...")
    analysis = analyzer.analyze_mappings()

    # Print detailed report
    analyzer.print_analysis_report(analysis)

    # Ask what to do
    print("\n" + "="*80)
    print("Was möchtest du tun?")
    print("  1) Interaktiven Mapping-Modus starten")
    print("  2) Export unmapped teams zu JSON")
    print("  3) Beenden")

    choice = input("\nWähle eine Option [1/2/3]: ").strip()

    if choice == '1':
        analyzer.interactive_mapping_mode(analysis)
    elif choice == '2':
        # Export unmapped teams
        output_file = "unmapped_teams.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(analysis['suggestions'], f, indent=2, ensure_ascii=False)
        print(f"\n✓ Unmapped teams exportiert nach: {output_file}")

    print("\n✓ Fertig!")


if __name__ == "__main__":
    main()
