"""
AG2 Agent System - Main Entry Point for Replit.

Usage:
    python agents/main.py                     # Interactive mode
    python agents/main.py "implement feature" # Single task mode
    python agents/main.py --mode groupchat    # Force GroupChat mode
"""

import argparse
import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))


def print_banner():
    print(
        """
========================================
  AG2 Multi-Agent System
  LOL ELO Calculator
========================================
  Agents: ProjectLead, BackendDev,
          DatabaseSpecialist, FrontendDev,
          QAEngineer
  Orchestrator: CaptainAgent
========================================
"""
    )


def check_environment():
    """Verify all required dependencies and secrets are available."""
    import os

    errors = []

    # Check API key
    if not os.environ.get("OPENAI_API_KEY"):
        errors.append(
            "OPENAI_API_KEY not set. Add it to Replit Secrets "
            "(Tools > Secrets > OPENAI_API_KEY)"
        )

    # Check AG2 installation
    try:
        import autogen

        print(f"  [OK] AG2/AutoGen installed (v{autogen.__version__})")
    except ImportError:
        errors.append("AG2 not installed. Run: pip install ag2[openai,captainagent]")

    # Check CaptainAgent
    try:
        from autogen.agentchat.contrib.captainagent import CaptainAgent

        print("  [OK] CaptainAgent available")
    except ImportError:
        print("  [!!] CaptainAgent not available (GroupChat fallback will be used)")

    # Check project structure
    elo_dir = Path(__file__).parent.parent / "elo_calculator"
    if elo_dir.exists():
        py_count = len(list(elo_dir.rglob("*.py")))
        print(f"  [OK] Project found: {py_count} Python files")
    else:
        errors.append("elo_calculator/ directory not found")

    if errors:
        print("\n  ERRORS:")
        for e in errors:
            print(f"  [X] {e}")
        return False

    print("  [OK] Environment ready")
    return True


def interactive_mode(mode: str):
    """Interactive REPL for sending tasks to agents."""
    from agents.agent_system import run_task

    print("Enter tasks for the agent team. Type 'quit' to exit.")
    print("Examples:")
    print('  > "Add average ELO calculation to the dashboard"')
    print('  > "Fix the bug where team names are not resolved"')
    print('  > "Write tests for the ELO calculator service"')
    print()

    while True:
        try:
            task = input("task> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if not task or task.lower() in ("quit", "exit", "q"):
            print("Exiting.")
            break

        print(f"\n[AG2] Delegating to agent team ({mode} mode)...")
        print("-" * 50)

        try:
            result = run_task(task, mode=mode)
            print("-" * 50)
            print("[AG2] Result:")
            print(result)
        except Exception as e:
            print(f"[AG2] Error: {e}")

        print()


def single_task_mode(task: str, mode: str):
    """Run a single task and exit."""
    from agents.agent_system import run_task

    print(f"[AG2] Task: {task}")
    print(f"[AG2] Mode: {mode}")
    print("-" * 50)

    try:
        result = run_task(task, mode=mode)
        print("-" * 50)
        print("[AG2] Result:")
        print(result)
    except Exception as e:
        print(f"[AG2] Error: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="AG2 Multi-Agent System for LOL ELO Calculator"
    )
    parser.add_argument(
        "task",
        nargs="?",
        default=None,
        help="Task to execute (omit for interactive mode)",
    )
    parser.add_argument(
        "--mode",
        choices=["auto", "captain", "groupchat"],
        default="auto",
        help="Agent orchestration mode (default: auto)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check environment and exit",
    )

    args = parser.parse_args()

    print_banner()

    print("Checking environment...")
    env_ok = check_environment()
    print()

    if args.check:
        sys.exit(0 if env_ok else 1)

    if not env_ok:
        print("Fix the errors above before running tasks.")
        sys.exit(1)

    if args.task:
        single_task_mode(args.task, args.mode)
    else:
        interactive_mode(args.mode)


if __name__ == "__main__":
    main()
