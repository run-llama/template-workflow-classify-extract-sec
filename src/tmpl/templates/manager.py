"""High-level template management operations."""

from __future__ import annotations

import shutil
from pathlib import Path

from ..utils import console, run_git_command
from .copier_integration import (
    parse_template_variables,
    run_copier_quietly,
    generate_template_defaults,
)


def get_template_dir(template_name: str) -> Path:
    """Get the directory path for a template."""
    root = Path(__file__).parent.parent.parent.parent
    return root / "templates" / template_name


def get_rendered_dir(template_name: str) -> Path:
    """Get the directory path for a rendered template."""
    root = Path(__file__).parent.parent.parent.parent
    return root / "rendered" / template_name


def regenerate_test_proj(template_dir: Path) -> None:
    """Regenerate the test directory for a template using copier."""
    # Extract template name from template_dir path (e.g., templates/basic -> basic)
    template_name = template_dir.name
    root = Path.cwd()
    test_proj_dir: Path = root / "rendered" / template_name

    variables = (
        parse_template_variables(template_dir)
        if test_proj_dir.exists()
        else generate_template_defaults(template_dir)
    )

    if test_proj_dir.exists():
        console.print(f"Deleting {test_proj_dir}")
        shutil.rmtree(test_proj_dir)
    else:
        console.print(f"Directory {test_proj_dir} does not exist")

    with console.status("[bold green]Running copier to regenerate test directory..."):
        run_copier_quietly(str(template_dir), str(test_proj_dir), variables)

    answers_file = test_proj_dir / ".copier-answers.yml"
    if answers_file.exists():
        try:
            run_git_command(["git", "restore", str(answers_file)], cwd=template_dir)
        except SystemExit:
            pass


def ensure_test_proj_exists(template_dir: Path) -> Path:
    """Ensure test directory exists and return its path for a template."""
    # Extract template name from template_dir path (e.g., templates/basic -> basic)
    template_name = template_dir.name
    root = Path.cwd()
    test_proj_dir: Path = root / "rendered" / template_name
    if not test_proj_dir.exists():
        console.print(
            f"Error: test directory for {template_name} does not exist. Run 'tmpl regenerate {template_name}' first.",
            style="bold red",
        )
        raise SystemExit(1)
    return test_proj_dir
