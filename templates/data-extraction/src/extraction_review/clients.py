import functools
import os
from typing import Any
import httpx

from llama_cloud_services import ExtractionAgent, LlamaExtract
from llama_cloud_services.extract import ExtractConfig, ExtractMode
from llama_cloud.core.api_error import ApiError
from llama_cloud_services.beta.agent_data import AsyncAgentDataClient, ExtractedData
from llama_cloud.client import AsyncLlamaCloud
import logging

from extraction_review.config import (
    EXTRACTED_DATA_COLLECTION,
    EXTRACTION_AGENT_NAME,
    USE_REMOTE_EXTRACTION_SCHEMA,
    ExtractionSchema,
)

logger = logging.getLogger(__name__)

# deployed agents may infer their name from the deployment name
# Note: Make sure that an agent deployment with this name actually exists
# otherwise calls to get or set data will fail. You may need to adjust the `or `
# name for development
agent_name = os.getenv("LLAMA_DEPLOY_DEPLOYMENT_NAME")
# required for all llama cloud calls
api_key = os.environ["LLAMA_CLOUD_API_KEY"]
# get this in case running against a different environment than production
base_url = os.getenv("LLAMA_CLOUD_BASE_URL")
project_id = os.getenv("LLAMA_DEPLOY_PROJECT_ID")


@functools.lru_cache(maxsize=None)
def get_extract_agent() -> ExtractionAgent:
    extract_api = LlamaExtract(
        api_key=api_key, base_url=base_url, project_id=project_id
    )
    config = ExtractConfig(
        extraction_mode=ExtractMode.PREMIUM,
        system_prompt=None,
        # advanced
        use_reasoning=False,
        cite_sources=False,
        confidence_scores=True,
    )
    try:
        existing = extract_api.get_agent(EXTRACTION_AGENT_NAME)
        if not USE_REMOTE_EXTRACTION_SCHEMA:
            existing.data_schema = ExtractionSchema
        existing.config = config
        return existing
    except ApiError as e:
        if e.status_code == 404:
            if USE_REMOTE_EXTRACTION_SCHEMA:
                logger.warning(
                    "Extraction agent does not exist, creating a new one from the local schema"
                )
            return extract_api.create_agent(
                name=EXTRACTION_AGENT_NAME, data_schema=ExtractionSchema, config=config
            )
        else:
            raise


@functools.lru_cache(maxsize=None)
def get_data_client() -> AsyncAgentDataClient:
    return AsyncAgentDataClient(
        deployment_name=agent_name,
        collection=EXTRACTED_DATA_COLLECTION,
        type=ExtractedData[Any],
        client=get_llama_cloud_client(),
    )


@functools.lru_cache(maxsize=None)
def get_llama_cloud_client():
    return AsyncLlamaCloud(
        base_url=base_url,
        token=api_key,
        httpx_client=httpx.AsyncClient(
            timeout=60, headers={"Project-Id": project_id} if project_id else None
        ),
    )
