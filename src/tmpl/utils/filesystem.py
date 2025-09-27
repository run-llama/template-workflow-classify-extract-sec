"""File system utilities."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Set


def get_git_tracked_files(directory: Path, respect_gitignore: bool = True) -> Set[Path]:
    """Get set of files that would be tracked by git (optionally respecting gitignore)."""
    ignored_files = {".copier-answers.yml"}

    if not respect_gitignore:
        tracked_files: Set[Path] = set()
        for file_path in directory.rglob("*"):
            if file_path.is_file():
                relative_path = file_path.relative_to(directory)
                if relative_path.name not in ignored_files:
                    tracked_files.add(relative_path)
        return tracked_files

    result = subprocess.run(
        ["git", "ls-files", "--others", "--cached", "--exclude-standard"],
        cwd=directory,
        capture_output=True,
        text=True,
        check=True,
    )

    tracked_files: Set[Path] = set()
    for line in result.stdout.strip().split("\n"):
        if line.strip():
            file_path = directory / line.strip()
            relative_path = Path(line.strip())
            if file_path.is_file() and relative_path.name not in ignored_files:
                tracked_files.add(relative_path)

    return tracked_files
