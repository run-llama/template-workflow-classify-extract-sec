import asyncio
import hashlib
import logging
import os
from pathlib import Path
import tempfile
from typing import Any, Literal

import httpx
from llama_cloud import ExtractRun
from llama_cloud_services.extract import SourceText
from llama_cloud_services.beta.agent_data import ExtractedData, InvalidExtractionData
from workflows import Context, Workflow, step
from workflows.events import Event, StartEvent, StopEvent
from workflows.retry_policy import ConstantDelayRetryPolicy

from .config import get_llama_cloud_client, get_data_client, get_extract_agent
from .schemas import MySchema

logger = logging.getLogger(__name__)


class FileEvent(StartEvent):
    file_id: str


class DownloadFileEvent(Event):
    file_id: str


class FileDownloadedEvent(Event):
    file_id: str
    file_path: str
    filename: str


class UIToast(Event):
    level: Literal["info", "warning", "error"]
    message: str


class ExtractedEvent(Event):
    data: ExtractedData[MySchema]


class ExtractedInvalidEvent(Event):
    data: ExtractedData[dict[str, Any]]


class ProcessFileWorkflow(Workflow):
    """
    Given a file path, this workflow will process a single file through the custom extraction logic.
    """

    @step(retry_policy=ConstantDelayRetryPolicy(maximum_attempts=3, delay=10))
    async def run_file(self, event: FileEvent) -> DownloadFileEvent:
        logger.info(f"Running file {event.file_id}")
        return DownloadFileEvent(file_id=event.file_id)

    @step(retry_policy=ConstantDelayRetryPolicy(maximum_attempts=3, delay=10))
    async def download_file(
        self, event: DownloadFileEvent, ctx: Context
    ) -> FileDownloadedEvent:
        """Download the file reference from the cloud storage"""
        try:
            file_metadata = await get_llama_cloud_client().files.get_file(
                id=event.file_id
            )
            file_url = await get_llama_cloud_client().files.read_file_content(
                event.file_id
            )

            temp_dir = tempfile.gettempdir()
            filename = file_metadata.name
            file_path = os.path.join(temp_dir, filename)
            client = httpx.AsyncClient()
            # Report progress to the UI
            logger.info(f"Downloading file {file_url.url} to {file_path}")

            async with client.stream("GET", file_url.url) as response:
                with open(file_path, "wb") as f:
                    async for chunk in response.aiter_bytes():
                        f.write(chunk)
            logger.info(f"Downloaded file {file_url.url} to {file_path}")
            return FileDownloadedEvent(
                file_id=event.file_id, file_path=file_path, filename=filename
            )
        except Exception as e:
            logger.error(f"Error downloading file {event.file_id}: {e}", exc_info=True)
            ctx.write_event_to_stream(
                UIToast(
                    level="error",
                    message=f"Error downloading file {event.file_id}: {e}",
                )
            )
            raise e

    @step(retry_policy=ConstantDelayRetryPolicy(maximum_attempts=3, delay=10))
    async def process_file(
        self, event: FileDownloadedEvent, ctx: Context
    ) -> ExtractedEvent | ExtractedInvalidEvent:
        """Runs the extraction against the file"""
        try:
            agent = get_extract_agent()
            # track the content of the file, so as to be able to de-duplicate
            file_content = Path(event.file_path).read_bytes()
            file_hash = hashlib.sha256(file_content).hexdigest()
            source_text = SourceText(
                file=event.file_path,
                filename=event.filename,
            )
            logger.info(f"Extracting data from file {event.filename}")
            ctx.write_event_to_stream(
                UIToast(
                    level="info", message=f"Extracting data from file {event.filename}"
                )
            )
            extracted_result: ExtractRun = await agent.aextract(source_text)
            try:
                logger.info(f"Extracted data: {extracted_result}")
                data = ExtractedData.from_extraction_result(
                    result=extracted_result,
                    schema=MySchema,
                    file_hash=file_hash,
                )
                return ExtractedEvent(data=data)
            except InvalidExtractionData as e:
                logger.error(f"Error validating extracted data: {e}", exc_info=True)
                return ExtractedInvalidEvent(data=e.invalid_item)
        except Exception as e:
            logger.error(
                f"Error extracting data from file {event.filename}: {e}",
                exc_info=True,
            )
            ctx.write_event_to_stream(
                UIToast(
                    level="error",
                    message=f"Error extracting data from file {event.filename}: {e}",
                )
            )
            raise e

    @step(retry_policy=ConstantDelayRetryPolicy(maximum_attempts=3, delay=10))
    async def record_extracted_data(
        self, event: ExtractedEvent | ExtractedInvalidEvent, ctx: Context
    ) -> StopEvent:
        """Records the extracted data to the agent data API"""
        try:
            logger.info(f"Recorded extracted data for file {event.data.file_name}")
            ctx.write_event_to_stream(
                UIToast(
                    level="info",
                    message=f"Recorded extracted data for file {event.data.file_name}",
                )
            )
            # remove past data when reprocessing the same file
            if event.data.file_hash:
                existing_data = await get_data_client().untyped_search(
                    filter={
                        "file_hash": {
                            "eq": event.data.file_hash,
                        },
                    },
                )
                if existing_data.items:
                    logger.info(
                        f"Removing past data for file {event.data.file_name} with hash {event.data.file_hash}"
                    )
                    await asyncio.gather(
                        *[
                            get_data_client().delete_item(item.id)
                            for item in existing_data.items
                        ]
                    )
            # finally, save the new data
            item_id = await get_data_client().create_item(event.data)
            return StopEvent(
                result=item_id.id,
            )
        except Exception as e:
            logger.error(
                f"Error recording extracted data for file {event.data.file_name}: {e}",
                exc_info=True,
            )
            ctx.write_event_to_stream(
                UIToast(
                    level="error",
                    message=f"Error recording extracted data for file {event.data.file_name}: {e}",
                )
            )
            raise e


workflow = ProcessFileWorkflow(timeout=None)

if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    logging.basicConfig(level=logging.INFO)

    async def main():
        file = await get_llama_cloud_client().files.upload_file(
            upload_file=Path("test.pdf").open("rb")
        )
        await workflow.run(start_event=FileEvent(file_id=file.id))

    asyncio.run(main())
