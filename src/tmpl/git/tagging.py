from __future__ import annotations

from typing import Dict, List, Optional

from ..config import TemplatesMapping, get_mapping_data
from ..utils import git_output, run
from ..utils.console import console


def ensure_remote(remote: str, url: str) -> None:
    """Ensure the remote exists without emitting error noise if missing."""
    try:
        git_output(["remote", "get-url", remote])
    except Exception:
        run(["git", "remote", "add", remote, url])


def compute_subtree_split(prefix: str, branch: str) -> str:
    return git_output(["subtree", "split", "--prefix", prefix, branch])


def get_remote_tag_hash(remote: str, tag_name: str) -> Optional[str]:
    """Return the hash of a tag on a remote, if present."""
    try:
        out = git_output(["ls-remote", "--tags", remote, tag_name])
        if not out:
            return None
        lines = out.splitlines()
        # Prefer peeled entry (annotated tags): refs/tags/<tag>^{}
        for line in lines:
            if line.endswith(f"refs/tags/{tag_name}^{{}}"):
                return line.split()[0]
        # Fallback to the first line (lightweight tags or annotated without peeled)
        first = lines[0]
        return first.split()[0] if first else None
    except Exception:
        return None


def remote_has_tag(remote: str, tag_name: str) -> bool:
    return get_remote_tag_hash(remote, tag_name) is not None


def push_tag_to_remote(remote: str, commit: str, tag_name: str) -> None:
    run(["git", "push", remote, f"{commit}:refs/tags/{tag_name}", "-f"])


def tag_all_versions(
    mapping: Dict[str, TemplatesMapping], dry_run: bool = False
) -> List[str]:
    """Create missing tags on remotes for all templates.

    Returns a list of "name:tag" strings created. Aggregates errors per-template
    and continues; callers should check for errors via exceptions from run_tag_versions.
    """
    tagged: List[str] = []
    errors: List[str] = []

    for name, cfg in mapping.items():
        try:
            version = cfg.get("version")
            if not version:
                continue
            remote = cfg.get("remote")
            url = cfg.get("url")
            branch = cfg.get("branch", "main")
            if not remote or not url:
                console.print(
                    f"Skipping {name}: missing remote or url in mapping", style="yellow"
                )
                continue

            console.print(
                f"\n🔖 Tagging {name}: version=v{version} remote={remote} url={url} branch={branch}",
                style="bold",
            )
            ensure_remote(remote, url)
            console.print("Fetching remote branch...")
            # Ensure objects (including the configured branch and tags) from the subtree
            # remote are present locally.
            run(["git", "fetch", remote, branch])

            tag_name = f"v{version}"
            prefix = f"templates/{name}"
            commit = compute_subtree_split(prefix, branch)
            console.print(
                f"Computed subtree split for {prefix} on {branch}: {commit}",
                style="dim",
            )

            existing_hash = get_remote_tag_hash(remote, tag_name)
            if existing_hash:
                # Detailed diagnostics when tag already exists on remote
                console.print(
                    f"Remote {remote} tag {tag_name} = {existing_hash}", style="dim"
                )
                console.print(f"Computed subtree commit = {commit}", style="dim")

                if existing_hash != commit:
                    console.print(
                        (
                            f"⚠️  {name}: remote tag {tag_name} points to a different commit than the current subtree split.\n"
                            f"   This likely indicates unversioned changes or a missing version bump.\n"
                            f"   Skipping push to avoid clobbering an existing tag."
                        ),
                        style="yellow",
                    )
                else:
                    console.print(
                        f"✓ {name}: remote tag matches computed subtree commit",
                        style="green",
                    )
                # Skip pushing if tag exists; behavior unchanged.
                continue

            if dry_run:
                console.print(
                    f"DRY-RUN: would push tag {tag_name} -> {commit} to {remote}",
                    style="cyan",
                )
                tagged.append(f"{name}:{tag_name}")
            else:
                console.print(
                    f"Pushing tag {tag_name} -> {commit} to {remote}", style="cyan"
                )
                push_tag_to_remote(remote, commit, tag_name)
                tagged.append(f"{name}:{tag_name}")
                console.print(
                    f"✓ Created {tag_name} on {remote} at {commit}", style="green"
                )

        except SystemExit as e:
            code = int(e.code) if isinstance(e.code, int) else 1
            errors.append(
                f"{name}: failed with exit code {code} while tagging v{cfg.get('version')} on {cfg.get('remote') or 'unknown remote'}"
            )
            # Continue to next template
        except Exception as e:  # safeguard
            errors.append(f"{name}: unexpected error: {e}")

    if errors:
        console.print(
            "\n⚠️  One or more tagging operations encountered errors:",
            style="bold yellow",
        )
        for err in errors:
            console.print(f"  - {err}", style="yellow")
        # Do not fail the overall command; provide diagnostics only.

    return tagged


def run_tag_versions(dry_run: bool = False) -> List[str]:
    mapping = get_mapping_data()
    return tag_all_versions(mapping, dry_run=dry_run)
