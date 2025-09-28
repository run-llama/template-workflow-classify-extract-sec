"""Validation checks for tmpl."""

from .python import run_python_checks
from .javascript import run_javascript_checks
from .workflows import validate_workflows

__all__ = ["run_python_checks", "run_javascript_checks", "validate_workflows"]
