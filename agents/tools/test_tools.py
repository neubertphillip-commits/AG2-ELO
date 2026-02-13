"""
Test and validation tools for AG2 agents.
Allows agents to run pytest and validation scripts.
"""

import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent / "elo_calculator"


def run_tests(test_path: str = "tests/", verbose: bool = True) -> str:
    """Run pytest on the project test suite.

    Args:
        test_path: Relative path to test file or directory (default: tests/).
        verbose: Whether to show verbose output.

    Returns:
        Test results output.
    """
    cmd = ["python", "-m", "pytest", str(PROJECT_ROOT / test_path)]
    if verbose:
        cmd.append("-v")
    cmd.append("--tb=short")

    try:
        result = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=120,
        )
        output = result.stdout
        if result.stderr:
            output += "\n--- STDERR ---\n" + result.stderr
        return output if output.strip() else "(no output)"
    except subprocess.TimeoutExpired:
        return "ERROR: Tests timed out after 120 seconds"
    except Exception as e:
        return f"ERROR running tests: {e}"


def run_python(script_path: str, args: str = "") -> str:
    """Execute a Python script from the project.

    Args:
        script_path: Relative path like 'scripts/view_database.py'
        args: Optional command-line arguments.

    Returns:
        Script output (stdout + stderr).
    """
    cmd = ["python", str(PROJECT_ROOT / script_path)]
    if args:
        cmd.extend(args.split())

    try:
        result = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = result.stdout
        if result.stderr:
            output += "\n--- STDERR ---\n" + result.stderr
        return output[:5000] if output.strip() else "(no output)"
    except subprocess.TimeoutExpired:
        return "ERROR: Script timed out after 60 seconds"
    except Exception as e:
        return f"ERROR running script: {e}"


def check_syntax(filepath: str) -> str:
    """Check Python file for syntax errors.

    Args:
        filepath: Relative path to a .py file.

    Returns:
        'OK' if no syntax errors, or error details.
    """
    target = PROJECT_ROOT / filepath
    if not target.exists():
        return f"ERROR: File not found: {filepath}"

    try:
        result = subprocess.run(
            ["python", "-m", "py_compile", str(target)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return f"OK: {filepath} has no syntax errors"
        return f"SYNTAX ERROR in {filepath}:\n{result.stderr}"
    except Exception as e:
        return f"ERROR: {e}"
