"""Configuration management for tmpl."""

from .mapping import MAPPING_DATA, TemplatesMapping, load_mapping
from .settings import MAPPING_FILE

__all__ = ["MAPPING_DATA", "TemplatesMapping", "load_mapping", "MAPPING_FILE"]
