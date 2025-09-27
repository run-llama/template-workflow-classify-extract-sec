"""Git operations for tmpl."""

from .changes import detect_base_ref, list_changed_files, templates_from_files
from .operations import ensure_remote
from .subtree import clone_templates, merge_template, mirror_template

__all__ = [
    "detect_base_ref",
    "list_changed_files",
    "templates_from_files",
    "ensure_remote",
    "clone_templates",
    "merge_template",
    "mirror_template",
]
