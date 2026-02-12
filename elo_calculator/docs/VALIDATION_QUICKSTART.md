# Validation Suite - Quick Start Guide

## 🎯 Overview

Diese Validation Suite ist **bereit für API-Daten** und analysiert das ELO-System umfassend, sobald Sie historische Daten importiert haben.

## 📋 Prerequisites

```bash
# 1. Importieren Sie Daten
python scripts/import_google_sheets.py        # Bestehende Daten
python scripts/import_tier1_data.py --test    # Leaguepedia 2024 (sobald API bereit)

# ODER kompletter Import (2023-2024):
python scripts/import_tier1_data.py --start-year 2023 --end-year 2024
```

---

## 🚀 Quick Start - Kompletter Report

**Ein Befehl für alle Analysen:**

```bash
python scripts/generate_validation_report.py
```

**Output:**
- `reports/validation_report.md` - Vollständiger Markdown-Report
- Enthält: K-Fold CV, Bootstrap CI, Feature Importance, Error Patterns

**Dauer:** ~5-10 Minuten

---

## 📊 Einzelne Analysen

### 1. K-Fold Cross-Validation

**Testet Robustheit über Zeit:**

```bash
python validation/k_fold_validation.py --k 5
```

**Output:**
```
Mean Accuracy: 71.38% ± 1.2%
95% CI: [70.18%, 72.58%]
```

**Interpretation:**
- Std < 2%: Sehr robust ✅
- Std < 5%: Robust ✅
- Std > 10%: Overfitting-Gefahr ⚠️

---

### 2. Bootstrap Confidence Intervals

**Quantifiziert statistische Unsicherheit:**

```bash
python validation/bootstrap_ci.py --iterations 1000
```

**Output:**
```
Overall Accuracy: 71.38%
95% CI: [69.5%, 73.2%]
Margin of Error: ±1.85%

Cross-Regional Accuracy: 60.87%
95% CI: [52.3%, 68.4%]
Margin of Error: ±8.05%
```

**Interpretation:**
- Samples < 50: Zu wenig Daten ⚠️
- Samples < 100: Moderate Daten 🟡
- Samples > 150: Gut ✅

---

### 3. Feature Importance (Ablation Study)

**Zeigt Beitrag jedes Features:**

```bash
python analysis/feature_importance.py
```

**Output:**
```
| Configuration           | Test Acc | vs Baseline |
|-------------------------|----------|-------------|
| K24 + Scale + Offsets   | 71.38%   | +1.53%      |
| K24 + Scale             | 70.46%   | +0.61%      |
| Optimized K (K=24)      | 69.85%   | 0.00%       |
| Baseline (K=20)         | 69.85%   | -            |
```

**Interpretation:**
- Zeigt welche Features am meisten bringen
- Guide für weitere Optimierungen

---

### 4. Error Pattern Analysis

**Identifiziert Schwachstellen:**

```bash
python analysis/error_patterns.py
```

**Output:**
```
Accuracy by ELO Difference:
  Toss-up (<25):    62.5%
  Close (25-50):    68.3%
  Moderate (50-100): 72.4%
  Stomp (>150):     85.2%
```

**Interpretation:**
- Wo macht das System Fehler?
- Welche Matchups sind schwierig?
- Tournament-spezifische Probleme?

---

### 5. Tournament Context Variante (NEU)

**Test der Tournament-Context K-Faktoren:**

```bash
# Test standalone
python variants/with_tournament_context.py

# In Feature Importance integriert
python analysis/feature_importance.py
```

**Theorie:**
- Worlds/MSI: K=32 (höchste Stakes)
- Playoffs: K=28
- Regular Season: K=24

**Erwartete Verbesserung:** +0.3-0.8pp

---

## 🔍 Database Tools

### Datenbank ansehen

```bash
# Interaktiv
python scripts/view_database.py

# Command line
python scripts/view_database.py stats
python scripts/view_database.py matches 20
python scripts/view_database.py teams 50
python scripts/view_database.py team "T1"
python scripts/view_database.py player "Faker"
```

### Duplikate diagnostizieren

```bash
python scripts/diagnose_duplicates.py
```

**Zeigt:**
- Welche Matches als Duplikate erkannt wurden
- Warum sie Duplikate sind
- Ob es echte Duplikate oder False Positives sind

---

## 📈 Workflow: Nach API-Import

**Sobald Sie 2023-2024 Daten importiert haben:**

```bash
# 1. Kompletten Report generieren
python scripts/generate_validation_report.py

# 2. Review Report
cat reports/validation_report.md

# 3. Wenn gut: Commit results
git add reports/validation_report.md
git commit -m "Add validation report with 2023-2024 data"
```

**Erwartete Results (mit 2023-2024 Daten):**

```
K-Fold CV:
  Mean: 71-72%
  Std: <3% (robust)

Bootstrap CI:
  Cross-Regional Samples: 150-200
  Margin of Error: ±7-8%

Feature Importance:
  Tournament Context: +0.5-0.8pp
  Regional Offsets: +3-4pp (now validated!)

Error Patterns:
  Stomps: 80-85% accuracy
  Toss-ups: 60-65% accuracy
```

---

## 🎯 Decision Criteria

### Regional Offsets behalten?

```python
if cross_regional_samples > 100:
    if cross_regional_accuracy > 58%:
        print("✅ Keep Regional Offsets")
    else:
        print("❌ Remove Regional Offsets (lucky)")
else:
    print("⚠️ Need more data")
```

### Tournament Context hinzufügen?

```python
if improvement > 0.5 and overfitting < 5:
    print("✅ Add Tournament Context")
else:
    print("⊘ Skip Tournament Context")
```

---

## 📁 Output Files

```
reports/
  └── validation_report.md          # Master report

validation/
  ├── k_fold_results_k5.json        # K-Fold results
  └── bootstrap_ci_results.json     # Bootstrap CI

analysis/
  ├── feature_importance_results.json
  └── error_patterns_results.json
```

---

## 🔧 Troubleshooting

### "No module named 'pandas'"

```bash
pip install pandas numpy
```

### "No data found"

```bash
# Check database
python scripts/view_database.py stats

# If empty, import data
python scripts/import_google_sheets.py
```

### "Rate limited"

Warten Sie 30-60 Minuten vor erneutem API-Import.

### Reports sehen komisch aus

Öffnen Sie `.md` Dateien in einem Markdown-Viewer oder auf GitHub.

---

## 💡 Tips

1. **Starten Sie mit dem Master Report** - gibt Überblick über alles
2. **Drill down** in einzelne Analysen bei Interesse
3. **Speichern Sie Reports** nach jedem Major Change
4. **Vergleichen Sie Reports** über Zeit

---

## 🚀 Ready to Go!

Sobald die API-Daten importiert sind, einfach:

```bash
python scripts/generate_validation_report.py
```

Und Sie haben eine vollständige Validierung Ihres Systems! 🎉
