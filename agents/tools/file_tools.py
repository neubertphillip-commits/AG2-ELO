"""
File system tools for AG2 agents.
Allows agents to read, write, and list project files.
"""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent / "elo_calculator"


def read_file(filepath: str) -> str:
    """Read a file from the project. Path is relative to elo_calculator/.

    Args:
        filepath: Relative path like 'core/database.py' or 'config.py'

    Returns:
        File contents as string, or error message.
    """
    target = PROJECT_ROOT / filepath
    if not target.exists():
        return f"ERROR: File not found: {filepath}"
    if not target.is_file():
        return f"ERROR: Not a file: {filepath}"
    try:
        return target.read_text(encoding="utf-8")
    except Exception as e:
        return f"ERROR reading {filepath}: {e}"


def write_file(filepath: str, content: str) -> str:
    """Write content to a file in the project. Creates parent dirs if needed.

    Args:
        filepath: Relative path like 'core/new_module.py'
        content: Full file content to write.

    Returns:
        Success or error message.
    """
    target = PROJECT_ROOT / filepath
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"OK: Written {len(content)} bytes to {filepath}"
    except Exception as e:
        return f"ERROR writing {filepath}: {e}"


def list_files(directory: str = "") -> str:
    """List files in a project directory.

    Args:
        directory: Relative path like 'core/' or '' for project root.

    Returns:
        Newline-separated list of files and directories.
    """
    target = PROJECT_ROOT / directory
    if not target.exists():
        return f"ERROR: Directory not found: {directory}"
    if not target.is_dir():
        return f"ERROR: Not a directory: {directory}"

    entries = []
    for item in sorted(target.iterdir()):
        prefix = "[DIR] " if item.is_dir() else "      "
        entries.append(f"{prefix}{item.name}")

    return "\n".join(entries) if entries else "(empty directory)"


def search_in_files(pattern: str, directory: str = "") -> str:
    """Search for a text pattern across project files.

    Args:
        pattern: Text to search for (case-insensitive).
        directory: Subdirectory to search in, or '' for all.

    Returns:
        Matching lines with file paths and line numbers.
    """
    target = PROJECT_ROOT / directory
    if not target.exists():
        return f"ERROR: Directory not found: {directory}"

    results = []
    pattern_lower = pattern.lower()

    for py_file in target.rglob("*.py"):
        try:
            lines = py_file.read_text(encoding="utf-8").splitlines()
            for i, line in enumerate(lines, 1):
                if pattern_lower in line.lower():
                    rel = py_file.relative_to(PROJECT_ROOT)
                    results.append(f"{rel}:{i}: {line.strip()}")
        except Exception:
            continue

    if not results:
        return f"No matches found for '{pattern}'"

    if len(results) > 50:
        results = results[:50]
        results.append(f"... (truncated, {len(results)} total matches)")

    return "\n".join(results)
