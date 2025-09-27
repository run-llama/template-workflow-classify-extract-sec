"""Subprocess utilities for running commands."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from .console import console


def run(command: List[str], cwd: Optional[Path] = None) -> None:
    """Run a command and stream output to stdout."""
    process = subprocess.Popen(
        command,
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    assert process.stdout is not None
    for line in process.stdout:
        sys.stdout.write(line)
    code = process.wait()
    if code:
        raise SystemExit(code)


def git_output(args: List[str]) -> str:
    """Run a git command and return its output."""
    return subprocess.check_output(["git", *args], text=True).strip()


def run_git_command(
    cmd: List[str], cwd: Optional[Path] = None
) -> subprocess.CompletedProcess[str]:
    """Run a git command and return the result."""
    console.print(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, check=True
        )
        return result
    except subprocess.CalledProcessError as e:
        console.print(f"Command failed with exit code {e.returncode}", style="bold red")
        console.print(f"stdout: {e.stdout}", style="bold yellow")
        console.print(f"stderr: {e.stderr}", style="bold yellow")
        raise SystemExit(1)
