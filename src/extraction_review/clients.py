import logging
import os

from llama_cloud import AsyncLlamaCloud

logger = logging.getLogger(__name__)

# deployed agents may infer their name from the deployment name
agent_name = os.getenv("LLAMA_DEPLOY_DEPLOYMENT_NAME")
# required for all llama cloud calls
api_key = os.getenv("LLAMA_CLOUD_API_KEY")
# get this in case running against a different environment than production
base_url = os.getenv("LLAMA_CLOUD_BASE_URL")
project_id = os.getenv("LLAMA_DEPLOY_PROJECT_ID")


def get_llama_cloud_client() -> AsyncLlamaCloud:
    """Cloud services connection for file storage and processing."""
    return AsyncLlamaCloud(
        api_key=api_key,
        base_url=base_url,
        default_headers={"Project-Id": project_id} if project_id else {},
    )
