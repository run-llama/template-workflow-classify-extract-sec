"""Template mapping configuration management."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, TypedDict, Optional

import yaml

from .settings import MAPPING_FILE


class TemplatesMapping(TypedDict):
    """Configuration for a template mapping."""

    remote: str  # tpl-wf-document-qa
    url: str  # git@github.com:run-llama/template-workflow-document-qa.git
    branch: str  # main
    version: Optional[str]  # semantic version string like 1.2.3


def load_mapping(path: Path) -> Dict[str, TemplatesMapping]:
    """Load template mappings from a YAML file."""
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    templates = data.get("templates", {})
    assert isinstance(templates, dict)
    for k, v in templates.items():
        templates[k] = TemplatesMapping(
            remote=v["remote"],
            url=v["url"],
            branch=v["branch"],
            version=v.get("version"),
        )
    return templates


def save_mapping(path: Path, mapping: Dict[str, TemplatesMapping]) -> None:
    """Persist template mappings to the YAML file.

    Writes the `templates` section with keys: remote, url, branch, and optional version.
    """
    data: Dict[str, Dict[str, Dict[str, str]]] = {"templates": {}}
    for name, cfg in mapping.items():
        entry: Dict[str, str] = {
            "remote": cfg.get("remote", ""),
            "url": cfg.get("url", ""),
            "branch": cfg.get("branch", "main"),
        }
        version = cfg.get("version")
        if version:
            entry["version"] = version
        data["templates"][name] = entry

    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False)


# Load the global mapping data
MAPPING_DATA = load_mapping(Path(MAPPING_FILE))
