# LOL ELO System - Command Quick Reference

**1-Page Cheat Sheet** | Schneller Überblick über alle wichtigen Befehle

---

## 📥 Data Import

```bash
# Google Sheets importieren
python scripts/import_google_sheets.py

# Leaguepedia Tier-1 Daten (2024 nur)
python scripts/import_tier1_data.py --test

# Historische Daten (2023-2024)
python scripts/import_tier1_data.py --start-year 2023 --end-year 2024

# Spezifische Ligen
python scripts/import_tier1_data.py --leagues LEC LCK --start-year 2024
```

---

## 🔍 Database Tools

```bash
# Interaktiver DB Viewer
python scripts/view_database.py

# Schnelle Statistiken
python scripts/view_database.py stats

# Matches anzeigen
python scripts/view_database.py matches 20

# Team suchen
python scripts/view_database.py team "T1"

# Spieler suchen
python scripts/view_database.py player "Faker"

# Duplikate diagnostizieren
python scripts/diagnose_duplicates.py
```

---

## 📊 Validation & Analysis

```bash
# MASTER: Kompletter Validation Report (empfohlen!)
python scripts/generate_validation_report.py

# Einzelne Analysen:
python validation/k_fold_validation.py --k 5
python validation/bootstrap_ci.py --iterations 1000
python analysis/feature_importance.py
python analysis/error_patterns.py
```

---

## 🎮 Streamlit Dashboard

```bash
# Dashboard starten
streamlit run dashboard/app.py

# Mit Port
streamlit run dashboard/app.py --server.port 8501
```

---

## 🧪 Testing & Development

```bash
# Team Name Resolver testen
python core/team_name_resolver.py

# Database Manager testen
python core/database.py

# Unified Data Loader testen
python core/unified_data_loader.py

# Tournament Context Variante testen
python variants/with_tournament_context.py
```

---

## 📈 ELO System Variants

```python
# In Python Code:
from variants.base_elo import BaseElo
from variants.with_scale_factor import ScaleFactorElo
from variants.with_dynamic_offsets import DynamicOffsetElo
from variants.with_tournament_context import TournamentContextElo

# Nutzen:
elo = DynamicOffsetElo(k_factor=24, use_scale_factors=True)
elo.update_ratings("T1", "Gen.G", 3, 2)
```

---

## 🔧 Häufige Workflows

### Nach API-Datenimport

```bash
# 1. Daten importieren
python scripts/import_tier1_data.py --start-year 2023

# 2. Validierung ausführen
python scripts/generate_validation_report.py

# 3. Report ansehen
cat reports/validation_report.md
```

### Team Name Probleme

```bash
# 1. Duplikate check
python scripts/diagnose_duplicates.py

# 2. Mappings prüfen
cat config/team_name_mappings.json

# 3. Resolver testen
python core/team_name_resolver.py
```

---

## 💾 Output Files

| Pfad | Inhalt |
|------|--------|
| `db/elo_system.db` | SQLite Datenbank |
| `reports/validation_report.md` | Master Validation Report |
| `validation/*.json` | K-Fold, Bootstrap Results |
| `analysis/*.json` | Feature Importance, Error Patterns |

---

## ⚡ Pro Tips

```bash
# Pipe output für bessere Lesbarkeit
python scripts/view_database.py stats | less

# JSON Resultate schön formatiert
cat validation/k_fold_results_k5.json | python -m json.tool

# Zeitstempel zu Logs
python scripts/import_tier1_data.py | ts

# Logs speichern
python scripts/generate_validation_report.py 2>&1 | tee validation.log
```

---

## 🆘 Troubleshooting

| Problem | Lösung |
|---------|--------|
| "No module 'pandas'" | `pip install pandas numpy streamlit` |
| "Rate limited" | Warte 30-60 Min |
| "Database locked" | Schließe andere DB-Connections |
| "No data found" | Importiere zuerst Daten |

---

**Vollständige Dokumentation:** `docs/COMMANDS_GUIDE.md`
**Wissenschaftliche Details:** `docs/SCIENTIFIC_BLOG.md`
