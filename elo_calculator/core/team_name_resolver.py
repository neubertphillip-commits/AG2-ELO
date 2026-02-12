"""
Team Name Resolver
Intelligently maps team names across different data sources
Handles Lolesports API ≠ Leaguepedia ≠ Google Sheets naming differences
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from difflib import SequenceMatcher
import re


class TeamNameResolver:
    """
    Resolves team names across different data sources

    Uses:
    1. Manual mappings (config/team_name_mappings.json)
    2. Fuzzy matching for automatic resolution
    3. Caching for performance
    """

    def __init__(self, mappings_file: str = "config/team_name_mappings.json"):
        """
        Initialize resolver

        Args:
            mappings_file: Path to mappings configuration
        """
        self.mappings_file = Path(mappings_file)
        self.mappings = self._load_mappings()

        # Build lookup tables
        self.alias_to_canonical = {}
        self.canonical_teams = set()
        self._build_lookup_tables()

        # Cache for resolved names
        self.resolution_cache = {}

    def _load_mappings(self) -> Dict:
        """Load mappings from JSON file"""
        if not self.mappings_file.exists():
            print(f"⚠️  Mappings file not found: {self.mappings_file}")
            return {"mappings": [], "fuzzy_matching_rules": {}}

        with open(self.mappings_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return data

    def _build_lookup_tables(self):
        """Build fast lookup tables from mappings"""
        for mapping in self.mappings.get("mappings", []):
            canonical = mapping["canonical_name"]
            self.canonical_teams.add(canonical)

            # Map canonical name to itself
            self.alias_to_canonical[canonical.lower()] = canonical

            # Map all aliases to canonical
            for alias in mapping.get("aliases", []):
                self.alias_to_canonical[alias.lower()] = canonical

    def normalize_name(self, name: str) -> str:
        """
        Normalize team name for matching

        Args:
            name: Team name to normalize

        Returns:
            Normalized name
        """
        if not name:
            return ""

        # Get fuzzy matching rules
        rules = self.mappings.get("fuzzy_matching_rules", {})

        # Remove common suffixes
        normalized = name
        if rules.get("remove_suffixes"):
            for suffix in rules["remove_suffixes"]:
                pattern = rf'\s*{re.escape(suffix)}\s*$'
                normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)

        # Normalize spaces
        if rules.get("normalize_spaces", True):
            normalized = ' '.join(normalized.split())

        # Case normalization
        if rules.get("ignore_case", True):
            normalized = normalized.lower()

        return normalized.strip()

    def similarity(self, str1: str, str2: str) -> float:
        """
        Calculate similarity between two strings

        Args:
            str1: First string
            str2: Second string

        Returns:
            Similarity score (0-1)
        """
        return SequenceMatcher(None, str1, str2).ratio()

    def fuzzy_match(self, name: str) -> Optional[Tuple[str, float]]:
        """
        Find best fuzzy match for team name

        Args:
            name: Team name to match

        Returns:
            Tuple of (canonical_name, confidence) or None
        """
        rules = self.mappings.get("fuzzy_matching_rules", {})

        if not rules.get("enabled", True):
            return None

        threshold = rules.get("similarity_threshold", 0.85)
        normalized_input = self.normalize_name(name)

        best_match = None
        best_score = 0.0

        # Check against all known names (canonical + aliases)
        for alias, canonical in self.alias_to_canonical.items():
            normalized_alias = self.normalize_name(alias)
            score = self.similarity(normalized_input, normalized_alias)

            if score > best_score and score >= threshold:
                best_score = score
                best_match = canonical

        if best_match:
            return (best_match, best_score)

        return None

    def resolve(self, name: str, source: str = "unknown") -> str:
        """
        Resolve team name to canonical form

        Args:
            name: Team name to resolve
            source: Data source (for logging)

        Returns:
            Canonical team name
        """
        if not name:
            return name

        # Check cache
        cache_key = name.lower()
        if cache_key in self.resolution_cache:
            return self.resolution_cache[cache_key]

        # Try exact match (case-insensitive)
        normalized = name.lower()
        if normalized in self.alias_to_canonical:
            canonical = self.alias_to_canonical[normalized]
            self.resolution_cache[cache_key] = canonical
            return canonical

        # Try fuzzy matching
        fuzzy_result = self.fuzzy_match(name)
        if fuzzy_result:
            canonical, confidence = fuzzy_result

            # Log low-confidence matches for review
            if confidence < 0.95:
                print(f"  ⚠️  Fuzzy match: '{name}' → '{canonical}' "
                      f"(confidence: {confidence:.2%}, source: {source})")

            self.resolution_cache[cache_key] = canonical
            return canonical

        # No match found - return original name
        # Log for manual mapping addition
        if source != "unknown":
            print(f"  ⚠️  No mapping found: '{name}' (source: {source})")
            print(f"     Add to config/team_name_mappings.json if needed")

        # Cache negative result to avoid repeated lookups
        self.resolution_cache[cache_key] = name
        return name

    def resolve_batch(self, names: List[str], source: str = "unknown") -> Dict[str, str]:
        """
        Resolve multiple team names

        Args:
            names: List of team names
            source: Data source

        Returns:
            Dictionary mapping original → canonical names
        """
        results = {}
        for name in names:
            results[name] = self.resolve(name, source)
        return results

    def get_canonical_name(self, name: str) -> Optional[str]:
        """
        Get canonical name if exists, None otherwise

        Args:
            name: Team name

        Returns:
            Canonical name or None
        """
        resolved = self.resolve(name)
        if resolved in self.canonical_teams:
            return resolved
        return None

    def add_mapping(self, canonical: str, aliases: List[str],
                   region: str = None, notes: str = ""):
        """
        Add new mapping (in-memory, needs manual save)

        Args:
            canonical: Canonical team name
            aliases: List of aliases
            region: Team region
            notes: Additional notes
        """
        # Add to mappings
        new_mapping = {
            "canonical_name": canonical,
            "aliases": aliases,
            "region": region,
            "notes": notes
        }

        self.mappings["mappings"].append(new_mapping)

        # Update lookup tables
        self.canonical_teams.add(canonical)
        self.alias_to_canonical[canonical.lower()] = canonical

        for alias in aliases:
            self.alias_to_canonical[alias.lower()] = canonical

        print(f"✓ Added mapping: {canonical} ← {aliases}")
        print(f"  Save with .save_mappings() to persist")

    def save_mappings(self):
        """Save mappings back to JSON file"""
        with open(self.mappings_file, 'w', encoding='utf-8') as f:
            json.dump(self.mappings, f, indent=2, ensure_ascii=False)

        print(f"✓ Saved mappings to: {self.mappings_file}")

    def get_stats(self) -> Dict:
        """Get statistics about mappings"""
        total_canonical = len(self.canonical_teams)
        total_aliases = len(self.alias_to_canonical)
        cached = len(self.resolution_cache)

        return {
            "canonical_teams": total_canonical,
            "total_mappings": total_aliases,
            "cache_size": cached
        }

    def print_stats(self):
        """Print mapping statistics"""
        stats = self.get_stats()

        print("\n" + "="*60)
        print("TEAM NAME RESOLVER - STATISTICS")
        print("="*60)
        print(f"\n  Canonical Teams: {stats['canonical_teams']}")
        print(f"  Total Mappings:  {stats['total_mappings']}")
        print(f"  Cache Size:      {stats['cache_size']}")

        # Show some examples
        print(f"\n  Example Mappings:")
        for i, mapping in enumerate(self.mappings.get("mappings", [])[:5], 1):
            canonical = mapping["canonical_name"]
            aliases = mapping.get("aliases", [])[:2]  # Show first 2 aliases
            print(f"    {i}. {canonical} ← {', '.join(aliases)}")


# Singleton instance
_resolver_instance = None


def get_resolver() -> TeamNameResolver:
    """Get singleton resolver instance"""
    global _resolver_instance
    if _resolver_instance is None:
        _resolver_instance = TeamNameResolver()
    return _resolver_instance


def resolve_team_name(name: str, source: str = "unknown") -> str:
    """
    Convenience function to resolve team name

    Args:
        name: Team name to resolve
        source: Data source

    Returns:
        Canonical team name
    """
    resolver = get_resolver()
    return resolver.resolve(name, source)


if __name__ == "__main__":
    # Test the resolver
    print("="*60)
    print("TEAM NAME RESOLVER - TEST")
    print("="*60)

    resolver = TeamNameResolver()

    # Print stats
    resolver.print_stats()

    # Test cases
    test_cases = [
        ("LLL", "lolesports"),
        ("LOUD", "leaguepedia"),
        ("Los Loud", "google_sheets"),
        ("T1", "lolesports"),
        ("SK Telecom T1", "leaguepedia"),
        ("SKT", "google_sheets"),
        ("GenG", "lolesports"),
        ("Gen.G Esports", "leaguepedia"),
        ("Samsung Galaxy", "historical"),
        ("G2", "lolesports"),
        ("G2 Esports", "leaguepedia"),
        ("Unknown Team XYZ", "test"),  # Should not match
    ]

    print("\n" + "="*60)
    print("RESOLUTION TESTS")
    print("="*60)
    print(f"\n{'Input':<25} {'Source':<15} {'→ Resolved':<25} {'Match'}")
    print("-"*75)

    for name, source in test_cases:
        resolved = resolver.resolve(name, source)
        is_canonical = resolved in resolver.canonical_teams
        match_symbol = "✓" if is_canonical else "⚠️"

        print(f"{name:<25} {source:<15} → {resolved:<25} {match_symbol}")

    # Test fuzzy matching
    print("\n" + "="*60)
    print("FUZZY MATCHING EXAMPLES")
    print("="*60)

    fuzzy_tests = [
        "loud esports",
        "T 1",
        "Gen G",
        "MAD Lions Madrid",
    ]

    for name in fuzzy_tests:
        resolved = resolver.resolve(name, "fuzzy_test")
        fuzzy_result = resolver.fuzzy_match(name)

        if fuzzy_result:
            canonical, confidence = fuzzy_result
            print(f"\n  '{name}' → '{canonical}' (confidence: {confidence:.2%})")
        else:
            print(f"\n  '{name}' → No fuzzy match")
