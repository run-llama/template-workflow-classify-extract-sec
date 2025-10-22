"""High-level template management operations."""

from __future__ import annotations


from pathlib import Path


def get_template_dir(template_name: str) -> Path:
    """Get the directory path for a template."""
    root = Path(__file__).parent.parent.parent.parent
    return root / "templates" / template_name
