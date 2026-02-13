"""
Git tools for AG2 agents.
Allows agents to commit changes and check status.
"""

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent


def _run_git(cmd: list[str], timeout: int = 30) -> str:
    """Run a git command and return output."""
    try:
        result = subprocess.run(
            ["git"] + cmd,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = result.stdout.strip()
        if result.returncode != 0:
            error = result.stderr.strip()
            return f"ERROR (exit {result.returncode}): {error}"
        return output if output else "(no output)"
    except subprocess.TimeoutExpired:
        return "ERROR: Git command timed out"
    except Exception as e:
        return f"ERROR: {e}"


def git_status() -> str:
    """Show current git status (modified, staged, untracked files)."""
    return _run_git(["status", "--short"])


def git_diff(filepath: str = "") -> str:
    """Show unstaged changes. Optionally for a specific file.

    Args:
        filepath: Optional file path relative to repo root.
    """
    cmd = ["diff", "--stat"]
    if filepath:
        cmd.append(filepath)
    return _run_git(cmd)


def git_add_and_commit(message: str, files: str = ".") -> str:
    """Stage files and create a commit.

    Args:
        message: Commit message describing the changes.
        files: Space-separated file paths to stage, or '.' for all.

    Returns:
        Commit result or error.
    """
    # Stage
    file_list = files.split()
    add_result = _run_git(["add"] + file_list)
    if add_result.startswith("ERROR"):
        return f"Stage failed: {add_result}"

    # Commit
    commit_result = _run_git(["commit", "-m", message])
    return commit_result


def git_log(count: int = 5) -> str:
    """Show recent commit history.

    Args:
        count: Number of recent commits to show.
    """
    return _run_git(["log", f"--oneline", f"-{count}"])
