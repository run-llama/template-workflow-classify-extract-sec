import asyncio
import hashlib
import logging
import os
from pathlib import Path
import tempfile
from typing import Any, Literal

import httpx
from llama_cloud import ClassificationResult, ExtractRun
from llama_cloud.types import ClassifierRule, ClassifyParsingConfiguration
from llama_cloud_services.extract import SourceText
from llama_cloud_services.beta.agent_data import ExtractedData, InvalidExtractionData
from pydantic import BaseModel
from workflows import Context, Workflow, step
from workflows.events import Event, StartEvent, StopEvent

from .clients import (
    get_classifier_client,
    get_llama_cloud_client,
    get_data_client,
    get_extract_agent,
)
from .config import FILING_SCHEMAS

logger = logging.getLogger(__name__)


class FileEvent(StartEvent):
    file_id: str


class DownloadFileEvent(Event):
    pass


class FileDownloadedEvent(Event):
    pass


class ClassifyFileEvent(Event):
    pass


class FileClassifiedEvent(Event):
    filing_type: str
    confidence: float | None = None
    reasoning: str | None = None


class Status(Event):
    level: Literal["info", "warning", "error"]
    message: str


class ExtractedEvent(Event):
    data: ExtractedData


class ExtractedInvalidEvent(Event):
    data: ExtractedData[dict[str, Any]]


class ExtractionState(BaseModel):
    file_id: str | None = None
    file_path: str | None = None
    filename: str | None = None
    filing_type: str | None = None
    classification_confidence: float | None = None
    classification_reasoning: str | None = None


class ProcessFileWorkflow(Workflow):
    """
    Given a file path, this workflow will process a single file through the custom extraction logic.
    """

    @step()
    async def run_file(self, event: FileEvent, ctx: Context) -> DownloadFileEvent:
        logger.info(f"Running file {event.file_id}")
        async with ctx.store.edit_state() as state:
            state.file_id = event.file_id
        return DownloadFileEvent()

    @step()
    async def download_file(
        self, event: DownloadFileEvent, ctx: Context[ExtractionState]
    ) -> ClassifyFileEvent:
        """Download the file reference from the cloud storage"""
        state = await ctx.store.get_state()
        if state.file_id is None:
            raise ValueError("File ID is not set")
        try:
            file_metadata = await get_llama_cloud_client().files.get_file(
                id=state.file_id
            )
            file_url = await get_llama_cloud_client().files.read_file_content(
                state.file_id
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
            async with ctx.store.edit_state() as state:
                state.file_path = file_path
                state.filename = filename
            return ClassifyFileEvent()

        except Exception as e:
            logger.error(f"Error downloading file {state.file_id}: {e}", exc_info=True)
            ctx.write_event_to_stream(
                Status(
                    level="error",
                    message=f"Error downloading file {state.file_id}: {e}",
                )
            )
            raise e

    @step()
    async def classify_file(
        self, event: ClassifyFileEvent, ctx: Context[ExtractionState]
    ) -> FileClassifiedEvent:
        """Classify the SEC filing document type"""
        state = await ctx.store.get_state()
        if state.file_path is None or state.filename is None:
            raise ValueError("File path or filename is not set")

        try:
            logger.info(f"Classifying file {state.filename}")
            ctx.write_event_to_stream(
                Status(level="info", message=f"Classifying file {state.filename}")
            )

            # Initialize the classifier

            classifier = get_classifier_client()

            # Define classification rules for SEC filing types
            rules = [
                ClassifierRule(
                    type="10-K",
                    description=(
                        "Form 10-K is an annual report filed by public companies with the SEC. "
                        "It provides a comprehensive summary of a company's financial performance for the year, "
                        "including audited financial statements, management's discussion and analysis (MD&A), "
                        "risk factors, business description, and executive compensation. "
                        "Look for: 'Form 10-K', 'Annual Report', fiscal year references, audited financials."
                    ),
                ),
                ClassifierRule(
                    type="10-Q",
                    description=(
                        "Form 10-Q is a quarterly report filed by public companies with the SEC. "
                        "It provides unaudited financial statements and management discussion for a specific quarter. "
                        "Contains quarterly financial data, updates on business operations, and material changes. "
                        "Look for: 'Form 10-Q', 'Quarterly Report', quarter references (Q1, Q2, Q3), unaudited statements."
                    ),
                ),
                ClassifierRule(
                    type="8-K",
                    description=(
                        "Form 8-K is a current report filed to announce material events or corporate changes. "
                        "Used to notify investors of significant events like mergers, acquisitions, leadership changes, "
                        "earnings releases, or other material corporate events that shareholders should know about. "
                        "Look for: 'Form 8-K', 'Current Report', Item numbers (e.g., Item 1.01, Item 5.02), event dates, "
                        "specific triggering events."
                    ),
                ),
                ClassifierRule(
                    type="other",
                    description=(
                        "Any other SEC filing type not covered by 10-K, 10-Q, or 8-K. "
                        "This includes forms such as S-1 (IPO registration), DEF 14A (proxy statement), "
                        "13F (institutional holdings), SC 13D (beneficial ownership), and other SEC forms."
                    ),
                ),
            ]

            # Configure parsing - only parse first few pages for classification
            parsing_config = ClassifyParsingConfiguration(
                max_pages=5,  # Only parse first 5 pages for faster classification
            )

            # Classify the file
            results = await classifier.aclassify_file_paths(
                rules=rules,
                file_input_paths=[state.file_path],
                parsing_configuration=parsing_config,
            )

            # Extract classification result
            if results.items and len(results.items) > 0:
                item = results.items[0]
                result: ClassificationResult | None = item.result
                if result:
                    filing_type = result.type
                    confidence = result.confidence
                    reasoning = result.reasoning

                    logger.info(
                        f"Classified {state.filename} as {filing_type} "
                        f"(confidence: {confidence}, reasoning: {reasoning})"
                    )
                    ctx.write_event_to_stream(
                        Status(
                            level="info",
                            message=f"Classified as {filing_type} SEC filing",
                        )
                    )

                    async with ctx.store.edit_state() as state:
                        state.filing_type = filing_type
                        state.classification_confidence = confidence
                        state.classification_reasoning = reasoning

                    return FileClassifiedEvent(
                        filing_type=filing_type,
                        confidence=confidence,
                        reasoning=reasoning,
                    )
                else:
                    # Classification failed, default to "other"
                    logger.warning(
                        f"Classification failed for {state.filename}, defaulting to 'other'"
                    )
                    ctx.write_event_to_stream(
                        Status(
                            level="warning",
                            message="Classification uncertain, using default schema",
                        )
                    )
                    async with ctx.store.edit_state() as state:
                        state.filing_type = "other"
                    return FileClassifiedEvent(filing_type="other")
            else:
                # No results, default to "other"
                logger.warning(f"No classification results for {state.filename}")
                async with ctx.store.edit_state() as state:
                    state.filing_type = "other"
                return FileClassifiedEvent(filing_type="other")

        except Exception as e:
            logger.error(f"Error classifying file {state.filename}: {e}", exc_info=True)
            ctx.write_event_to_stream(
                Status(
                    level="warning",
                    message=f"Classification failed, using default schema: {e}",
                )
            )
            # On error, default to "other" and continue
            async with ctx.store.edit_state() as state:
                state.filing_type = "other"
            return FileClassifiedEvent(filing_type="other")

    @step()
    async def process_file(
        self, event: FileClassifiedEvent, ctx: Context[ExtractionState]
    ) -> ExtractedEvent | ExtractedInvalidEvent:
        """Runs the extraction against the file"""
        state = await ctx.store.get_state()
        if state.file_path is None or state.filename is None:
            raise ValueError("File path or filename is not set")
        try:
            # Get the appropriate schema based on classification
            filing_type = (state.filing_type or "other").upper()
            schema = FILING_SCHEMAS.get(filing_type, FILING_SCHEMAS["other"])

            logger.info(f"Using schema for filing type: {filing_type}")
            ctx.write_event_to_stream(
                Status(
                    level="info",
                    message=f"Extracting data using {filing_type} schema",
                )
            )

            agent = get_extract_agent()
            # Update the agent's data schema for this specific filing type
            agent.data_schema = schema
            # track the content of the file, so as to be able to de-duplicate
            file_content = Path(state.file_path).read_bytes()
            file_hash = hashlib.sha256(file_content).hexdigest()
            source_text = SourceText(
                file=state.file_path,
                filename=state.filename,
            )
            logger.info(f"Extracting data from file {state.filename}")
            ctx.write_event_to_stream(
                Status(
                    level="info", message=f"Extracting data from file {state.filename}"
                )
            )
            extracted_result: ExtractRun = await agent.aextract(source_text)
            try:
                logger.info(f"Extracted data: {extracted_result}")
                data = ExtractedData.from_extraction_result(
                    result=extracted_result,
                    schema=schema,
                    file_hash=file_hash,
                )
                # Add classification information to the extracted data
                if data.metadata is None:
                    data.metadata = {}
                data.metadata["classification"] = filing_type
                data.metadata["classification_confidence"] = (
                    state.classification_confidence
                )
                data.metadata["classification_reasoning"] = (
                    state.classification_reasoning
                )
                return ExtractedEvent(data=data)
            except InvalidExtractionData as e:
                logger.error(f"Error validating extracted data: {e}", exc_info=True)
                return ExtractedInvalidEvent(data=e.invalid_item)
        except Exception as e:
            logger.error(
                f"Error extracting data from file {state.filename}: {e}",
                exc_info=True,
            )
            ctx.write_event_to_stream(
                Status(
                    level="error",
                    message=f"Error extracting data from file {state.filename}: {e}",
                )
            )
            raise e

    @step()
    async def record_extracted_data(
        self, event: ExtractedEvent | ExtractedInvalidEvent, ctx: Context
    ) -> StopEvent:
        """Records the extracted data to the agent data API"""
        try:
            logger.info(f"Recorded extracted data for file {event.data.file_name}")
            ctx.write_event_to_stream(
                Status(
                    level="info",
                    message=f"Recorded extracted data for file {event.data.file_name}",
                )
            )
            # remove past data when reprocessing the same file
            if event.data.file_hash:
                await get_data_client().delete(
                    filter={
                        "file_hash": {
                            "eq": event.data.file_hash,
                        },
                    },
                )
                logger.info(
                    f"Removing past data for file {event.data.file_name} with hash {event.data.file_hash}"
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
                Status(
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
