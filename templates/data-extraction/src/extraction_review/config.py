"""
For simple configuration of the extraction review application, just customize this file.

If you need more control, feel free to edit the rest of the application
"""

from __future__ import annotations
import os
from typing import Type

from llama_cloud import ExtractConfig
from llama_cloud_services.extract import ExtractMode
from pydantic import BaseModel, Field

# If you change this to true, the schema and extraction configuration will be fetched from the remote extraction agent
# rather than using the ExtractionSchema and configuration defined below.
USE_REMOTE_EXTRACTION_SCHEMA: bool = False
# The name of the extraction agent to use. Prefers the name of this deployment when deployed to isolate environments.
# Note that the application will create a new agent from the below ExtractionSchema if the extraction agent does not yet exist.
EXTRACTION_AGENT_NAME: str = (
    os.getenv("LLAMA_DEPLOY_DEPLOYMENT_NAME") or "extraction-review"
)
# The name of the collection to use for storing extracted data. This will be qualified by the agent name.
# When developing locally, this will use the _public collection (shared within the project), otherwise agent
# data is isolated to each agent
EXTRACTED_DATA_COLLECTION: str = "extraction-review"


# Modify this to match the fields you want extracted.
# - Use comments as prompts for the extraction agent.
# - Make fields optional or specify via a comment to provide a default value when the document may not contain
# the information.
# - Sub objects may be provided via sub-classes of BaseModel. Note that dicts are not supported: all available
#   fields must be defined
class ExtractionSchema(BaseModel):
    document_type: str = Field(
        description="An overarching category for the type of document (e.g. invoice, purchase order, etc.)"
    )
    summary: str = Field(
        description="A 2-3 sentence summary describing the content of the document"
    )
    key_points: list[str] = Field(
        description="A list of key points or insights from the document"
    )


# This is only used if USE_REMOTE_EXTRACTION_SCHEMA is False.
EXTRACT_CONFIG = ExtractConfig(
    extraction_mode=ExtractMode.PREMIUM,
    system_prompt=None,
    # advanced. Only compatible with Premium mode.
    use_reasoning=False,
    cite_sources=False,
    confidence_scores=True,
)


SCHEMA: Type[BaseModel] | None = (
    None if USE_REMOTE_EXTRACTION_SCHEMA else ExtractionSchema
)
