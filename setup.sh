#!/bin/bash
# AG2 Agent System - Setup Script for Replit
# Run: bash setup.sh

set -e

echo "========================================="
echo "  AG2 Agent System - Setup"
echo "  LOL ELO Calculator"
echo "========================================="
echo ""

# Install dependencies
echo "[1/3] Installing Python dependencies..."
pip install -q ag2[openai,captainagent] python-dotenv
pip install -q pandas numpy streamlit plotly pytest python-dateutil
echo "  Done."

# Check API key
echo ""
echo "[2/3] Checking configuration..."
if [ -z "$OPENAI_API_KEY" ]; then
    echo "  [!] OPENAI_API_KEY not set."
    echo "  Add it in Replit: Tools > Secrets > OPENAI_API_KEY"
else
    echo "  [OK] OPENAI_API_KEY is configured."
fi

# Verify installation
echo ""
echo "[3/3] Verifying installation..."
python -c "
import autogen
print(f'  [OK] AG2/AutoGen v{autogen.__version__}')
try:
    from autogen.agentchat.contrib.captainagent import CaptainAgent
    print('  [OK] CaptainAgent available')
except ImportError:
    print('  [!!] CaptainAgent not available')
"

echo ""
echo "========================================="
echo "  Setup complete!"
echo ""
echo "  Run agents:    python agents/main.py"
echo "  Web UI:        streamlit run agents/web_ui.py"
echo "  Dashboard:     streamlit run elo_calculator/dashboard/app.py"
echo "  Tests:         python -m pytest elo_calculator/tests/ -v"
echo "  Env check:     python agents/main.py --check"
echo "========================================="
