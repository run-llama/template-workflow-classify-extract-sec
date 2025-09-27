"""Template mapping configuration management."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, TypedDict

import yaml

from .settings import MAPPING_FILE


class TemplatesMapping(TypedDict):
    """Configuration for a template mapping."""

    remote: str  # tpl-wf-document-qa
    url: str  # git@github.com:run-llama/template-workflow-document-qa.git
    branch: str  # main


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
        )
    return templates


# Load the global mapping data
MAPPING_DATA = load_mapping(Path(MAPPING_FILE))
