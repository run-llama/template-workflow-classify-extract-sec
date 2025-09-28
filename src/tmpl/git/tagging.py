from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from ..config import load_mapping, TemplatesMapping
from ..utils import git_output, run


def ensure_remote(remote: str, url: str) -> None:
    try:
        run(["git", "remote", "get-url", remote])
    except SystemExit:
        run(["git", "remote", "add", remote, url])


def compute_subtree_split(prefix: str, branch: str) -> str:
    return git_output(["subtree", "split", "--prefix", prefix, branch])


def remote_has_tag(remote: str, tag_name: str) -> bool:
    try:
        out = git_output(["ls-remote", "--tags", remote, tag_name])
        return bool(out)
    except Exception:
        return False


def push_tag_to_remote(remote: str, commit: str, tag_name: str) -> None:
    run(["git", "push", remote, f"{commit}:refs/tags/{tag_name}", "-f"])


def tag_all_versions(mapping: Dict[str, TemplatesMapping]) -> List[str]:
    tagged: List[str] = []
    for name, cfg in mapping.items():
        version = cfg.get("version")
        if not version:
            continue
        remote = cfg.get("remote")
        url = cfg.get("url")
        branch = cfg.get("branch", "main")
        if not remote or not url:
            continue

        ensure_remote(remote, url)
        # Ensure objects (including the configured branch and tags) from the subtree
        # remote are present locally. This avoids failures where `git subtree split`
        # references a prior split hash and needs objects from the subtree repo.
        run(["git", "fetch", remote, branch])
        run(["git", "fetch", remote, "--tags"])
        tag_name = f"v{version}"
        if remote_has_tag(remote, tag_name):
            continue

        prefix = f"templates/{name}"
        commit = compute_subtree_split(prefix, branch)
        push_tag_to_remote(remote, commit, tag_name)
        tagged.append(f"{name}:{tag_name}")
    return tagged


def run_tag_versions(mapping_path: Path | None = None) -> List[str]:
    from .. import config as cfg

    mapping_file = mapping_path or Path(cfg.MAPPING_FILE)
    mapping = load_mapping(mapping_file)
    return tag_all_versions(mapping)
