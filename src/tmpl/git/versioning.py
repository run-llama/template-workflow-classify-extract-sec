from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from packaging.version import Version

from ..config import TemplatesMapping


def detect_changed_templates(
    *,
    head_ref: str,
    base_ref: Optional[str],
    include_uncommitted: bool = True,
    detect_base_ref_func,
    list_changed_files_func,
    templates_from_files_func,
    mapping_keys: List[str],
) -> List[str]:
    head = head_ref
    base = base_ref or detect_base_ref_func(head)
    files = list_changed_files_func(base, head, include_uncommitted=include_uncommitted)
    return templates_from_files_func(files, mapping_keys)


def bump_version_string(current: Optional[str], bump: str) -> str:
    ver = Version(current) if current else Version("0.0.0")
    major, minor, patch = ver.major, ver.minor, ver.micro
    if bump == "major":
        major += 1
        minor = 0
        patch = 0
    elif bump == "minor":
        minor += 1
        patch = 0
    elif bump == "patch":
        patch += 1
    return f"{major}.{minor}.{patch}"


def apply_version_bumps(
    mapping: Dict[str, TemplatesMapping],
    decisions: Dict[str, str],
) -> Dict[str, TemplatesMapping]:
    # Deep-copy mapping entries so original mapping remains unchanged
    updated: Dict[str, TemplatesMapping] = {k: dict(v) for k, v in mapping.items()}  # type: ignore[dict-item]
    for name, action in decisions.items():
        if action == "ignore":
            continue
        if name not in updated:
            continue
        new_version = bump_version_string(updated[name].get("version"), action)
        updated[name]["version"] = new_version  # type: ignore[index]
    return updated


def save_mapping_versions(mapping: Dict[str, TemplatesMapping], path: Path) -> None:
    from ..config.mapping import save_mapping  # avoid cycle on import

    save_mapping(path, mapping)
