"""
Streamlit Web UI for the AG2 Agent System.
Run with: streamlit run agents/web_ui.py

Provides a visual interface for Replit to:
- Send tasks to the agent team
- View agent activity log
- Check environment status
- Switch between CaptainAgent and GroupChat modes
"""

import os
import sys
from datetime import datetime
from io import StringIO
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

st.set_page_config(
    page_title="AG2 Agent Control Panel",
    page_icon="🤖",
    layout="wide",
)

st.title("🤖 AG2 Agent Control Panel")
st.caption("LOL ELO Calculator - Multi-Agent Development System")
st.markdown("---")

# ── Sidebar: Status ──────────────────────────────────────────────
with st.sidebar:
    st.header("System Status")

    # API key check
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if api_key:
        st.success("OpenAI API Key: configured")
    else:
        st.error("OpenAI API Key: MISSING")
        st.caption("Add via Replit Secrets (Tools > Secrets)")

    # AG2 check
    try:
        import autogen

        st.success(f"AG2: v{autogen.__version__}")
    except ImportError:
        st.error("AG2: not installed")
        st.code("pip install ag2[openai,captainagent]")

    # CaptainAgent check
    try:
        from autogen.agentchat.contrib.captainagent import CaptainAgent

        st.success("CaptainAgent: available")
    except ImportError:
        st.warning("CaptainAgent: not available (GroupChat fallback)")

    # Project check
    elo_dir = Path(__file__).parent.parent / "elo_calculator"
    py_files = list(elo_dir.rglob("*.py")) if elo_dir.exists() else []
    st.info(f"Project: {len(py_files)} Python files")

    st.markdown("---")
    st.header("Agent Team")
    st.markdown("""
    - **ProjectLead** - Architecture & coordination
    - **BackendDev** - ELO algorithms & core logic
    - **DatabaseSpecialist** - SQLite & queries
    - **FrontendDev** - Streamlit dashboard
    - **QAEngineer** - Testing & validation
    """)

# ── Main: Task Input ─────────────────────────────────────────────
col1, col2 = st.columns([3, 1])

with col2:
    mode = st.selectbox(
        "Mode",
        ["auto", "captain", "groupchat"],
        help="auto = CaptainAgent if available, else GroupChat",
    )

with col1:
    task = st.text_area(
        "Task for Agent Team",
        placeholder=(
            "Enter a high-level task, e.g.:\n"
            '  "Add average ELO calculation to the rankings page"\n'
            '  "Fix the team name resolver for Korean teams"\n'
            '  "Write comprehensive tests for the database layer"'
        ),
        height=120,
    )

# Quick task buttons
st.markdown("**Quick Tasks:**")
qcol1, qcol2, qcol3, qcol4 = st.columns(4)
with qcol1:
    if st.button("📋 Inspect Project"):
        task = "Inspect the entire project structure and give a comprehensive status report."
with qcol2:
    if st.button("🧪 Run All Tests"):
        task = "Run all tests and report the results. Fix any failures."
with qcol3:
    if st.button("🔍 Code Review"):
        task = "Review the codebase for potential bugs, code quality issues, and improvements."
with qcol4:
    if st.button("📊 DB Status"):
        task = "Check the database status, show table schemas and record counts."

# ── Execute Task ──────────────────────────────────────────────────
if st.button("🚀 Run Task", type="primary", disabled=not task):
    if not api_key:
        st.error("Cannot run: OPENAI_API_KEY not configured.")
    else:
        with st.spinner("Agents are working..."):
            # Capture stdout to show agent conversation
            log_buffer = StringIO()
            old_stdout = sys.stdout

            try:
                # Tee stdout to both console and buffer
                class TeeWriter:
                    def write(self, text):
                        log_buffer.write(text)
                        old_stdout.write(text)

                    def flush(self):
                        log_buffer.flush()
                        old_stdout.flush()

                sys.stdout = TeeWriter()

                from agents.agent_system import run_task

                started = datetime.now()
                result = run_task(task, mode=mode)
                elapsed = (datetime.now() - started).total_seconds()

            except Exception as e:
                result = f"Error: {e}"
                elapsed = 0
            finally:
                sys.stdout = old_stdout

        # Show results
        st.markdown("---")
        st.subheader("Result")
        st.markdown(result)
        st.caption(f"Completed in {elapsed:.1f}s using {mode} mode")

        # Show agent log
        log_text = log_buffer.getvalue()
        if log_text:
            with st.expander("Agent Activity Log", expanded=False):
                st.code(log_text, language="text")

        # Log to session state for history
        if "history" not in st.session_state:
            st.session_state.history = []
        st.session_state.history.append(
            {
                "time": datetime.now().strftime("%H:%M:%S"),
                "task": task[:100],
                "mode": mode,
                "elapsed": f"{elapsed:.1f}s",
            }
        )

# ── Task History ──────────────────────────────────────────────────
if "history" in st.session_state and st.session_state.history:
    st.markdown("---")
    st.subheader("Task History")
    for entry in reversed(st.session_state.history):
        st.markdown(
            f"**{entry['time']}** | `{entry['mode']}` | "
            f"{entry['task']} | {entry['elapsed']}"
        )

# ── Footer ────────────────────────────────────────────────────────
st.markdown("---")
st.caption(
    "AG2 Agent System | "
    "Give high-level instructions, let agents handle implementation | "
    "[AG2 Docs](https://docs.ag2.ai)"
)
