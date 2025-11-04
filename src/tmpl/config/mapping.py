"""Template mapping configuration management.

Non-configurable mapping discovery:
- Discover a workspace mapping file by walking up from this module's path,
  looking for `.github/templates-remotes.yml`.
- If not found (e.g., installed non-editable), fall back to an embedded
  default mapping bundled with the package.
- Expose a memoized getter so callers can treat it like a constant.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, TypedDict, Optional, cast
from functools import lru_cache
from importlib.resources import files

import yaml


class TemplatesMapping(TypedDict):
    """Configuration for a template mapping."""

    remote: str  # tpl-wf-document-qa
    url: str  # git@github.com:run-llama/template-workflow-document-qa.git
    branch: str  # main
    version: Optional[str]  # semantic version string like 1.2.3


def _parse_mapping_dict(data: dict[str, object]) -> dict[str, TemplatesMapping]:
    templates_section = data.get("templates", {})
    assert isinstance(templates_section, dict)
    out: dict[str, TemplatesMapping] = {}
    for k, v in templates_section.items():
        v = cast(dict[str, Any], v)
        remote = v["remote"]
        assert isinstance(remote, str)
        url = v["url"]
        assert isinstance(url, str)
        branch = v["branch"]
        assert isinstance(branch, str)
        version = v.get("version")
        assert isinstance(version, str) or version is None
        assert isinstance(k, str), "Key of mapping must be a string"
        out[k] = TemplatesMapping(
            remote=remote,
            url=url,
            branch=branch,
            version=version,
        )
    return out


def _load_mapping(path: Path) -> Dict[str, TemplatesMapping]:
    """Load template mappings from a YAML file path."""
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    assert isinstance(data, dict)
    return _parse_mapping_dict(data)


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


def load_bundled_mapping() -> Dict[str, TemplatesMapping]:
    """Load the bundled default mapping from the package resources."""
    try:
        mapping_file = files("tmpl.config").joinpath("templates-remotes.yml")
        content = mapping_file.read_text(encoding="utf-8")
        data = yaml.safe_load(content) or {}
        assert isinstance(data, dict)
        return _parse_mapping_dict(data)
    except Exception:
        # If bundled file is not available, return empty mapping
        return {}


def discover_repo_mapping_path() -> Optional[Path]:
    """Discover the repository mapping file path by walking parents.

    Returns a Path if `.github/templates-remotes.yml` exists relative to any
    parent of this module; otherwise returns None.
    """
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / ".github" / "templates-remotes.yml"
        if candidate.exists():
            return candidate
    return None


@lru_cache(maxsize=1)
def get_mapping_data() -> Dict[str, TemplatesMapping]:
    """Return template mapping data, discovered or default (memoized)."""
    repo_path = discover_repo_mapping_path()
    if repo_path is not None:
        return _load_mapping(repo_path)
    # Fallback to bundled mapping file
    return load_bundled_mapping()


def get_mapping_write_path() -> Path:
    """Return the path to write the mapping file.

    Raises if no repository mapping file can be discovered.
    """
    repo_path = discover_repo_mapping_path()
    if repo_path is None:
        raise RuntimeError(
            "Unable to locate repository mapping file for write: .github/templates-remotes.yml"
        )
    return repo_path


# Load the global mapping data via the memoized getter
MAPPING_DATA = get_mapping_data()
