"""Copier integration utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Dict

import yaml
import copier
from copier._template import Template

from .jinja_utils import render_jinja_string
from ..utils import run_git_command
from ..utils import git_output


def run_copier_quietly(src_path: str, dst_path: str, data: Dict[str, str]) -> None:
    """Run copier with minimal output."""
    # Clean gitignored files from source directory before copying
    src_path_obj = Path(src_path).resolve()

    # Find git repository root
    try:
        repo_root = Path(git_output(["rev-parse", "--show-toplevel"])).resolve()

        # Get relative path from repo root to src_path
        relative_src_path = src_path_obj.relative_to(repo_root)

        # Run git clean on the specific subdirectory
        run_git_command(["git", "clean", "-Xf", str(relative_src_path)], cwd=repo_root)
    except (SystemExit, ValueError, OSError):
        # If git operations fail, continue anyway - this is not critical
        pass

    copier.run_copy(
        src_path=src_path,
        dst_path=dst_path,
        data=data,
        unsafe=True,
        quiet=True,
        vcs_ref="HEAD",
    )


def parse_template_variables(template_dir: Path) -> Dict[str, str]:
    """Parse template variables using Copier's Jinja environment for a given template."""

    # Read answers from existing materialized project
    template_name = template_dir.name
    root = Path.cwd()
    test_proj = root / "rendered" / template_name
    answers_file = test_proj / ".copier-answers.yml"

    with open(answers_file, "r", encoding="utf-8") as f:
        answers_data = yaml.safe_load(f)
        # Filter out copier metadata
        user_answers = {k: v for k, v in answers_data.items() if not k.startswith("_")}

    # Get template configuration for variable parsing
    template = Template(url=str(template_dir))

    # Build complete variable context by evaluating template defaults
    result: Dict[str, str] = dict(user_answers)

    # Multiple passes to handle dependencies between computed variables
    max_iterations = 10
    for _ in range(max_iterations):
        changed = False
        for question_name, question_config in template.questions_data.items():
            if question_name not in result and "default" in question_config:
                default_value = question_config["default"]
                if isinstance(default_value, str) and "{{" in default_value:
                    # Evaluate Jinja expression using our helper
                    try:
                        rendered = render_jinja_string(
                            default_value, result, template_dir
                        )
                        result[question_name] = rendered
                        changed = True
                    except Exception:
                        # Skip variables that can't be evaluated yet
                        pass
                else:
                    result[question_name] = default_value
                    changed = True

        # Stop if no new variables were computed
        if not changed:
            break
    return result
