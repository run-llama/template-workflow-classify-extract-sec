from typing import Any
from workflows import Workflow, step
from workflows.events import StartEvent, StopEvent

import jsonref

from .config import EXTRACTED_DATA_COLLECTION, FILING_SCHEMAS


class MetadataResponse(StopEvent):
    schemas: dict[str, dict[str, Any]]
    extracted_data_collection: str


class MetadataWorkflow(Workflow):
    """
    Simple single step workflow to expose configuration to the UI, such as all JSON schemas and collection name.
    """

    @step
    async def get_metadata(self, _: StartEvent) -> MetadataResponse:
        # Convert all filing schemas to JSON schemas
        schemas = {}
        for filing_type, schema_class in FILING_SCHEMAS.items():
            json_schema = schema_class.model_json_schema()
            # Resolve any $ref references
            json_schema = jsonref.replace_refs(json_schema, proxies=False)
            schemas[filing_type] = json_schema

        return MetadataResponse(
            schemas=schemas,
            extracted_data_collection=EXTRACTED_DATA_COLLECTION,
        )


workflow = MetadataWorkflow(timeout=None)
