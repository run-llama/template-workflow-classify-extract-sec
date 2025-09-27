"""Jinja rendering utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Dict

from copier._template import Template


def render_jinja_string(
    template_string: str, variables: Dict[str, str], template_dir: Path
) -> str:
    """Render a Jinja template string using Copier's configuration for a template dir."""
    template = Template(url=str(template_dir))

    import jinja2  # local import to avoid hard dependency at import time

    jinja_env = jinja2.Environment(
        loader=jinja2.BaseLoader(),
        extensions=template.jinja_extensions,
        **template.envops,
    )

    return jinja_env.from_string(template_string).render(**variables)
