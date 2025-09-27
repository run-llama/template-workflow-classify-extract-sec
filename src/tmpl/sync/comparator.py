"""Directory and file comparison utilities."""

from __future__ import annotations

from pathlib import Path
from typing import List

from ..utils.filesystem import get_git_tracked_files


def compare_directories(expected_dir: Path, actual_dir: Path) -> List[str]:
    """Compare two directories and return list of files that differ, respecting gitignore."""
    differences: List[str] = []

    expected_files = (
        get_git_tracked_files(expected_dir, respect_gitignore=False)
        if expected_dir.exists()
        else set()
    )
    actual_files = (
        get_git_tracked_files(actual_dir, respect_gitignore=True)
        if actual_dir.exists()
        else set()
    )

    for file_path in expected_files - actual_files:
        differences.append(f"Missing file: {file_path}")

    for file_path in actual_files - expected_files:
        differences.append(f"Extra file: {file_path}")

    for file_path in expected_files & actual_files:
        expected_file = expected_dir / file_path
        actual_file = actual_dir / file_path

        with open(expected_file, "r", encoding="utf-8") as f:
            expected_content = f.read()
        with open(actual_file, "r", encoding="utf-8") as f:
            actual_content = f.read()

        def _normalize_newline_end(s: str) -> str:
            return s.rstrip("\n") + "\n"

        if _normalize_newline_end(expected_content) == _normalize_newline_end(
            actual_content
        ):
            continue

        if expected_content != actual_content:
            differences.append(f"Content differs: {file_path}")

    return differences
