"""Template validation utilities."""

from __future__ import annotations

from pathlib import Path

from .copier_integration import parse_template_variables


def map_materialized_to_template_path(
    template_dir: Path, materialized_path: str
) -> str:
    """Map a materialized file path back to its template path for a given template."""
    path_parts: tuple[str, ...] = Path(materialized_path).parts

    variables = parse_template_variables(template_dir)
    project_name_snake = variables.get("project_name_snake", "test_proj")
    if (
        len(path_parts) >= 2
        and path_parts[0] == "src"
        and path_parts[1] == project_name_snake
    ):
        new_parts: tuple[str, ...] = ("src", "{{ project_name_snake }}") + path_parts[
            2:
        ]
        template_path: str = str(Path(*new_parts))
        jinja_path: str = template_path + ".jinja"
        if (template_dir / jinja_path).exists():
            return jinja_path
        return template_path

    jinja_path = materialized_path + ".jinja"
    if (template_dir / jinja_path).exists():
        return jinja_path
    return materialized_path
