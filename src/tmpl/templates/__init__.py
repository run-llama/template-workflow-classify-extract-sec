"""Template management for tmpl."""

from .copier_integration import parse_template_variables, run_copier_quietly
from .jinja_utils import render_jinja_string
from .manager import get_template_dir, regenerate_test_proj, ensure_test_proj_exists
from .validation import map_materialized_to_template_path

__all__ = [
    "parse_template_variables",
    "run_copier_quietly", 
    "render_jinja_string",
    "get_template_dir",
    "regenerate_test_proj",
    "ensure_test_proj_exists",
    "map_materialized_to_template_path",
]
