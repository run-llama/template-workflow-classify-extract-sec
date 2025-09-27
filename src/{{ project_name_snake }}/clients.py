import functools
import os
import httpx

from llama_cloud.client import AsyncLlamaCloud
from llama_cloud_services import LlamaCloudIndex, LlamaParse
from llama_cloud_services.parse import ResultType

# deployed agents may infer their name from the deployment name
# Note: Make sure that an agent deployment with this name actually exists
# otherwise calls to get or set data will fail. You may need to adjust the `or `
# name for development
DEPLOYMENT_NAME = os.getenv("LLAMA_DEPLOY_DEPLOYMENT_NAME")
# required for all llama cloud calls
LLAMA_CLOUD_API_KEY = os.environ["LLAMA_CLOUD_API_KEY"]
# get this in case running against a different environment than production
LLAMA_CLOUD_BASE_URL = os.getenv("LLAMA_CLOUD_BASE_URL")
LLAMA_CLOUD_PROJECT_ID = os.getenv("LLAMA_DEPLOY_PROJECT_ID")
INDEX_NAME = "document_qa_index"


@functools.cache
def get_base_cloud_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=60,
        headers={"Project-Id": LLAMA_CLOUD_PROJECT_ID}
        if LLAMA_CLOUD_PROJECT_ID
        else None,
    )


@functools.cache
def get_llama_cloud_client() -> AsyncLlamaCloud:
    return AsyncLlamaCloud(
        base_url=LLAMA_CLOUD_BASE_URL,
        token=LLAMA_CLOUD_API_KEY,
        httpx_client=get_base_cloud_client(),
    )


@functools.cache
def get_llama_parse_client() -> LlamaParse:
    return LlamaParse(
        parse_mode="parse_page_with_agent",
        model="openai-gpt-4-1-mini",
        high_res_ocr=True,
        adaptive_long_table=True,
        outlined_table_extraction=True,
        output_tables_as_HTML=True,
        result_type=ResultType.MD,
        api_key=LLAMA_CLOUD_API_KEY,
        project_id=LLAMA_CLOUD_PROJECT_ID,
        custom_client=get_base_cloud_client(),
    )


@functools.lru_cache(maxsize=None)
def get_index(index_name: str) -> LlamaCloudIndex:
    return LlamaCloudIndex.create_index(
        name=index_name,
        project_id=LLAMA_CLOUD_PROJECT_ID,
        api_key=LLAMA_CLOUD_API_KEY,
        base_url=LLAMA_CLOUD_BASE_URL,
        show_progress=True,
        custom_client=get_base_cloud_client(),
    )
