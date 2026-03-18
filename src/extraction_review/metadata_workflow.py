from typing import Annotated, Any

from workflows import Workflow, step
from workflows.events import StartEvent, StopEvent
from workflows.resource import Resource, ResourceConfig

from .config import EXTRACTED_DATA_COLLECTION, ExtractConfig, create_union_schema

DISCRIMINATOR_FIELD = "document_type"


class MetadataResponse(StopEvent):
    json_schema: dict[str, Any]
    schemas: dict[str, dict[str, Any]]
    discriminator_field: str
    extracted_data_collection: str


async def get_presentation_schema(
    extract_10k: Annotated[
        ExtractConfig,
        ResourceConfig(
            config_file="configs/config.json",
            path_selector="extract-10k",
            label="10-K Extraction",
        ),
    ],
    extract_10q: Annotated[
        ExtractConfig,
        ResourceConfig(
            config_file="configs/config.json",
            path_selector="extract-10q",
            label="10-Q Extraction",
        ),
    ],
    extract_8k: Annotated[
        ExtractConfig,
        ResourceConfig(
            config_file="configs/config.json",
            path_selector="extract-8k",
            label="8-K Extraction",
        ),
    ],
    extract_other: Annotated[
        ExtractConfig,
        ResourceConfig(
            config_file="configs/config.json",
            path_selector="extract-other",
            label="Other Extraction",
        ),
    ],
) -> dict[str, Any]:
    schemas = {
        "10-K": extract_10k.json_schema,
        "10-Q": extract_10q.json_schema,
        "8-K": extract_8k.json_schema,
        "other": extract_other.json_schema,
    }
    union = create_union_schema(schemas, discriminator_field=DISCRIMINATOR_FIELD)
    return {
        "json_schema": union,
        "schemas": schemas,
        "discriminator_field": DISCRIMINATOR_FIELD,
    }


class MetadataWorkflow(Workflow):
    """Provide extraction schema and configuration to the workflow editor."""

    @step
    async def get_metadata(
        self,
        _: StartEvent,
        presentation: Annotated[dict[str, Any], Resource(get_presentation_schema)],
    ) -> MetadataResponse:
        """Return the data schemas and storage settings for the review interface."""
        return MetadataResponse(
            json_schema=presentation["json_schema"],
            schemas=presentation["schemas"],
            discriminator_field=presentation["discriminator_field"],
            extracted_data_collection=EXTRACTED_DATA_COLLECTION,
        )


workflow = MetadataWorkflow(timeout=None)
