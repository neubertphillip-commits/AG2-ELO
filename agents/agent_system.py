"""
AG2 Multi-Agent System for LOL ELO Calculator.

Two operation modes:
1. CaptainAgent mode  - Automatic task decomposition and agent selection
2. GroupChat mode     - Direct collaboration between all specialist agents

CaptainAgent is preferred. GroupChat is the fallback if CaptainAgent
extras are not installed.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agents.config.llm_config import get_captain_llm_config, get_llm_config

# AG2 imports
try:
    import autogen
    from autogen import AssistantAgent, GroupChat, GroupChatManager, UserProxyAgent

    AG2_AVAILABLE = True
except ImportError:
    AG2_AVAILABLE = False

# CaptainAgent import (optional extra)
try:
    from autogen.agentchat.contrib.captainagent import CaptainAgent

    CAPTAIN_AVAILABLE = True
except ImportError:
    CAPTAIN_AVAILABLE = False

EXPERT_LIBRARY = Path(__file__).parent / "config" / "expert_library.json"
WORK_DIR = PROJECT_ROOT / "agents" / "workdir"


def _register_tools(agent: Any, executor: Any) -> None:
    """Register file/git/test tools with an agent + executor pair."""
    from agents.tools.file_tools import list_files, read_file, search_in_files, write_file
    from agents.tools.git_tools import git_add_and_commit, git_log, git_status
    from agents.tools.test_tools import check_syntax, run_python, run_tests

    tools = [
        read_file,
        write_file,
        list_files,
        search_in_files,
        git_status,
        git_add_and_commit,
        git_log,
        run_tests,
        run_python,
        check_syntax,
    ]

    for tool_fn in tools:
        autogen.register_function(
            tool_fn,
            caller=agent,
            executor=executor,
            name=tool_fn.__name__,
            description=tool_fn.__doc__ or "",
        )


# ---------------------------------------------------------------------------
# Mode 1: CaptainAgent (recommended)
# ---------------------------------------------------------------------------


def run_captain_mode(task: str) -> str:
    """Run a task using CaptainAgent with the expert library.

    CaptainAgent automatically:
    - Analyzes the task
    - Selects relevant experts from the library
    - Creates a nested group chat
    - Coordinates agents to complete the task
    """
    if not CAPTAIN_AVAILABLE:
        raise ImportError(
            "CaptainAgent not available. Install with: "
            "pip install ag2[openai,captainagent]"
        )

    llm_config = get_captain_llm_config()
    WORK_DIR.mkdir(parents=True, exist_ok=True)

    captain = CaptainAgent(
        name="captain_agent",
        llm_config=llm_config,
        code_execution_config={
            "use_docker": False,
            "work_dir": str(WORK_DIR),
        },
        agent_lib=str(EXPERT_LIBRARY),
        agent_config_save_path=None,
    )

    user_proxy = UserProxyAgent(
        name="user",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=0,
    )

    result = user_proxy.initiate_chat(
        captain,
        message=_build_task_prompt(task),
        max_turns=1,
    )

    return _extract_result(result)


# ---------------------------------------------------------------------------
# Mode 2: GroupChat (fallback)
# ---------------------------------------------------------------------------


def run_groupchat_mode(task: str) -> str:
    """Run a task using a GroupChat with all specialist agents.

    All agents participate in a round-robin style conversation,
    managed by a GroupChatManager that selects who speaks next.
    """
    if not AG2_AVAILABLE:
        raise ImportError(
            "AG2 not available. Install with: pip install ag2[openai]"
        )

    llm_config = get_llm_config()
    captain_llm = get_captain_llm_config()
    WORK_DIR.mkdir(parents=True, exist_ok=True)

    # Load expert definitions
    experts = json.loads(EXPERT_LIBRARY.read_text(encoding="utf-8"))

    # User proxy (executes code and tools)
    user_proxy = UserProxyAgent(
        name="executor",
        human_input_mode="NEVER",
        code_execution_config={
            "use_docker": False,
            "work_dir": str(WORK_DIR),
            "last_n_messages": 3,
        },
        max_consecutive_auto_reply=10,
        is_termination_msg=lambda msg: "TERMINATE" in msg.get("content", ""),
    )

    # Create specialist agents from library
    agents = [user_proxy]
    for expert in experts:
        agent = AssistantAgent(
            name=expert["name"],
            system_message=expert["system_message"],
            llm_config=llm_config,
            description=expert["description"],
        )
        # Register tools so agents can interact with the project
        _register_tools(agent, user_proxy)
        agents.append(agent)

    # Group chat with auto speaker selection
    group_chat = GroupChat(
        agents=agents,
        messages=[],
        max_round=30,
        speaker_selection_method="auto",
        allow_repeat_speaker=False,
    )

    manager = GroupChatManager(
        groupchat=group_chat,
        llm_config=captain_llm,
    )

    result = user_proxy.initiate_chat(
        manager,
        message=_build_task_prompt(task),
    )

    return _extract_result(result)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_task_prompt(task: str) -> str:
    """Wrap the user's task with project context."""
    return f"""You are working on the LOL ELO Calculator project.

Project location: elo_calculator/
Key directories:
- core/       - ELO engine, database, data loaders
- dashboard/  - Streamlit frontend (page_modules/)
- scripts/    - Import/export utilities
- tests/      - pytest test suite
- validation/ - Statistical validation
- config.py   - System configuration (K=24, Initial ELO=1500)

Database: SQLite (elo_calculator/db/)
Frontend: Streamlit (streamlit run dashboard/app.py)

TASK:
{task}

Instructions:
1. First inspect relevant files to understand current state
2. Plan your approach before writing code
3. Implement the changes
4. Verify with syntax checks or tests
5. Commit the changes with a descriptive message
6. Reply TERMINATE when done
"""


def _extract_result(chat_result: Any) -> str:
    """Extract a readable summary from the chat result."""
    if hasattr(chat_result, "summary"):
        return chat_result.summary
    if hasattr(chat_result, "chat_history") and chat_result.chat_history:
        last = chat_result.chat_history[-1]
        content = last.get("content", "")
        return content if content else "(no content in last message)"
    return str(chat_result)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_task(task: str, mode: str = "auto") -> str:
    """Run a development task with the AG2 agent team.

    Args:
        task: High-level task description (feature, bug fix, etc.)
        mode: 'captain', 'groupchat', or 'auto' (tries captain first).

    Returns:
        Summary of what the agents accomplished.
    """
    if mode == "captain":
        return run_captain_mode(task)
    elif mode == "groupchat":
        return run_groupchat_mode(task)
    else:
        # Auto: prefer CaptainAgent, fall back to GroupChat
        if CAPTAIN_AVAILABLE:
            print("[AG2] Using CaptainAgent mode")
            return run_captain_mode(task)
        elif AG2_AVAILABLE:
            print("[AG2] CaptainAgent not installed, using GroupChat mode")
            return run_groupchat_mode(task)
        else:
            raise ImportError(
                "AG2 is not installed. Run: pip install ag2[openai,captainagent]"
            )
