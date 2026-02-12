"""
LOL ELO System - Comprehensive Streamlit Dashboard
Multi-page app with all features, visualizations, and command integration
"""

import streamlit as st
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure page
st.set_page_config(
    page_title="LOL ELO System",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #666;
        text-align: center;
        padding-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .success-box {
        padding: 1rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 0.25rem;
        color: #155724;
    }
    .warning-box {
        padding: 1rem;
        background-color: #fff3cd;
        border: 1px solid #ffeeba;
        border-radius: 0.25rem;
        color: #856404;
    }
    .error-box {
        padding: 1rem;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 0.25rem;
        color: #721c24;
    }
    </style>
""", unsafe_allow_html=True)

# Sidebar navigation
st.sidebar.title("🎮 LOL ELO System")
st.sidebar.markdown("---")

# Page selection
page = st.sidebar.radio(
    "Navigation",
    [
        "🏠 Home",
        "📊 Rankings",
        "🎯 Match Predictor",
        "🌍 Regional Offsets",
        "📈 Validation Suite",
        "🔍 Analysis Tools",
        "📥 Data Management",
        "⚙️ Advanced Tools",
        "📚 Documentation"
    ]
)

st.sidebar.markdown("---")

# Quick stats in sidebar
from core.database import DatabaseManager

try:
    db = DatabaseManager()
    stats = db.get_stats()

    st.sidebar.subheader("📊 Quick Stats")
    st.sidebar.metric("Total Matches", f"{stats['total_matches']:,}")
    st.sidebar.metric("Teams", f"{stats['total_teams']:,}")
    st.sidebar.metric("Players", f"{stats.get('total_players', 0):,}")

    if stats['date_range'][0]:
        st.sidebar.caption(f"📅 {stats['date_range'][0][:10]} to {stats['date_range'][1][:10]}")

    db.close()
except Exception as e:
    st.sidebar.warning("Database not available")

st.sidebar.markdown("---")
st.sidebar.caption("Built with ❤️ for League of Legends Esports")

# Load selected page
if page == "🏠 Home":
    from dashboard.page_modules import home
    home.show()
elif page == "📊 Rankings":
    from dashboard.page_modules import rankings
    rankings.show()
elif page == "🎯 Match Predictor":
    from dashboard.page_modules import predictor
    predictor.show()
elif page == "🌍 Regional Offsets":
    from dashboard.page_modules import regional_offsets
    regional_offsets.show()
elif page == "📈 Validation Suite":
    from dashboard.page_modules import validation
    validation.show()
elif page == "🔍 Analysis Tools":
    from dashboard.page_modules import analysis
    analysis.show()
elif page == "📥 Data Management":
    from dashboard.page_modules import data_management
    data_management.show()
elif page == "⚙️ Advanced Tools":
    from dashboard.page_modules import advanced
    advanced.show()
elif page == "📚 Documentation":
    from dashboard.page_modules import documentation
    documentation.show()
