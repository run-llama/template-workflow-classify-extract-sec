"""CLI interface for tmpl - Template monorepo manager."""

from __future__ import annotations

import json
import os
from typing import Optional

import click

from .config import MAPPING_DATA
from .git import (
    clone_templates,
    detect_base_ref,
    list_changed_files,
    merge_template,
    mirror_template,
    templates_from_files,
)
from .templates import (
    ensure_test_proj_exists,
    get_template_dir,
    regenerate_test_proj,
)
from .sync import compare_with_expected_materialized
from .checks import run_javascript_checks, run_python_checks
from .init.scripts import init_python_scripts, init_package_json_scripts
from .utils import console, run_git_command


@click.group()
def cli() -> None:
    """Template monorepo manager."""
    pass


@cli.command("list")
@click.option("--detail", "detail", is_flag=True, default=False)
def list_cmd(detail: bool) -> None:
    """
    List configured templates and their remote URL and branch.
    """
    for name, cfg in MAPPING_DATA.items():
        print(name)
        if detail:
            print(f"  remote: {cfg.get('remote')}")
            print(f"  url: {cfg.get('url')}")
            print(f"  branch: {cfg.get('branch')}")


@cli.command("changed")
@click.option("--base", "base_ref", default=None, help="Base ref/sha to diff against")
@click.option("--head", "head_ref", default="HEAD", help="Head ref/sha to diff from")
@click.option("--format", "fmt", type=click.Choice(["json", "lines"]), default="json")
@click.option("--github-output", is_flag=True, help="Write GitHub Actions outputs")
def changed_cmd(
    base_ref: Optional[str], head_ref: str, fmt: str, github_output: bool
) -> None:
    """
    Show which templates changed between two git refs.

    - --base: base ref/sha to diff against (auto-detected if omitted)
    - --head: head ref/sha to diff from (default: HEAD)
    - --format: output format (json|lines)
    - --github-output: also write outputs to $GITHUB_OUTPUT (json, has_changes)
    """
    head = head_ref
    base = base_ref or detect_base_ref(head)
    files = list_changed_files(base, head)
    changed = templates_from_files(files, list(MAPPING_DATA.keys()))
    if fmt == "json":
        print(json.dumps(changed))
    else:
        for t in changed:
            print(t)
    if github_output:
        gh_out = os.getenv("GITHUB_OUTPUT")
        if gh_out:
            with open(gh_out, "a", encoding="utf-8") as f:
                f.write(f"json={json.dumps(changed)}\n")
                f.write(f"has_changes={'true' if changed else 'false'}\n")


@cli.command("mirror")
@click.argument("template_name", type=click.Choice(MAPPING_DATA.keys()))
@click.option("--force", is_flag=True, help="Force push to remote (use with caution)")
def mirror_cmd(template_name: str, force: bool) -> None:
    """
    Push the contents of templates/<name> to its upstream repository.

    Ensures the configured remote exists, then runs
    `git subtree push --prefix templates/<name> <remote> <branch>` to mirror
    the template subtree to the external repo/branch.
    
    Use --force to force push when there are conflicts (e.g., after squash merges).
    """
    cfg = MAPPING_DATA.get(template_name)
    if not cfg:
        raise SystemExit(f"No mapping found for template: {template_name}")
    mirror_template(template_name, cfg, force=force)


@cli.command("merge")
@click.argument("template_name", type=click.Choice(MAPPING_DATA.keys()))
def merge_cmd(template_name: str) -> None:
    """
    Merge upstream changes into templates/<name> from its configured remote.

    Runs `git subtree pull --prefix templates/<name> <remote> <branch> --squash`.
    """
    cfg = MAPPING_DATA.get(template_name)
    if not cfg:
        raise SystemExit(f"No mapping found for template: {template_name}")
    merge_template(template_name, cfg)


@cli.command("clone")
@click.argument("template_name", type=click.Choice(MAPPING_DATA.keys()))
def clone_cmd(template_name: str) -> None:
    """
    Add all configured templates under templates/ via git subtree (initial import).

    For each template not already present locally, runs
    `git subtree add --prefix templates/<name> <remote> <branch> --squash`.
    """
    clone_templates({template_name: MAPPING_DATA[template_name]})


@cli.command("regenerate")
@click.argument("template_name", type=click.Choice(MAPPING_DATA.keys()))
def template_regenerate_cmd(template_name: str) -> None:
    """Regenerate the test directory for a template."""
    template_dir = get_template_dir(template_name)
    console.print(f"Working directory: {template_dir}")
    console.print("Checking for uncommitted changes...")
    git_status_check = run_git_command(
        ["git", "status", "--porcelain"], cwd=template_dir
    )
    if git_status_check.stdout.strip():
        console.print(
            "Error: Repository has uncommitted changes. Please commit or stash them first.",
            style="bold red",
        )
        console.print(git_status_check.stdout)
        raise SystemExit(1)
    regenerate_test_proj(template_dir)
    console.print("✓ test directory regenerated")


@cli.command("check-regeneration")
@click.argument("template_name", type=click.Choice(MAPPING_DATA.keys()))
def template_check_regeneration_cmd(template_name: str) -> None:
    """Check if test directory matches what would be generated from the template."""
    template_dir = get_template_dir(template_name)
    console.print(f"Working directory: {template_dir}")
    regenerate_test_proj(template_dir)
    console.print("Checking generated files against template...")
    git_status = run_git_command(["git", "status", "--porcelain"], cwd=template_dir)
    if git_status.stdout.strip():
        console.print("\n❌ Generated files do not match template!", style="bold red")
        console.print("\nFiles that differ:")
        console.print(git_status.stdout)
        console.print("\nDifferences:")
        git_diff = run_git_command(["git", "diff"], cwd=template_dir)
        console.print(git_diff.stdout)
        console.print(
            "\nTo fix: If these changes look good, likely you just need to run regenerate and commit the changes.",
            style="bold red",
        )
        raise SystemExit(1)
    else:
        console.print("✓ Generated files match template")


@cli.command("check-python")
@click.argument("template_name", type=click.Choice(MAPPING_DATA.keys()))
@click.option("--fix", is_flag=True, help="Fix formatting issues automatically.")
def template_check_python_cmd(template_name: str, fix: bool) -> None:
    """Run Python validation checks on test directory."""
    template_dir = get_template_dir(template_name)
    test_proj_dir = ensure_test_proj_exists(template_dir)
    run_python_checks(test_proj_dir, fix)


@cli.command("check-javascript")
@click.argument("template_name", type=click.Choice(MAPPING_DATA.keys()))
@click.option("--fix", is_flag=True, help="Fix formatting issues automatically.")
def template_check_javascript_cmd(template_name: str, fix: bool) -> None:
    """Run JavaScript/TypeScript validation checks on test directory."""
    template_dir = get_template_dir(template_name)
    test_proj_dir = ensure_test_proj_exists(template_dir)
    run_javascript_checks(test_proj_dir, fix)


@cli.command("check-template")
@click.argument("template_name", type=click.Choice(MAPPING_DATA.keys()))
@click.option("--fix", is_flag=True, help="Fix template files by copying back changes.")
@click.option(
    "--fix-format",
    is_flag=True,
    help="Run Python and JavaScript formatters before fixing template files. Implies --fix.",
)
def template_check_template_cmd(
    template_name: str, fix: bool, fix_format: bool
) -> None:
    """Compare test directory with expected template output and optionally fix differences."""
    template_dir = get_template_dir(template_name)
    console.print(f"Working directory: {template_dir}")
    if fix_format:
        fix = True
    test_proj_dir = ensure_test_proj_exists(template_dir)
    if fix_format:
        run_python_checks(test_proj_dir, fix=True)
        run_javascript_checks(test_proj_dir, fix=True)
    compare_with_expected_materialized(template_dir, fix_mode=fix)


@cli.command("init-scripts")
@click.argument("template_name", type=click.Choice(MAPPING_DATA.keys()))
def init_python_scripts_cmd(template_name: str) -> None:
    """Initialize development scripts for a template (Python and JavaScript/TypeScript)."""
    template_dir = get_template_dir(template_name)
    console.print(f"Working directory: {template_dir}")
    init_python_scripts(template_name)
    init_package_json_scripts(template_name)
