# LOL ELO System - Complete Command Guide

**Comprehensive Tutorial & Reference** | Von ersten Schritten bis Advanced Analytics

---

## 📋 Table of Contents

1. [Getting Started](#getting-started)
2. [Daily Operations](#daily-operations)
3. [Data Import Workflows](#data-import-workflows)
4. [Database Management](#database-management)
5. [Validation & Analysis](#validation--analysis)
6. [Dashboard Usage](#dashboard-usage)
7. [Advanced Tools](#advanced-tools)
8. [Troubleshooting](#troubleshooting)
9. [Best Practices](#best-practices)

---

## Getting Started

### Prerequisites

```bash
# Install dependencies
pip install pandas numpy streamlit requests

# Verify installation
python -c "import pandas, numpy, streamlit; print('✓ All dependencies installed')"
```

### Initial Setup

```bash
# 1. Clone repository
git clone <your-repo-url>
cd lol-elo-system

# 2. Verify directory structure
ls core/         # Should show database.py, elo_calculator.py, etc.
ls config/       # Should show team_name_mappings.json
ls db/           # Database will be created here

# 3. Test core components
python core/database.py              # Test database manager
python core/team_name_resolver.py   # Test team name mapping
```

### Your First Import

```bash
# Import Google Sheets data (if you have existing data)
python scripts/import_google_sheets.py

# Quick database check
python scripts/view_database.py stats
```

**Expected Output:**
```
Database Statistics:
  Total Matches: 42
  Total Teams: 12
  Total Players: 60
  Date Range: 2024-01-15 to 2024-03-20
```

---

## Daily Operations

### Quick Health Check

```bash
# One-liner to check system health
python scripts/view_database.py stats && echo "✓ Database OK"
```

### View Recent Matches

```bash
# Last 10 matches
python scripts/view_database.py matches 10

# Last 50 matches
python scripts/view_database.py matches 50

# All matches from specific team
python scripts/view_database.py team "T1"
```

### Search Players

```bash
# Find specific player
python scripts/view_database.py player "Faker"

# Output shows:
# - Player statistics
# - Recent match history
# - Performance metrics
```

### Team Lookup

```bash
# Search team by name
python scripts/view_database.py team "Gen.G"

# Also works with aliases:
python scripts/view_database.py team "GenG"
python scripts/view_database.py team "Samsung Galaxy"  # Historical name
```

---

## Data Import Workflows

### Import from Leaguepedia API

#### Test Run (Recommended First)

```bash
# Import small test dataset (2024 only, limited matches)
python scripts/import_tier1_data.py --test
```

**What happens:**
- Imports ~50-100 recent matches
- Tests API connectivity
- Validates data structure
- Takes ~2-5 minutes

#### Import Specific Year

```bash
# Import all 2024 data
python scripts/import_tier1_data.py --start-year 2024 --end-year 2024
```

#### Import Historical Data

```bash
# Import 2023-2024 (recommended for initial dataset)
python scripts/import_tier1_data.py --start-year 2023 --end-year 2024

# Import complete history (2013-2024) - VERY SLOW!
python scripts/import_tier1_data.py --start-year 2013 --end-year 2024
```

**⚠️ Warning:** Complete history takes 2-4 hours due to rate limiting!

#### Import Specific Leagues

```bash
# Only LEC and LCK
python scripts/import_tier1_data.py --leagues LEC LCK --start-year 2024

# Only Worlds and MSI (international tournaments)
python scripts/import_tier1_data.py --leagues Worlds MSI --start-year 2023
```

**Available Leagues:**
- `LEC` - Europe
- `LCS` - North America
- `LCK` - Korea
- `LPL` - China
- `Worlds` - World Championship
- `MSI` - Mid-Season Invitational

#### Save Import Logs

```bash
# Save output to file for later review
python scripts/import_tier1_data.py --start-year 2024 2>&1 | tee import_2024.log

# Check log later
cat import_2024.log
```

---

## Database Management

### Interactive Database Viewer

```bash
# Launch interactive mode
python scripts/view_database.py

# Then use commands:
# - stats: Show statistics
# - matches <N>: Show N recent matches
# - team <name>: Search team
# - player <name>: Search player
# - sql <query>: Run custom SQL
# - help: Show help
# - exit: Quit
```

### Diagnose Data Quality

```bash
# Check for duplicates
python scripts/diagnose_duplicates.py

# Output shows:
# - Duplicate matches (same teams + date)
# - Duplicate external IDs
# - Recommendations for cleanup
```

**Example Output:**
```
Duplicate Analysis Report

1. Duplicates by (team1, team2, date):
   Found 3 duplicate groups

   Group 1: T1 vs Gen.G on 2024-03-15
   - Match IDs: 123, 124
   - Action: Keep most recent, remove ID 123

2. Duplicates by external_id:
   Found 0 duplicates ✓

Recommendation: Run manual cleanup for 3 matches
```

### Custom SQL Queries

```bash
# Interactive SQL mode
python scripts/view_database.py

> sql SELECT COUNT(*) FROM matches WHERE tournament LIKE '%Worlds%'
> sql SELECT team_name, COUNT(*) as games FROM teams JOIN matches ...
```

### Export Data

```python
# In Python:
from core.unified_data_loader import UnifiedDataLoader

with UnifiedDataLoader() as loader:
    df = loader.load_matches(source='database')
    df.to_csv('export_matches.csv', index=False)
    print(f"✓ Exported {len(df)} matches to export_matches.csv")
```

---

## Validation & Analysis

### Master Validation Report (Recommended!)

```bash
# Generate comprehensive validation report
python scripts/generate_validation_report.py

# View report
cat reports/validation_report.md
```

**Report includes:**
- K-Fold cross-validation results
- Bootstrap confidence intervals
- Feature importance analysis
- Error pattern analysis
- Recommendations

**Time:** ~2-5 minutes depending on dataset size

### Individual Validation Components

#### K-Fold Cross-Validation

```bash
# 5-fold validation (default, recommended)
python validation/k_fold_validation.py --k 5

# 10-fold validation (more thorough, slower)
python validation/k_fold_validation.py --k 10

# View results
cat validation/k_fold_results_k5.json | python -m json.tool
```

**Output:**
```json
{
  "k": 5,
  "accuracy": 0.6823,
  "margin_of_error": 0.0156,
  "fold_accuracies": [0.679, 0.685, 0.681, 0.683, 0.684],
  "std_dev": 0.0023
}
```

#### Bootstrap Confidence Intervals

```bash
# 1000 iterations (default)
python validation/bootstrap_ci.py --iterations 1000

# 10000 iterations (publication-quality)
python validation/bootstrap_ci.py --iterations 10000
```

**Interpretation:**
- **Accuracy:** Mean prediction accuracy
- **95% CI:** Confidence interval bounds
- **Margin of Error:** Maximum expected deviation

#### Feature Importance

```bash
# Ablation study
python analysis/feature_importance.py

# View results
cat analysis/feature_importance.json | python -m json.tool
```

**Shows:**
- Baseline accuracy (default K-factor)
- Impact of scale factors
- Impact of regional offsets
- Impact of tournament context

#### Error Pattern Analysis

```bash
# Analyze where model fails
python analysis/error_patterns.py

# View results
cat analysis/error_patterns.json | python -m json.tool
```

**Reveals:**
- Accuracy by ELO difference (toss-up vs stomp)
- Accuracy by tournament type
- Accuracy by match closeness
- Common failure modes

---

## Dashboard Usage

### Launch Dashboard

```bash
# Start Streamlit dashboard
streamlit run dashboard/app.py

# Custom port
streamlit run dashboard/app.py --server.port 8501

# Open automatically in browser
streamlit run dashboard/app.py --server.headless false
```

**Access:** Open browser to `http://localhost:8501`

### Dashboard Pages

1. **🏠 Home**
   - System overview
   - Quick statistics
   - Recent matches
   - Status indicators

2. **📊 Rankings**
   - Current team rankings
   - Player leaderboards
   - Historical ELO charts
   - Regional comparisons

3. **🎯 Match Predictor**
   - Predict match outcomes
   - Win probability calculations
   - What-if scenarios
   - Tournament simulation

4. **📈 Validation Suite**
   - Run validation tests
   - View validation results
   - Interactive charts
   - Performance metrics

5. **🔍 Analysis Tools**
   - Feature importance
   - Error patterns
   - Custom analysis
   - Data exploration

6. **📥 Data Management**
   - Import data
   - View database stats
   - Diagnose issues
   - Export data

7. **⚙️ Advanced Tools**
   - Team name mapping
   - Custom SQL queries
   - Batch operations
   - System configuration

8. **📚 Documentation**
   - Inline help
   - Command reference
   - Scientific documentation
   - API documentation

---

## Advanced Tools

### Test ELO Variants

```bash
# Test base ELO
python variants/base_elo.py

# Test with scale factors
python variants/with_scale_factor.py

# Test with dynamic offsets
python variants/with_dynamic_offsets.py

# Test with tournament context
python variants/with_tournament_context.py
```

### Team Name Resolver

```bash
# Test team name resolution
python core/team_name_resolver.py

# Add new mapping (programmatically):
```

```python
from core.team_name_resolver import TeamNameResolver

resolver = TeamNameResolver()
resolver.add_mapping(
    canonical="New Team Name",
    aliases=["NTN", "New Team", "NewTeamGaming"],
    region="EU",
    notes="Joined LEC in 2024"
)
resolver.save_mappings()
```

### Unified Data Loader

```bash
# Test unified loader
python core/unified_data_loader.py

# Use in scripts:
```

```python
from core.unified_data_loader import UnifiedDataLoader

# Automatic source selection
with UnifiedDataLoader() as loader:
    df = loader.load_matches(source='auto')  # Prefers database

# Explicit source
with UnifiedDataLoader() as loader:
    df = loader.load_matches(source='database')
    # or source='sheets'
```

---

## Troubleshooting

### Common Issues

#### "No module named 'pandas'"

```bash
# Solution: Install dependencies
pip install pandas numpy streamlit requests
```

#### "Database is locked"

```bash
# Cause: Another process accessing database
# Solution 1: Close all Python processes
pkill python

# Solution 2: Check for hung processes
ps aux | grep python

# Solution 3: Restart and try again
```

#### "Rate limited" from API

```bash
# Cause: Too many API requests
# Solution: Wait 30-60 minutes, then retry

# Prevention: Use --test flag first
python scripts/import_tier1_data.py --test
```

#### "No data found" errors

```bash
# Check database has data
python scripts/view_database.py stats

# If empty, import data first
python scripts/import_google_sheets.py
# OR
python scripts/import_tier1_data.py --test
```

#### "Team name not found"

```bash
# Check team name mappings
cat config/team_name_mappings.json

# Test resolver
python core/team_name_resolver.py

# Add mapping if needed (edit config/team_name_mappings.json)
```

### Debug Mode

```bash
# Run with Python verbose mode
python -v scripts/import_tier1_data.py --test

# Enable SQL echo (edit core/database.py temporarily)
# Change: self.conn = sqlite3.connect(db_path)
# To: self.conn = sqlite3.connect(db_path, isolation_level=None)
```

### Check File Integrity

```bash
# Verify key files exist
ls core/database.py
ls core/leaguepedia_loader.py
ls config/team_name_mappings.json
ls db/elo_system.db

# Check database is valid SQLite
sqlite3 db/elo_system.db "SELECT COUNT(*) FROM matches"
```

---

## Best Practices

### Data Import

1. **Always start with --test flag**
   ```bash
   python scripts/import_tier1_data.py --test
   ```

2. **Import recent data first** (2023-2024) before historical

3. **Save logs for large imports**
   ```bash
   python scripts/import_tier1_data.py --start-year 2023 2>&1 | tee import.log
   ```

4. **Check for duplicates after import**
   ```bash
   python scripts/diagnose_duplicates.py
   ```

### Validation

1. **Run master validation report after major changes**
   ```bash
   python scripts/generate_validation_report.py
   ```

2. **Use K=5 for quick validation, K=10 for thorough**

3. **Run bootstrap with 1000+ iterations for confidence**

### Performance

1. **Use unified data loader for automatic caching**

2. **Close database connections properly**
   ```python
   db = DatabaseManager()
   try:
       # ... use db ...
   finally:
       db.close()
   ```

3. **Build indices for faster queries** (already built in schema)

### Team Name Mapping

1. **Test new mappings before import**
   ```bash
   python core/team_name_resolver.py
   ```

2. **Add fuzzy matches to config if confidence < 95%**

3. **Review warnings during import** for unmapped teams

### Dashboard

1. **Use cached data when possible** (sidebar stats)

2. **Limit query results** for large datasets

3. **Export analysis results** for external use

---

## Quick Reference Card

```bash
# ESSENTIAL COMMANDS

# Import test data
python scripts/import_tier1_data.py --test

# View database
python scripts/view_database.py stats

# Validation report
python scripts/generate_validation_report.py

# Launch dashboard
streamlit run dashboard/app.py

# Check duplicates
python scripts/diagnose_duplicates.py

# Test team names
python core/team_name_resolver.py
```

---

## Next Steps

After completing this guide, explore:

1. **Scientific Documentation:** `docs/SCIENTIFIC_BLOG.md`
   - Mathematical foundations
   - Design decisions
   - Alternative approaches

2. **API Integration:** `docs/API_INTEGRATION.md`
   - Leaguepedia Cargo API
   - Best practices
   - Rate limiting

3. **Quick Reference:** `docs/COMMANDS_QUICKREF.md`
   - 1-page cheat sheet
   - Essential commands
   - Common workflows

---

**Questions? Issues?**

1. Check troubleshooting section above
2. Review error messages carefully
3. Test with smaller datasets (`--test` flag)
4. Check GitHub issues for similar problems

**Happy analyzing! 🎮📊**
