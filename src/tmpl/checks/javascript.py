"""JavaScript/TypeScript validation checks."""

from __future__ import annotations

from pathlib import Path

from ..utils import console, run_git_command


def run_javascript_checks(test_proj_dir: Path, fix: bool) -> None:
    """Run TypeScript and format validation checks on test/ui using npm."""
    ui_dir: Path = test_proj_dir / "ui"
    if not ui_dir.exists():
        console.print(
            "test/ui directory does not exist. Ignoring JavaScript checks.",
            style="yellow",
        )
        return
    console.print("Running TypeScript validation checks...")
    run_git_command(["npm", "run", "all-fix" if fix else "all-check"], cwd=ui_dir)
    console.print("✓ TypeScript checks passed")
