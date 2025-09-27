"""Git change detection utilities."""

from __future__ import annotations

import os
import subprocess
from typing import Iterable, List, Set

from ..utils import git_output, run


def detect_base_ref(head: str) -> str:
    """Detect the base reference for comparing changes."""
    base_ref = os.getenv("GITHUB_BASE_REF")
    if base_ref:
        try:
            git_output(["rev-parse", f"origin/{base_ref}"])
        except subprocess.CalledProcessError:
            run(["git", "fetch", "--no-tags", "--depth", "1", "origin", base_ref])
        return git_output(["merge-base", f"origin/{base_ref}", head])

    for candidate in ("main", "master"):
        try:
            git_output(["rev-parse", f"origin/{candidate}"])
        except subprocess.CalledProcessError:
            continue
        return git_output(["merge-base", f"origin/{candidate}", head])

    return git_output(["rev-parse", f"{head}~1"])  # type: ignore[no-any-return]


def list_changed_files(base: str, head: str) -> List[str]:
    """List files changed between two git references."""
    out = git_output(["diff", "--name-only", f"{base}...{head}"])
    return [line for line in out.splitlines() if line]


def templates_from_files(files: Iterable[str]) -> List[str]:
    """Extract template names from a list of file paths."""
    templates: Set[str] = set()
    for path in files:
        if path.startswith("templates/"):
            parts = path.split("/")
            if len(parts) >= 2 and parts[1]:
                templates.add(parts[1])
    return sorted(templates)
