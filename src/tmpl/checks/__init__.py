"""Validation checks for tmpl."""

from .python import run_python_checks
from .javascript import run_javascript_checks

__all__ = ["run_python_checks", "run_javascript_checks"]
