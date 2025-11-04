"""
Selects a locally defined shema, or queries the remote extraction agent for the schema.
"""

import asyncio
import jsonref
from .clients import get_extract_agent
from .config import USE_REMOTE_EXTRACTION_SCHEMA, ExtractionSchema
from typing import Any, Type
from pydantic import BaseModel
from pydantic import create_model, Field


SCHEMA: Type[BaseModel] | None = (
    None if USE_REMOTE_EXTRACTION_SCHEMA else ExtractionSchema
)


_schema_lock = asyncio.Lock()


async def get_extraction_schema() -> Type[BaseModel]:
    global SCHEMA
    if SCHEMA is not None:
        return SCHEMA
    async with _schema_lock:
        if SCHEMA is not None:
            return SCHEMA
        agent = get_extract_agent()
        SCHEMA = model_from_schema(agent.data_schema)
        return SCHEMA


async def get_extraction_schema_json() -> dict[str, Any]:
    json_schema = (await get_extraction_schema()).model_json_schema()
    json_schema = jsonref.replace_refs(json_schema, proxies=False)
    return json_schema


def model_from_schema(schema: dict[str, Any]) -> Type[BaseModel]:
    """
    Converts a JSON schema back to a Pydantic model.
    """
    typemap = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "array": list,
        "object": dict,
    }
    fields = {}
    for prop, meta in schema.get("properties", {}).items():
        py_type = typemap.get(meta.get("type"), Any)
        default = ... if prop in schema.get("required", []) else None
        fields[prop] = (py_type, Field(default, description=meta.get("description")))
    return create_model(schema.get("title", "DynamicModel"), **fields)
