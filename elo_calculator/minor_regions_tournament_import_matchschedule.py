#!/usr/bin/env python3
"""
MINOR REGIONS TOURNAMENT DATA IMPORT - Using MatchSchedule Table
Importiert Match-Daten für Minor Region Turniere (CBLOL, LLA, LJL, PCS, VCS, etc.)

WICHTIG: Nutzt MatchSchedule statt ScoreboardGames!
- MatchSchedule hat bereits Match-level Daten (kein Game-Aggregation nötig)
- Verwendet SPACES in OverviewPage (z.B. "CBLOL/2024 Season/Split 1")
- Importiert nur Minor Regions: CBLOL, LLA, LJL, PCS, VCS, TCL, LCL, OPL, etc.
"""

import json
import time
import os
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.leaguepedia_loader import LeaguepediaLoader
from core.database import DatabaseManager
from core.team_resolver import TeamResolver

def estimate_tournament_duration(tournament_name: str) -> int:
    """
    Estimate tournament duration in days based on tournament type.

    Args:
        tournament_name: Tournament name

    Returns:
        Estimated duration in days
    """
    name_lower = tournament_name.lower()

    # Playoffs are shorter
    if 'playoff' in name_lower:
        return 7  # ~1 week for playoffs
    elif 'regional' in name_lower or 'final' in name_lower:
        return 5  # ~5 days for regional finals
    elif 'msi' in name_lower or 'mid-season' in name_lower:
        return 14  # ~2 weeks for MSI
    elif 'world' in name_lower:
        return 30  # ~1 month for Worlds
    elif 'iem' in name_lower:
        return 4  # ~4 days for IEM
    elif 'kespa' in name_lower or 'demacia' in name_lower or 'rift rival' in name_lower:
        return 5  # ~5 days for cups
    else:
        # Regular season
        return 56  # ~8 weeks for regular season

def estimate_date_from_tournament(tournament_name: str, match_index: int, total_matches: int) -> datetime:
    """
    Estimate a date based on tournament name and match position.
    Distributes matches realistically over tournament duration.

    Args:
        tournament_name: Tournament name (e.g., "LPL 2013 Spring", "LCK 2020 Summer Playoffs")
        match_index: Index of this match (0-based)
        total_matches: Total number of matches in tournament

    Returns:
        Estimated datetime object
    """
    import re
    from datetime import timedelta

    # Extract year from tournament name
    year_match = re.search(r'20\d{2}|2013|2014|2015', tournament_name)
    year = int(year_match.group()) if year_match else 2020

    name_lower = tournament_name.lower()

    # Determine start month and day based on split/phase
    if 'winter' in name_lower:
        month, day = 1, 15
    elif 'spring' in name_lower:
        if 'playoff' in name_lower:
            month, day = 4, 15  # Spring Playoffs
        elif 'regional' in name_lower or 'final' in name_lower:
            month, day = 5, 1  # Spring Regional Finals
        else:
            month, day = 3, 15  # Spring Regular Season
    elif 'summer' in name_lower:
        if 'playoff' in name_lower:
            month, day = 8, 15  # Summer Playoffs
        elif 'regional' in name_lower or 'final' in name_lower:
            month, day = 9, 15  # Summer Regional Finals
        else:
            month, day = 7, 15  # Summer Regular Season
    elif 'msi' in name_lower or 'mid-season' in name_lower:
        month, day = 5, 15  # MSI
    elif 'world' in name_lower:
        month, day = 10, 15  # Worlds
    elif 'iem' in name_lower:
        # IEM tournaments vary, use tournament name hints
        if 'katowice' in name_lower:
            month, day = 3, 1
        elif 'cologne' in name_lower or 'gamescom' in name_lower:
            month, day = 8, 1
        elif 'oakland' in name_lower or 'san jose' in name_lower:
            month, day = 11, 15
        else:
            month, day = 6, 1  # Default for other IEM events
    elif 'kespa' in name_lower or 'demacia' in name_lower or 'rift rival' in name_lower:
        month, day = 6, 15  # Mid-year cups
    elif 'playoff' in name_lower:
        month, day = 8, 15  # Generic playoffs
    elif 'regional' in name_lower:
        month, day = 9, 15  # Generic regional finals
    else:
        # Default to mid-year if can't determine
        month, day = 6, 15

    # Base date (tournament start)
    base_date = datetime(year, month, day, 15, 0, 0)  # Start at 3 PM

    # Get tournament duration
    duration_days = estimate_tournament_duration(tournament_name)

    # Calculate which day this match falls on
    # Distribute matches evenly across tournament duration
    if total_matches <= 1:
        day_offset = 0
        match_of_day = 0
    else:
        # Spread matches across duration_days
        matches_per_day = max(1, total_matches / duration_days)
        day_offset = int(match_index / matches_per_day)
        match_of_day = int(match_index % matches_per_day)

    # Calculate match time (typically 3 PM, 6 PM, 9 PM for multiple matches per day)
    hour_offset = match_of_day * 3  # 3 hours between matches

    return base_date + timedelta(days=day_offset, hours=hour_offset)

def import_tournament(loader, db, team_resolver, name, url, stats, include_players=True):
    """
    Import all matches for a single tournament from MatchSchedule table

    Args:
        loader: LeaguepediaLoader instance
        db: DatabaseManager instance
        team_resolver: TeamResolver instance
        name: Tournament name
        url: Tournament URL (WITH SPACES!)
        stats: Statistics dictionary
        include_players: Whether to import player data (default True)

    Returns:
        bool: True if successful
    """
    print(f"\n{'='*80}")
    print(f"Importing: {name}")
    print(f"URL: {url}")
    print(f"{'='*80}")

    try:
        # Query matches from MatchSchedule (uses SPACES in OverviewPage)
        matches = loader._query_cargo(
            tables="MatchSchedule",
            fields="Team1,Team2,Team1Score,Team2Score,Winner,DateTime_UTC,BestOf,Phase,Round,Tab,OverviewPage,Patch,MatchId,UniqueMatch",
            where=f"OverviewPage='{url}'",
            limit=500,
            order_by="DateTime_UTC ASC"
        )

        if not matches:
            print(f"⚠️  No matches found for {name}")
            stats['tournaments_no_data'] += 1
            return False

        print(f"📥 Found {len(matches)} matches")
        stats['total_matches_found'] += len(matches)

        # Debug: Show sample of DateTime UTC values to understand the data
        if matches and len(matches) > 0:
            sample_dates = []
            for i, m in enumerate(matches[:5]):  # Check first 5 matches
                # API returns 'DateTime UTC' with space!
                dt = m.get('DateTime UTC', '') or m.get('DateTime_UTC', '')
                sample_dates.append(f"Match {i+1}: '{dt}'" if dt else f"Match {i+1}: EMPTY")
            print(f"📅 Sample dates: {', '.join(sample_dates)}")

        # Player data lookup - convert URL to underscores for ScoreboardPlayers
        players_by_match = {}
        if include_players:
            # ScoreboardPlayers uses UNDERSCORES in OverviewPage
            url_underscores = url.replace(' ', '_')

            try:
                players = loader._query_cargo(
                    tables="ScoreboardPlayers",
                    fields="UniqueMatch,Link,Role,Team",
                    where=f"OverviewPage='{url_underscores}'",
                    limit=500,
                    order_by="DateTime_UTC ASC"
                )

                # Group by UniqueMatch
                for player in players:
                    unique_match = player.get('UniqueMatch', '')
                    if unique_match:
                        if unique_match not in players_by_match:
                            players_by_match[unique_match] = []
                        players_by_match[unique_match].append(player)

                if players:
                    print(f"👥 Found {len(players)} player records")

            except Exception as e:
                print(f"⚠️  Could not fetch player data: {e}")

        # Insert matches
        matches_inserted = 0
        matches_failed = 0
        players_inserted = 0

        for match_index, match in enumerate(matches):
            team1_orig = match.get('Team1', '').strip()
            team2_orig = match.get('Team2', '').strip()

            if not team1_orig or not team2_orig:
                stats['matches_skipped'] += 1
                continue

            # Resolve team names
            # Note: API returns 'DateTime UTC' with space, not 'DateTime_UTC' with underscore!
            match_date = match.get('DateTime UTC', '') or match.get('DateTime_UTC', '')
            team1_resolved = team_resolver.resolve(team1_orig, match_date)
            team2_resolved = team_resolver.resolve(team2_orig, match_date)

            # Parse date
            date_is_estimated = False
            try:
                if match_date:
                    # Normalize single-digit hours to double-digit (8:00:00 -> 08:00:00)
                    # Split by space to handle "YYYY-MM-DD H:MM:SS AM/PM"
                    parts = match_date.split(' ')
                    if len(parts) == 3:  # Date, Time, AM/PM
                        date_part = parts[0]
                        time_part = parts[1]
                        ampm_part = parts[2]

                        # Normalize hour part (add leading zero if needed)
                        time_components = time_part.split(':')
                        if len(time_components) == 3:
                            hour, minute, second = time_components
                            if len(hour) == 1:  # Single digit hour
                                time_part = f"0{hour}:{minute}:{second}"
                            match_date = f"{date_part} {time_part} {ampm_part}"

                    # Try parsing with AM/PM format (Leaguepedia format)
                    try:
                        date_obj = datetime.strptime(match_date, "%Y-%m-%d %I:%M:%S %p")
                    except ValueError:
                        # Fallback to 24-hour format
                        try:
                            date_obj = datetime.strptime(match_date, "%Y-%m-%d %H:%M:%S")
                        except ValueError:
                            date_obj = None
                else:
                    date_obj = None
            except Exception as e:
                # Date parsing failed - will estimate instead
                date_obj = None

            # If no date, estimate from tournament name
            if not date_obj:
                # Pass match index and total matches for realistic distribution
                date_obj = estimate_date_from_tournament(name, match_index, len(matches))
                date_is_estimated = True
                stats['matches_with_estimated_dates'] += 1

            # Create external ID
            unique_match = match.get('UniqueMatch', '')
            match_id_field = match.get('MatchId', '')
            tab = match.get('Tab', '')
            external_id = unique_match or match_id_field or f"{url}_{tab}_{match_date}_{team1_orig}_{team2_orig}"

            # Insert match
            match_id = db.insert_match(
                team1_name=team1_resolved,
                team2_name=team2_resolved,
                team1_score=int(match.get('Team1Score', 0) or 0),
                team2_score=int(match.get('Team2Score', 0) or 0),
                date=date_obj,
                tournament_name=name,
                stage=match.get('Tab', '') or match.get('Phase', '') or match.get('Round', ''),
                patch=match.get('Patch', ''),
                external_id=external_id,
                source='leaguepedia'
            )

            if match_id:
                matches_inserted += 1
                stats['matches_inserted'] += 1

                # Insert players for this match
                if include_players and unique_match in players_by_match:
                    match_players = players_by_match[unique_match]

                    # Deduplicate by (player_name, role)
                    unique_players = {}
                    for player in match_players:
                        player_name = player.get('Link', '').strip()
                        role = player.get('Role', '').strip()
                        team_orig = player.get('Team', '').strip()

                        if not player_name:
                            continue

                        # Resolve player's team
                        team_resolved = team_resolver.resolve(team_orig, match_date)

                        key = (player_name, role)
                        if key not in unique_players:
                            unique_players[key] = (player_name, role, team_resolved)

                    # Insert unique players
                    for player_name, role, team_name in unique_players.values():
                        db.insert_match_player(
                            match_id=match_id,
                            player_name=player_name,
                            team_name=team_name,
                            role=role
                        )
                        players_inserted += 1
                        stats['players_inserted'] += 1
            else:
                matches_failed += 1
                stats['matches_failed'] += 1

        # Calculate per-tournament statistics
        skipped_this_tournament = stats['matches_skipped'] - stats.get('_last_skip_count', 0)
        estimated_this_tournament = stats['matches_with_estimated_dates'] - stats.get('_last_estimated_count', 0)

        print(f"✅ Inserted: {matches_inserted} matches, {players_inserted} players")
        if matches_failed > 0:
            print(f"⚠️  Failed: {matches_failed} matches")
        if skipped_this_tournament > 0:
            print(f"⏭️  Skipped: {skipped_this_tournament} matches (no date)")
        if estimated_this_tournament > 0:
            print(f"📅 Estimated dates: {estimated_this_tournament} matches")

        # Update counters for next tournament
        stats['_last_skip_count'] = stats['matches_skipped']
        stats['_last_estimated_count'] = stats['matches_with_estimated_dates']

        stats['tournaments_imported'] += 1
        return True

    except Exception as e:
        print(f"❌ ERROR importing {name}: {e}")
        import traceback
        traceback.print_exc()
        stats['tournaments_failed'] += 1
        return False

def main():
    """Main import function"""

    # Check for results file
    results_file = Path(__file__).parent / "minor_regions_discovery_results.json"
    if not results_file.exists():
        print(f"❌ Discovery results file not found: {results_file}")
        print(f"   Please run minor_regions_tournament_discovery_matchschedule.py first!")
        return 1

    # Load discovery results
    with open(results_file, 'r', encoding='utf-8') as f:
        results = json.load(f)

    tournaments = results.get('found_tournaments', [])
    if not tournaments:
        print("❌ No tournaments found in results file!")
        return 1

    print(f"📋 Loaded {len(tournaments)} tournaments from discovery results")

    # Initialize components
    bot_username = os.getenv("LEAGUEPEDIA_BOT_USERNAME", "Ekwo98@Elo")
    bot_password = os.getenv("LEAGUEPEDIA_BOT_PASSWORD")

    if not bot_password:
        print("❌ LEAGUEPEDIA_BOT_PASSWORD environment variable not set!")
        return 1

    print("\n🔧 Initializing components...")
    loader = LeaguepediaLoader(bot_username=bot_username, bot_password=bot_password)
    db = DatabaseManager()
    team_resolver = TeamResolver()

    # Statistics
    stats = {
        'tournaments_total': len(tournaments),
        'tournaments_imported': 0,
        'tournaments_failed': 0,
        'tournaments_no_data': 0,
        'total_matches_found': 0,
        'matches_inserted': 0,
        'matches_failed': 0,
        'matches_skipped': 0,
        'matches_with_estimated_dates': 0,
        'players_inserted': 0,
        '_last_skip_count': 0,  # Internal counter for per-tournament skip tracking
        '_last_estimated_count': 0  # Internal counter for per-tournament estimated dates tracking
    }

    # Import each tournament
    print(f"\n{'='*80}")
    print(f"STARTING IMPORT OF {len(tournaments)} TOURNAMENTS")
    print(f"{'='*80}")

    start_time = time.time()

    for i, tournament in enumerate(tournaments, 1):
        name = tournament['name']
        url = tournament['url']

        # Skip 2025 tournaments
        if '2025' in name:
            print(f"\n[{i}/{len(tournaments)}] {name} - ⏭️  SKIPPED (2025)")
            stats['tournaments_no_data'] += 1
            continue

        print(f"\n[{i}/{len(tournaments)}] {name}")

        import_tournament(
            loader=loader,
            db=db,
            team_resolver=team_resolver,
            name=name,
            url=url,
            stats=stats,
            include_players=False  # Disable player import to avoid API errors
        )

        # Progress update every 10 tournaments
        if i % 10 == 0:
            elapsed = time.time() - start_time
            avg_time = elapsed / i
            remaining = (len(tournaments) - i) * avg_time
            print(f"\n⏱️  Progress: {i}/{len(tournaments)} tournaments")
            print(f"   Elapsed: {elapsed/60:.1f}m, Estimated remaining: {remaining/60:.1f}m")

    # Final statistics
    elapsed_total = time.time() - start_time

    print(f"\n{'='*80}")
    print(f"IMPORT COMPLETE")
    print(f"{'='*80}")
    print(f"Time elapsed: {elapsed_total/60:.1f} minutes")
    print(f"\nTournaments:")
    print(f"  Total:       {stats['tournaments_total']}")
    print(f"  Imported:    {stats['tournaments_imported']}")
    print(f"  Failed:      {stats['tournaments_failed']}")
    print(f"  No data:     {stats['tournaments_no_data']}")
    print(f"\nMatches:")
    print(f"  Found:       {stats['total_matches_found']}")
    print(f"  Inserted:    {stats['matches_inserted']}")
    print(f"  Failed:      {stats['matches_failed']}")
    print(f"  Skipped:     {stats['matches_skipped']}")
    print(f"  Estimated dates: {stats['matches_with_estimated_dates']}")
    print(f"\nPlayers:")
    print(f"  Inserted:    {stats['players_inserted']}")

    # Save import log
    log_data = {
        'timestamp': datetime.now().isoformat(),
        'duration_seconds': elapsed_total,
        'statistics': stats
    }

    log_file = Path(__file__).parent / "import_log.json"
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(log_data, f, indent=2)

    print(f"\n📄 Import log saved to: {log_file}")

    return 0

if __name__ == "__main__":
    exit(main())
