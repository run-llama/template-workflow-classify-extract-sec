"""Configuration management for tmpl."""

from .mapping import (
    MAPPING_DATA,
    TemplatesMapping,
    _load_mapping,
    get_mapping_data,
    get_mapping_write_path,
)

__all__ = [
    "MAPPING_DATA",
    "TemplatesMapping",
    "_load_mapping",
    "get_mapping_data",
    "get_mapping_write_path",
]
