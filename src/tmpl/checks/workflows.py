"""Workflow validation checks."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple
import tomllib
from ..utils import console


def _read_pyproject(path: Path) -> Dict:
    with path.open("rb") as fp:
        return tomllib.load(fp)


def _extract_workflows(doc: Dict) -> Dict[str, str]:
    tool = doc.get("tool", {})
    if "llamactl" in tool and isinstance(tool["llamactl"], dict):
        wf = tool["llamactl"].get("workflows", {})
        if isinstance(wf, dict):
            return wf  # type: ignore[return-value]
    if "llamadeploy" in tool and isinstance(tool["llamadeploy"], dict):
        wf = tool["llamadeploy"].get("workflows", {})
        if isinstance(wf, dict):
            return wf  # type: ignore[return-value]
    return {}


def _collect_workflows_for_project(project_dir: Path) -> List[Tuple[str, str]]:
    pyproject_path = project_dir / "pyproject.toml"
    try:
        doc = _read_pyproject(pyproject_path)
    except Exception as e:
        raise SystemExit(f"Failed to parse {pyproject_path}: {e}")
    workflows = _extract_workflows(doc)
    results: List[Tuple[str, str]] = []
    for name, import_path in workflows.items():
        if not isinstance(import_path, str):
            continue
        results.append((name, import_path))
    return results


def validate_workflows(test_proj_dir: Path) -> None:
    """Validate all workflows for a single rendered project.

    - Discovers workflows in the project's pyproject under llamactl/llamadeploy
    - Imports the object and invokes its private _validate() method
    - Exits with error if any workflow fails
    """
    uv_path = shutil.which("uv")
    if uv_path is None:
        raise SystemExit(
            "uv not available; required to run within project dependencies"
        )

    workflows = _collect_workflows_for_project(test_proj_dir)
    assert workflows is not None, (
        f"Every project should have at least one workflow. None found for project {test_proj_dir.name}"
    )

    failures: List[str] = []

    # If more are needed, perhaps derive them from the project's .env.template by default
    env = os.environ.copy()
    env["LLAMA_CLOUD_API_KEY"] = os.getenv("LLAMA_CLOUD_API_KEY", "sk-fake***fake")

    for wf_name, import_path in workflows:
        code = f"""
import importlib, inspect
mod, attr = {import_path!r}.split(":", 1)
module = importlib.import_module(mod)
obj = getattr(module, attr)
if inspect.isclass(obj):
    try:
        wf = obj(timeout=None)
    except TypeError:
        wf = obj()
else:
    wf = obj
validate = getattr(wf, "_validate", None)
if not callable(validate):
    raise SystemExit("Workflow has no callable _validate() method")
validate()
"""

        cmd = [uv_path, "run", "python", "-c", code]
        proc = subprocess.run(
            cmd,
            env=env,
            cwd=str(test_proj_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=300,
            check=False,
        )
        if proc.returncode != 0:
            stdout = proc.stdout or ""
            failures.append(
                "\n".join(
                    [
                        "********************************************************************************",
                        f"Validation failed for {test_proj_dir.name}:{wf_name} -> {import_path}",
                        f"Command: {' '.join(map(shlex.quote, cmd))}",
                        "Output:",
                        stdout,
                    ]
                )
            )

    if failures:
        for msg in failures:
            console.print(msg, highlight=False)
        raise SystemExit(1)
    console.print("✓ Workflow validation passed", style="green")
