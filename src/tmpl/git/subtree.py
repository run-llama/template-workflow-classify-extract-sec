"""Git subtree operations for template management."""

from __future__ import annotations

from pathlib import Path
from typing import Dict

from ..config import TemplatesMapping
from ..utils import run
from .operations import ensure_remote


def mirror_template(template_name: str, config: TemplatesMapping) -> None:
    """Push the contents of templates/<name> to its upstream repository."""
    remote = config.get("remote")
    url = config.get("url")
    branch = config.get("branch", "main")
    if not remote or not url:
        raise SystemExit(f"Template {template_name} missing 'remote' or 'url'")
    
    # Ensure the git remote exists and is pointed at the correct URL
    ensure_remote(remote, url)
    prefix = f"templates/{template_name}"
    run(["git", "subtree", "push", "--prefix", prefix, remote, branch])


def merge_template(template_name: str, config: TemplatesMapping) -> None:
    """Merge upstream changes into templates/<name> from its configured remote."""
    remote = config.get("remote")
    url = config.get("url")
    branch = config.get("branch", "main")
    if not remote or not url:
        raise SystemExit(f"Template {template_name} missing 'remote' or 'url'")
    
    ensure_remote(remote, url)
    prefix = f"templates/{template_name}"
    run(["git", "subtree", "pull", "--prefix", prefix, remote, branch, "--squash"])


def clone_templates(mapping_data: Dict[str, TemplatesMapping]) -> None:
    """Add all configured templates under templates/ via git subtree (initial import)."""
    root = Path.cwd()
    templates_dir = root / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    
    for name, cfg in mapping_data.items():
        url = cfg.get("url")
        remote = cfg.get("remote")
        branch = cfg.get("branch", "main")
        if not url or not remote:
            print(f"Skipping {name}: missing remote or url")
            continue
        
        # Ensure the git remote exists and is pointed at the correct URL
        ensure_remote(remote, url)
        prefix = f"templates/{name}"
        dest = templates_dir / name
        if dest.exists():
            print(f"Exists: {dest}")
            continue
        
        # Add the upstream template as a subtree under templates/<name>
        run(["git", "subtree", "add", "--prefix", prefix, remote, branch, "--squash"])
