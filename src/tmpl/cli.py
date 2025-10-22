"""CLI interface for tmpl - Template monorepo manager."""

from __future__ import annotations

import json
import os
import sys
from typing import Optional

import click

from .config import MAPPING_DATA
from .config import load_mapping
from .config import MAPPING_FILE
from .git.versioning import (
    detect_changed_templates,
    apply_version_bumps,
    save_mapping_versions,
)
from .git.tagging import run_tag_versions
from .git import (
    clone_templates,
    detect_base_ref,
    list_changed_files,
    merge_template,
    mirror_template,
    templates_from_files,
)
from .templates import (
    get_template_dir,
)
from .checks import run_javascript_checks, run_python_checks, validate_workflows
from .init.scripts import init_python_scripts, init_package_json_scripts
from .metrics.exporter import send_posthog_event, GitHubAuth, get_all_events_for_export
from pathlib import Path
from packaging.version import Version
from .utils import console


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
            if cfg.get("version"):
                print(f"  version: {cfg.get('version')}")


@cli.command("version")
@click.option("--base", "base_ref", default=None, help="Base ref/sha to diff against")
@click.option("--head", "head_ref", default="HEAD", help="Head ref/sha to diff from")
@click.option(
    "--committed-only/--include-uncommitted",
    default=False,
    help="Only consider committed changes (default includes uncommitted)",
)
def version_cmd(base_ref: Optional[str], head_ref: str, committed_only: bool) -> None:
    """
    Bump versions for templates that have changed.

    Detects changed templates (like 'changed'), then interactively prompts for each
    whether the change is major, minor, patch, or ignore. Updates the version
    in .github/templates-remotes.yml accordingly (defaulting to 0.0.0 when missing).
    """
    changed = detect_changed_templates(
        head_ref=head_ref,
        base_ref=base_ref,
        include_uncommitted=not committed_only,
        detect_base_ref_func=detect_base_ref,
        list_changed_files_func=list_changed_files,
        templates_from_files_func=templates_from_files,
        mapping_keys=list(MAPPING_DATA.keys()),
    )

    if not changed:
        console.print("No template changes detected.", style="yellow")
        return

    mapping = load_mapping(Path(MAPPING_FILE))

    def parse_version(v: Optional[str]) -> Version:
        try:
            return Version(v) if v else Version("0.0.0")
        except Exception:
            return Version("0.0.0")

    decisions: dict[str, str] = {}
    for name in changed:
        choice = click.prompt(
            f"Version change for {name}",
            type=click.Choice(
                ["major", "minor", "patch", "ignore"], case_sensitive=False
            ),
            default="ignore",
            show_choices=True,
        )
        decisions[name] = choice.lower()

    new_mapping = apply_version_bumps(mapping, decisions)

    if mapping == new_mapping:
        console.print("No versions changed.", style="yellow")
        return

    save_mapping_versions(new_mapping, Path(MAPPING_FILE))
    console.print("Updated versions:", style="green")
    for name, action in decisions.items():
        if action != "ignore" and name in new_mapping:
            console.print(f"  - {name} -> {new_mapping[name].get('version')}")


@cli.command("tag-versions")
@click.option("--dry-run", is_flag=True, help="Print actions without fetching/pushing")
def tag_versions_cmd(dry_run: bool) -> None:
    """
    Ensure remote tags exist for all templates with a configured version.

    For each template with a `version` in the mapping, checks the remote for tag
    `vX.Y.Z`. If missing, computes the subtree split commit for the template and pushes
    the tag pointing to that commit to the remote.
    """
    tagged = run_tag_versions(Path(MAPPING_FILE), dry_run=dry_run)
    if tagged:
        console.print("Created/updated tags:", style="green")
        for t in tagged:
            name, tag = t.split(":", 1)
            console.print(f"  - {name} -> {tag}")


@cli.command("changed")
@click.option("--base", "base_ref", default=None, help="Base ref/sha to diff against")
@click.option("--head", "head_ref", default="HEAD", help="Head ref/sha to diff from")
@click.option("--format", "fmt", type=click.Choice(["json", "lines"]), default="json")
@click.option("--github-output", is_flag=True, help="Write GitHub Actions outputs")
@click.option(
    "--committed-only/--include-uncommitted",
    default=False,
    help="Only consider committed changes (default includes uncommitted)",
)
def changed_cmd(
    base_ref: Optional[str],
    head_ref: str,
    fmt: str,
    github_output: bool,
    committed_only: bool,
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
    files = list_changed_files(base, head, include_uncommitted=not committed_only)
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
def mirror_cmd(template_name: str) -> None:
    """
    Push the contents of templates/<name> to its upstream repository.

    Ensures the configured remote exists, then runs
    `git subtree push --prefix templates/<name> <remote> <branch>` to mirror
    the template subtree to the external repo/branch.
    """
    cfg = MAPPING_DATA.get(template_name)
    if not cfg:
        raise SystemExit(f"No mapping found for template: {template_name}")
    mirror_template(template_name, cfg)


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


@cli.command("check-python")
@click.argument("template_name", type=click.Choice(MAPPING_DATA.keys()))
@click.option("--fix", is_flag=True, help="Fix formatting issues automatically.")
def template_check_python_cmd(template_name: str, fix: bool) -> None:
    """Run Python validation checks on test directory."""
    template_dir = get_template_dir(template_name)
    run_python_checks(template_dir, fix)


@cli.command("check-javascript")
@click.argument("template_name", type=click.Choice(MAPPING_DATA.keys()))
@click.option("--fix", is_flag=True, help="Fix formatting issues automatically.")
def template_check_javascript_cmd(template_name: str, fix: bool) -> None:
    """Run JavaScript/TypeScript validation checks on test directory."""
    template_dir = get_template_dir(template_name)
    run_javascript_checks(template_dir, fix)


@cli.command("init-scripts")
@click.argument("template_name", type=click.Choice(MAPPING_DATA.keys()))
def init_python_scripts_cmd(template_name: str) -> None:
    """Initialize development scripts for a template (Python and JavaScript/TypeScript)."""
    template_dir = get_template_dir(template_name)
    console.print(f"Working directory: {template_dir}")
    init_python_scripts(template_name)
    init_package_json_scripts(template_name)


@cli.command("export-metrics")
@click.option(
    "--dry-run", is_flag=True, help="Do not send to PostHog; just print JSON."
)
@click.option(
    "--print", "print_json", is_flag=True, help="Print JSON results to stdout."
)
@click.option(
    "--backfill",
    is_flag=True,
    help="Send daily events for all days in the 14-day window.",
)
def export_metrics_cmd(dry_run: bool, print_json: bool, backfill: bool) -> None:
    """Export GitHub metrics for all configured template repositories.

    Requires GITHUB_TOKEN (or GITHUB_PAT). If not --dry-run, also requires
    POSTHOG_API_KEY and optionally POSTHOG_HOST.
    """
    gh_auth = GitHubAuth.from_env()
    metrics, events = get_all_events_for_export(
        MAPPING_DATA, github_auth=gh_auth, backfill=backfill
    )

    if print_json or dry_run:
        print(json.dumps(metrics))

    # Always print all events that will be/were sent
    if events:
        print(
            f"\n{'DRY RUN - Would send' if dry_run else 'Sending'} {len(events)} events:"
        )
        for event in events:
            template = event.properties.get("template", "unknown")
            print(
                f"  - {event.event_name} for {template}"
                + (f" at {event.timestamp}" if event.timestamp else "")
            )

    if not dry_run:
        for event in events:
            send_posthog_event(
                event.event_name,
                event.properties,
                timestamp=event.timestamp,
            )


@cli.command("check-workflows")
@click.argument("template_name", type=click.Choice(MAPPING_DATA.keys()))
def check_workflows_cmd(template_name: str) -> None:
    """Validate workflows for a single template's project."""
    template_dir = get_template_dir(template_name)
    validate_workflows(template_dir)


@cli.command(
    "all", context_settings={"ignore_unknown_options": True, "allow_extra_args": True}
)
@click.argument("command_name")
@click.option(
    "--continue-on-error",
    is_flag=True,
    help="Continue executing on other templates if one fails",
)
@click.pass_context
def all_cmd(ctx: click.Context, command_name: str, continue_on_error: bool) -> None:
    """Execute a command on all templates.

    Run any tmpl command across all configured templates. The template name
    will be automatically passed as the first argument to the command.

    Examples:
        tmpl all check-python --fix
        tmpl all mirror --continue-on-error
    """
    # Get any extra arguments passed to the command
    extra_args = ctx.args

    template_names = list(MAPPING_DATA.keys())

    if not template_names:
        console.print("No templates configured.", style="yellow")
        return

    extras_str = " ".join(extra_args) if extra_args else ""
    console.print(
        f"Running 'tmpl {command_name}{(' ' + extras_str) if extras_str else ''}' on {len(template_names)} templates..."
    )

    failed_templates = []

    for template_name in template_names:
        console.print(f"\n📁 Processing template: {template_name}", style="bold blue")

        # Invoke the target subcommand within the same Click app to preserve flag parsing
        args_for_cmd = [command_name, template_name, *extra_args]
        try:
            # Run the subcommand in-process; do not call sys.exit on errors
            cli.main(args=args_for_cmd, standalone_mode=False)
            console.print(f"✓ {template_name} completed successfully", style="green")

        except SystemExit as e:
            exit_code = int(e.code) if isinstance(e.code, int) else 1
            console.print(
                f"❌ {template_name} failed with exit code {exit_code}", style="red"
            )
            failed_templates.append(template_name)

            if not continue_on_error:
                console.print(
                    f"Stopping execution due to failure in {template_name}", style="red"
                )
                console.print(
                    "Use --continue-on-error to continue processing other templates",
                    style="yellow",
                )
                sys.exit(exit_code)

        except KeyboardInterrupt:
            console.print(
                f"\n🛑 Interrupted while processing {template_name}", style="yellow"
            )
            sys.exit(130)

    # Summary
    console.print("\n📊 Summary:", style="bold")
    successful_count = len(template_names) - len(failed_templates)
    console.print(
        f"✓ Successful: {successful_count}/{len(template_names)}", style="green"
    )

    if failed_templates:
        console.print(
            f"❌ Failed: {len(failed_templates)}/{len(template_names)}", style="red"
        )
        console.print("Failed templates:", style="red")
        for template in failed_templates:
            console.print(f"  - {template}", style="red")
        sys.exit(1)
    else:
        console.print("🎉 All templates processed successfully!", style="bold green")
