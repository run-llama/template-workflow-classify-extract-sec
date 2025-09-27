"""Basic git operations."""

from __future__ import annotations

import subprocess

from ..utils import git_output, run


def ensure_remote(name: str, url: str) -> None:
    """Ensure a git remote exists with the correct URL."""

    try:
        current = git_output(["remote", "get-url", name])
    except subprocess.CalledProcessError:
        current = None
    if current is None:
        print(f"Adding missing remote {name} -> {url}")
        run(["git", "remote", "add", name, url])
    elif current != url:
        print(f"Updating remote {name} url to {url}")
        run(["git", "remote", "set-url", name, url])
    else:
        print(f"Remote {name} already configured correctly")
