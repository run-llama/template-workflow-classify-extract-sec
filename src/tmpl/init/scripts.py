"""Initialize Python development scripts and tooling for templates."""

from __future__ import annotations

import json
import subprocess
from typing import cast

import tomlkit

from ..templates import get_template_dir
from ..utils import console


def init_python_scripts(template_name: str) -> None:
    """Initialize Python scripts for a template.

    This function:
    1. Adds development dependencies (ty, pytest, ruff, hatch) using uv
    2. Configures hatch commands in pyproject.toml for common development tasks
    """
    template_dir = get_template_dir(template_name)
    pyproject_path = template_dir / "pyproject.toml"

    if not pyproject_path.exists():
        console.print(f"❌ No pyproject.toml found in {template_dir}", style="bold red")
        return

    console.print(f"📦 Adding development dependencies to {template_name}")

    # Add development dependencies using uv
    try:
        subprocess.run(
            ["uv", "add", "--dev", "ty", "pytest", "ruff", "hatch"],
            cwd=template_dir,
            check=True,
            capture_output=True,
            text=True,
        )
        console.print("✓ Development dependencies added", style="green")
    except subprocess.CalledProcessError as e:
        console.print(f"❌ Failed to add dependencies: {e.stderr}", style="bold red")
        return

    # Modify pyproject.toml to add hatch commands
    console.print("⚙️  Configuring hatch commands in pyproject.toml")

    try:
        with open(pyproject_path, "r", encoding="utf-8") as f:
            doc = tomlkit.load(f)

        # Ensure tool.hatch.envs.default.scripts section exists
        scripts = get_table(["tool", "hatch", "envs", "default", "scripts"], doc)

        hatch_commands = {
            "format": "ruff format .",
            "format-check": "ruff format --check .",
            "lint": "ruff check --fix .",
            "lint-check": ["ruff check ."],
            "typecheck": "ty check src",
            "test": "pytest",
            "all-check": ["format-check", "lint-check", "test"],
            "all-fix": ["format", "lint", "test"],
        }

        for cmd, value in hatch_commands.items():
            scripts[cmd] = value

        set_table(["tool", "hatch", "envs", "default", "scripts"], doc, scripts)

        # Write back to file
        with open(pyproject_path, "w", encoding="utf-8") as f:
            tomlkit.dump(doc, f)

        console.print("✓ Hatch commands configured", style="green")
        console.print("Available commands:", style="bold")
        for cmd in hatch_commands:
            console.print(f"  • hatch run {cmd}")

    except Exception as e:
        console.print(f"❌ Failed to configure hatch commands: {e}", style="bold red")


def get_table(path: list[str], doc: tomlkit.TOMLDocument) -> tomlkit.TOMLDocument:
    """Get a table from a path in a tomlkit document."""
    for p in path:
        doc = cast(tomlkit.TOMLDocument, doc.get(p, tomlkit.table()))
    return doc


def set_table(
    path: list[str], doc: tomlkit.TOMLDocument, value: tomlkit.TOMLDocument
) -> None:
    """Set a table in a path in a tomlkit document."""
    for p in path[:-1]:
        value = cast(tomlkit.TOMLDocument, doc.get(p, tomlkit.table()))
        doc[p] = value
        doc = value
    doc[path[-1]] = value


def init_package_json_scripts(template_name: str) -> None:
    """Initialize JavaScript/TypeScript scripts for a template.

    This function:
    1. Adds development dependencies (prettier, typescript) using pnpm
    2. Configures npm scripts in package.json for common development tasks
    """
    template_dir = get_template_dir(template_name)
    package_json_path = template_dir / "ui" / "package.json"

    if not package_json_path.exists():
        console.print(f"❌ No package.json found in {template_dir}", style="bold red")
        return

    console.print(f"📦 Adding development dependencies to {template_name}")

    # Add development dependencies using pnpm
    try:
        subprocess.run(
            ["pnpm", "add", "--dev", "prettier", "typescript"],
            cwd=template_dir,
            check=True,
            capture_output=True,
            text=True,
        )
        console.print("✓ Development dependencies added", style="green")
    except subprocess.CalledProcessError as e:
        console.print(f"❌ Failed to add dependencies: {e.stderr}", style="bold red")
        return

    # Modify package.json to add npm scripts
    console.print("⚙️  Configuring npm scripts in package.json")

    try:
        with open(package_json_path, "r", encoding="utf-8") as f:
            package_data = json.load(f)

        # Ensure scripts section exists
        if "scripts" not in package_data:
            package_data["scripts"] = {}

        scripts = package_data["scripts"]

        # Add the npm scripts
        npm_scripts = {
            "lint": "tsc --noEmit",
            "format": "prettier --write src",
            "format-check": "prettier --check src",
            "all-check": "pnpm i && pnpm run lint && pnpm run format-check && pnpm run build",
            "all-fix": "pnpm i && pnpm run lint && pnpm run format && pnpm run build",
        }

        for cmd, value in npm_scripts.items():
            scripts[cmd] = value

        # Write back to file with proper formatting
        with open(package_json_path, "w", encoding="utf-8") as f:
            json.dump(package_data, f, indent=2, ensure_ascii=False)
            f.write("\n")  # Add trailing newline

        console.print("✓ npm scripts configured", style="green")
        console.print("Available commands:", style="bold")
        for cmd in npm_scripts:
            console.print(f"  • pnpm run {cmd}")

    except Exception as e:
        console.print(f"❌ Failed to configure npm scripts: {e}", style="bold red")
