# LOL ELO System

League of Legends ELO Rating System with Regional Offsets

## Features
- Multiple ELO calculation variants
- Temporal validation framework
- Regional offset system
- Streamlit dashboard

## Setup
```bash
pip install -r requirements.txt
```

## Project Structure
- `core/` - Shared utilities (data loading, validation, metrics)
- `variants/` - Different ELO implementations (baseline, with form, etc.)
- `validation/` - Testing frameworks (temporal split, cross-validation)
- `dashboard/` - Streamlit visualization

## Status
🚧 In active development - Migration from Google Apps Script to Python