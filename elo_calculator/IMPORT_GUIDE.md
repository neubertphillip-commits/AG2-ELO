# Leaguepedia Data Import Guide

## Quick Start

### 1. Status überprüfen
```bash
python scripts/check_import_status.py
```

Zeigt:
- Anzahl Matches in DB
- Matches pro Jahr
- Matches pro Turnier
- Teams
- Zeitraum

### 2. Vollständigen Import starten

```bash
# Stelle sicher, dass Bot-Credentials gesetzt sind
export LEAGUEPEDIA_BOT_USERNAME="Ekwo98@Elo"
export LEAGUEPEDIA_BOT_PASSWORD="n7d9rsiccg7hujkg2hvtnglg4h93480r"

# Starte den Import (dauert ca. 1-2 Stunden)
python scripts/import_all_historical_data.py
```

Das importiert:
- **LEC** (2013-2024): Spring, Summer + Playoffs
- **LPL** (2013-2024): Spring, Summer + Playoffs
- **LCK** (2013-2024): Spring, Summer + Playoffs
- **LCS** (2013-2024): Spring, Summer + Playoffs
- **MSI** (2015-2024): Main Event
- **Worlds** (2013-2024): Main Event

### 3. Import-Fortschritt überwachen

**In einem anderen Terminal:**
```bash
# Zeige Anzahl Matches (aktualisiert sich live)
watch -n 30 'python scripts/check_import_status.py | head -20'
```

**Oder manuell:**
```bash
python3 -c "
from core.database import DatabaseManager
db = DatabaseManager()
cursor = db.conn.cursor()
cursor.execute('SELECT COUNT(*) FROM matches')
print(f'Matches in DB: {cursor.fetchone()[0]}')
"
```

## Aktueller Status

```
✓ 528 Matches aus 2024 importiert
✓ Bot-Authentifizierung funktioniert
✓ API Tab-Field Bug behoben
✓ Rate-Limit: 2s (schnell aber sicher)
```

## Geschätzte Zeiten

Mit **2s Rate-Limit**:
- Pro Turnier: ~5-10 Minuten (je nach Anzahl Spiele)
- LEC 2013-2024: ~30 Minuten
- Alle 4 Ligen 2013-2024: ~2 Stunden
- MSI + Worlds: +30 Minuten
- **Gesamt: ~2.5 Stunden für alles**

## Troubleshooting

### "Rate limited"
Auch mit Bot-Credentials kann es passieren. Das Script macht automatisch 3 Retries mit exponential backoff (2s, 4s, 8s).

### "MWException"
Das sollte nicht mehr passieren (Tab-Field wurde entfernt). Falls doch:
```bash
# Prüfe ob neuester Code
git pull
```

### Import unterbrechen und fortsetzen
Der Import ist **idempotent** - Duplikate werden automatisch übersprungen. Du kannst jederzeit abbrechen (Ctrl+C) und später weitermachen.

### Einzelne Turniere importieren

```python
from core.leaguepedia_loader import LeaguepediaLoader

loader = LeaguepediaLoader()

# Beispiel: Nur LEC 2023
imported = loader.import_league_season(
    league='LEC',
    year=2023,
    split='Summer',
    include_playoffs=True,
    include_players=False
)
```

## Nach dem Import

### Validierung laufen lassen
```bash
python scripts/generate_validation_report.py
```

### Dashboard starten
```bash
streamlit run dashboard/app.py
```

### ELO-Berechnungen durchführen
```bash
python variants/with_dynamic_offsets.py
```

## Nächste Schritte

1. ✓ Import fertig
2. → Validierung durchführen
3. → Offset-Berechnung mit vollständigen Daten testen
4. → Dashboard mit historischen Daten analysieren
5. → Excel-Vergleich mit größerem Datensatz
