"""Python validation checks."""

from __future__ import annotations

from pathlib import Path

from ..utils import console, run_git_command


def run_python_checks(test_proj_dir: Path, fix: bool) -> None:
    """Run Python validation checks on test directory using hatch."""
    console.print("Running Python validation checks...")
    run_git_command(
        ["uv", "run", "hatch", "run", "all-fix" if fix else "all-check"],
        cwd=test_proj_dir,
    )
    console.print("✓ Python checks passed")
