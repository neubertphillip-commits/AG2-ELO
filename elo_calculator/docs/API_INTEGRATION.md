# API Integration - Leaguepedia Datenimport

## 📋 Überblick

Dieses System integriert Daten aus zwei Quellen:
1. **Google Sheets** (manuell gepflegte Daten)
2. **Leaguepedia API** (automatischer Import von Tier-1-Ligen)

Die Daten werden in einer **SQLite-Datenbank** gespeichert mit automatischer **Duplikaterkennung**.

---

## 🏗️ Architektur

```
┌─────────────────────────────────────────────────┐
│           Leaguepedia API                       │
│        (Tier 1: LEC, LPL, LCK, LCS)            │
│        (International: Worlds, MSI)             │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│        LeaguepediaLoader                        │
│  - Automatischer Import                         │
│  - Rate Limiting                                │
│  - Fehlerbehandlung                             │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│         SQLite Datenbank                        │
│  ┌──────────┬──────────┬────────────────────┐  │
│  │ Matches  │ Teams    │ Players            │  │
│  │ Rosters  │ Ratings  │ Tournaments        │  │
│  └──────────┴──────────┴────────────────────┘  │
│                                                 │
│  ✓ Duplikaterkennung                           │
│  ✓ Normalisierte Daten                         │
│  ✓ Schnelle Queries                            │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│      Elo Berechnungssystem                      │
│  - Team Elo                                     │
│  - Player Elo                                   │
│  - Regionale Offsets                            │
└─────────────────────────────────────────────────┘
```

---

## 📊 Verfügbare Daten

### Aus Leaguepedia:

**Match-Daten:**
- Datum und Zeit
- Teams (Team1, Team2)
- Ergebnis (z.B. 3:1, 2:0)
- Turnier & Stage (Regular Season, Playoffs, etc.)
- Patch-Version
- Bo-Format (Bo1, Bo3, Bo5)

**Spieler-Daten (pro Match):**
- Spielername & Role
- Champion
- KDA (Kills, Deaths, Assists)
- Gold, CS
- Damage to Champions
- Vision Score
- Items

**Turnier-Daten:**
- Turniername
- Region (EU, CN, KR, NA, International)
- Jahr & Split
- Tier (1 für Top-Ligen)

---

## 🚀 Verwendung

### 1. Google Sheets Daten importieren

Importiert bestehende Daten aus Google Sheets in die Datenbank:

```bash
python3 scripts/import_google_sheets.py
```

**Ausgabe:**
```
==============================================================
Google Sheets → SQLite Import
==============================================================

📊 Loading Google Sheets data...
✓ Loaded 1081 matches from Google Sheets
✓ Found 45 unique teams

💾 Importing into SQLite...
  Progress: 100/1081
  Progress: 200/1081
  ...

==============================================================
Import Summary
==============================================================
✓ Imported: 1081 matches
⊘ Skipped (duplicates): 0 matches

📊 Database Stats:
  Total Matches: 1081
  Total Teams: 45
  Date Range: 2024-01-10 to 2024-11-03
  By Source:
    - google_sheets: 1081
```

### 2. Leaguepedia Tier-1 Daten importieren

Importiert historische Daten von Tier-1-Ligen:

```bash
# Alle Tier-1 Ligen ab 2013
python3 scripts/import_tier1_data.py

# Nur bestimmte Jahre
python3 scripts/import_tier1_data.py --start-year 2020 --end-year 2024

# Nur bestimmte Ligen
python3 scripts/import_tier1_data.py --leagues LEC LCK

# Ohne Spielerdaten (schneller)
python3 scripts/import_tier1_data.py --no-players

# Test-Modus (nur 2024)
python3 scripts/import_tier1_data.py --test
```

**Ausgabe:**
```
======================================================================
Tier 1 League Data Import: 2023-2024
======================================================================

Leagues: LEC, LPL, LCK, LCS, WORLDS, MSI
Player Data: Yes
Time Range: 2023 - 2024

======================================================================
📥 Importing LEC
======================================================================

  📅 LEC 2023 Spring

🏆 Importing LEC 2023 Spring

📥 Fetching matches from: LEC/2023 Season/Spring Season
  Found 45 games in API
  Aggregated into 45 matches
  ✓ Imported: 45 matches

📥 Fetching matches from: LEC/2023 Playoffs/Spring Playoffs
  Found 12 games in API
  Aggregated into 8 matches
  ✓ Imported: 8 matches

  ✓ 2023 Total: 53 matches

...

======================================================================
IMPORT COMPLETE
======================================================================

📊 Import Statistics:
  Total Matches Imported: 847
  Duration: 0:15:23

  By League:
    LEC       :   156 matches
    LPL       :   289 matches
    LCK       :   201 matches
    LCS       :   143 matches
    WORLDS    :    42 matches
    MSI       :    16 matches

📦 Final Database Stats:
  Total Matches: 1928
  Total Teams: 127
  Total Players: 543
  Total Tournaments: 28
  Date Range: 2023-01-09 to 2024-11-02

  By Source:
    google_sheets  :  1081 matches
    leaguepedia    :   847 matches
```

---

## 🔧 Programmier-Interface

### DatabaseManager verwenden

```python
from core.database import DatabaseManager

# Datenbank öffnen
db = DatabaseManager()

# Match einfügen
match_id = db.insert_match(
    team1_name="T1",
    team2_name="Gen.G",
    team1_score=3,
    team2_score=2,
    date=datetime(2024, 9, 1),
    tournament_name="LCK 2024 Summer Playoffs",
    stage="Finals",
    patch="14.17",
    region="KR",
    source="leaguepedia"
)

# Spielerdaten hinzufügen
if match_id:
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

# Alle Matches abfragen
matches = db.get_all_matches(limit=100)

# Statistiken
stats = db.get_stats()
print(f"Total matches: {stats['total_matches']}")

# Schließen
db.close()
```

### LeaguepediaLoader verwenden

```python
from core.leaguepedia_loader import LeaguepediaLoader

# Initialisieren
loader = LeaguepediaLoader()

# Einzelnes Turnier importieren
loader.import_league_season(
    league='LEC',
    year=2024,
    split='Summer',
    include_playoffs=True,
    include_players=True
)

# Alle Tier-1 Ligen importieren
stats = loader.import_all_tier1(
    start_year=2020,
    end_year=2024,
    include_players=True
)

# Schließen
loader.close()
```

---

## 📋 Tier-1 Ligen Konfiguration

| Liga | Region | Start Jahr | Splits |
|------|--------|------------|--------|
| **LEC** | EU | 2013 | Spring, Summer |
| **LPL** | CN | 2013 | Spring, Summer |
| **LCK** | KR | 2013 | Spring, Summer |
| **LCS** | NA | 2013 | Spring, Summer |
| **Worlds** | International | 2013 | Main Event |
| **MSI** | International | 2015 | Main Event |

**Hinweise:**
- EU LCS → LEC (2019)
- NA LCS → LCS (2018)
- Champions → LCK (Korea)

---

## ⚙️ Technische Details

### Duplikaterkennung

Die Datenbank verhindert automatisch Duplikate durch:

1. **External ID Check**: Leaguepedia GameId
2. **Teams + Date Check**: Für Google Sheets Daten
3. **Unique Constraints**: In der Datenbank

### Rate Limiting

Leaguepedia API:
- **Limit**: 500 Ergebnisse pro Anfrage
- **Delay**: 1.5 Sekunden zwischen Requests
- **Empfehlung**: Große Imports außerhalb der Spitzenzeiten

### Datenbank Schema

```sql
-- Teams
CREATE TABLE teams (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,
    region TEXT,
    current_elo REAL DEFAULT 1500.0
);

-- Matches
CREATE TABLE matches (
    id INTEGER PRIMARY KEY,
    external_id TEXT UNIQUE,
    date TIMESTAMP,
    team1_id INTEGER,
    team2_id INTEGER,
    team1_score INTEGER,
    team2_score INTEGER,
    winner_id INTEGER,
    tournament_id INTEGER,
    stage TEXT,
    patch TEXT,
    bo_format TEXT,
    source TEXT,
    FOREIGN KEY (team1_id) REFERENCES teams(id),
    FOREIGN KEY (team2_id) REFERENCES teams(id)
);

-- Players
CREATE TABLE players (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,
    current_elo REAL DEFAULT 1500.0,
    role TEXT
);

-- Match Players (wer hat in welchem Match gespielt)
CREATE TABLE match_players (
    id INTEGER PRIMARY KEY,
    match_id INTEGER,
    player_id INTEGER,
    team_id INTEGER,
    role TEXT,
    champion TEXT,
    kills INTEGER,
    deaths INTEGER,
    assists INTEGER,
    gold INTEGER,
    cs INTEGER,
    damage_to_champions INTEGER,
    vision_score INTEGER,
    won BOOLEAN,
    FOREIGN KEY (match_id) REFERENCES matches(id),
    FOREIGN KEY (player_id) REFERENCES players(id)
);

-- Tournaments
CREATE TABLE tournaments (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,
    region TEXT,
    year INTEGER,
    split TEXT,
    tier INTEGER DEFAULT 1
);
```

---

## 🔍 Fehlerbehebung

### Problem: "Rate limited"
**Lösung**: Warten Sie 30-60 Sekunden zwischen großen Imports

### Problem: "No games found"
**Lösung**:
- Überprüfen Sie den Turniernamen (Format: "LEC/2024 Season/Summer Season")
- Prüfen Sie, ob das Turnier auf Leaguepedia existiert

### Problem: "Module not found"
**Lösung**: Script aus dem Projekt-Root ausführen:
```bash
python3 -m scripts.import_tier1_data
```

---

## 📈 Nächste Schritte

1. ✅ Datenbank erstellt
2. ✅ Leaguepedia Loader implementiert
3. ✅ Google Sheets Import
4. ✅ Duplikaterkennung
5. ⏳ Spieler-Elo System entwickeln
6. ⏳ Elo-Berechnungen auf neue Daten anwenden
7. ⏳ Export nach Google Sheets für Visualisierung
