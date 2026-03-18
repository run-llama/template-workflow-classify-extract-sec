import asyncio
import json
import logging
from typing import Annotated, Any, Literal

from llama_cloud import AsyncLlamaCloud
from llama_cloud.types.beta.extracted_data import ExtractedData, InvalidExtractionData
from pydantic import BaseModel
from workflows import Context, Workflow, step
from workflows.events import Event, StartEvent, StopEvent
from workflows.resource import Resource, ResourceConfig

from .clients import agent_name, get_llama_cloud_client, project_id
from .config import (
    EXTRACTED_DATA_COLLECTION,
    ClassifyConfig,
    ExtractConfig,
    get_extraction_schema,
)

logger = logging.getLogger(__name__)

DISCRIMINATOR_FIELD = "document_type"

# Mapping from classify rule types to config.json extract section keys
EXTRACT_CONFIG_KEYS = {
    "10-K": "extract-10k",
    "10-Q": "extract-10q",
    "8-K": "extract-8k",
    "other": "extract-other",
}


class FileEvent(StartEvent):
    file_id: str
    file_hash: str | None = None


class ClassifyFileEvent(Event):
    pass


class FileClassifiedEvent(Event):
    filing_type: str
    confidence: float | None = None
    reasoning: str | None = None


class Status(Event):
    level: Literal["info", "warning", "error"]
    message: str


class ExtractJobStartedEvent(Event):
    pass


class ExtractedEvent(Event):
    data: ExtractedData


class ExtractedInvalidEvent(Event):
    data: ExtractedData[dict[str, Any]]


class ExtractionState(BaseModel):
    file_id: str | None = None
    filename: str | None = None
    file_hash: str | None = None
    extract_job_id: str | None = None
    filing_type: str | None = None
    classification_confidence: float | None = None
    classification_reasoning: str | None = None


class ProcessFileWorkflow(Workflow):
    """Extract structured data from a document and save it for review."""

    @step()
    async def start_extraction(
        self,
        event: FileEvent,
        ctx: Context[ExtractionState],
        llama_cloud_client: Annotated[
            AsyncLlamaCloud, Resource(get_llama_cloud_client)
        ],
        extract_config: Annotated[
            ExtractConfig,
            ResourceConfig(
                config_file="configs/config.json",
                path_selector="extract-10k",
                label="Default Extraction Settings",
                description="Default extraction config (10-K); actual schema selected after classification",
            ),
        ],
    ) -> ExtractJobStartedEvent:
        """Start extraction job for the document."""
        file_id = event.file_id
        logger.info(f"Running file {file_id}")

        try:
            files_page = await llama_cloud_client.files.list(file_ids=[file_id])
            file_metadata = files_page.items[0]
            filename = file_metadata.name
        except Exception as e:
            logger.error(f"Error fetching file metadata {file_id}: {e}", exc_info=True)
            ctx.write_event_to_stream(
                Status(
                    level="error",
                    message=f"Error fetching file metadata {file_id}: {e}",
                )
            )
            raise e

        logger.info(f"Extracting data from file {filename}")
        ctx.write_event_to_stream(
            Status(level="info", message=f"Extracting data from file {filename}")
        )

        if extract_config.extraction_agent_id:
            extract_job = await llama_cloud_client.extraction.jobs.extract(
                extraction_agent_id=extract_config.extraction_agent_id,
                file_id=file_id,
            )
        else:
            extract_job = await llama_cloud_client.extraction.run(
                config=extract_config.settings.model_dump(),
                data_schema=extract_config.json_schema,
                file_id=file_id,
                project_id=project_id,
            )

        file_hash = event.file_hash or file_metadata.external_file_id

        async with ctx.store.edit_state() as state:
            state.file_id = file_id
            state.filename = filename
            state.file_hash = file_hash
            state.extract_job_id = extract_job.id

        return ExtractJobStartedEvent()

    @step()
    async def classify_file(
        self,
        event: ExtractJobStartedEvent,
        ctx: Context[ExtractionState],
        llama_cloud_client: Annotated[
            AsyncLlamaCloud, Resource(get_llama_cloud_client)
        ],
        classify_config: Annotated[
            ClassifyConfig,
            ResourceConfig(
                config_file="configs/config.json",
                path_selector="classify",
                label="Classification Rules",
                description="Rules for classifying SEC filing types",
            ),
        ],
    ) -> FileClassifiedEvent:
        """Classify the SEC filing document type while extraction runs."""
        state = await ctx.store.get_state()
        if state.file_id is None or state.filename is None:
            raise ValueError("File ID or filename is not set")

        try:
            logger.info(f"Classifying file {state.filename}")
            ctx.write_event_to_stream(
                Status(level="info", message=f"Classifying file {state.filename}")
            )

            # Build rules from config
            rules = [
                {"type": rule.type, "description": rule.description}
                for rule in classify_config.rules
            ]

            # Build parsing config from settings
            parsing_config: dict[str, Any] = {}
            if classify_config.settings.parsing_config.max_pages is not None:
                parsing_config["max_pages"] = (
                    classify_config.settings.parsing_config.max_pages
                )
            if classify_config.settings.parsing_config.target_pages is not None:
                parsing_config["target_pages"] = (
                    classify_config.settings.parsing_config.target_pages
                )

            # 3-step classify: create job, wait, get results
            classify_job = await llama_cloud_client.classifier.jobs.create(
                file_ids=[state.file_id],
                rules=rules,
                mode=classify_config.settings.mode,
                **({"parsing_configuration": parsing_config} if parsing_config else {}),
            )
            await llama_cloud_client.classifier.wait_for_completion(classify_job.id)
            results = await llama_cloud_client.classifier.jobs.get_results(
                classify_job.id
            )

            # Extract classification result
            if results.items and len(results.items) > 0:
                item = results.items[0]
                if item.result:
                    filing_type = item.result.type
                    confidence = item.result.confidence
                    reasoning = item.result.reasoning

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
            async with ctx.store.edit_state() as state:
                state.filing_type = "other"
            return FileClassifiedEvent(filing_type="other")

    @step()
    async def complete_extraction(
        self,
        event: FileClassifiedEvent,
        ctx: Context[ExtractionState],
        llama_cloud_client: Annotated[
            AsyncLlamaCloud, Resource(get_llama_cloud_client)
        ],
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
    ) -> StopEvent:
        """Wait for extraction to complete, validate results, and save for review."""
        state = await ctx.store.get_state()
        if state.extract_job_id is None:
            raise ValueError("Job ID cannot be null when waiting for its completion")

        # Select the extract config for the classified filing type
        extract_configs = {
            "10-K": extract_10k,
            "10-Q": extract_10q,
            "8-K": extract_8k,
            "other": extract_other,
        }
        filing_type = state.filing_type or "other"
        extract_config = extract_configs.get(filing_type, extract_other)

        await llama_cloud_client.extraction.jobs.wait_for_completion(
            state.extract_job_id
        )

        extracted_result = await llama_cloud_client.extraction.jobs.get_result(
            state.extract_job_id
        )
        extract_run = await llama_cloud_client.extraction.runs.get(
            run_id=extracted_result.run_id
        )

        extracted_event: ExtractedEvent | ExtractedInvalidEvent
        try:
            logger.info(
                f"Extracted data: {json.dumps(extracted_result.model_dump(), indent=2)}"
            )
            if extract_config.extraction_agent_id:
                agent = await llama_cloud_client.extraction.extraction_agents.get(
                    extract_config.extraction_agent_id
                )
                schema_class = get_extraction_schema(agent.data_schema)
            else:
                schema_class = get_extraction_schema(
                    extract_config.json_schema,
                    discriminator_field=DISCRIMINATOR_FIELD,
                    discriminator_value=filing_type,
                )
            data = ExtractedData.from_extraction_result(
                result=extract_run,
                schema=schema_class,
                file_name=state.filename,
                file_id=state.file_id,
                file_hash=state.file_hash,
            )
            # Add classification information to the extracted data
            if data.metadata is None:
                data.metadata = {}
            data.metadata["classification"] = filing_type
            data.metadata["classification_confidence"] = state.classification_confidence
            data.metadata["classification_reasoning"] = state.classification_reasoning
            extracted_event = ExtractedEvent(data=data)
        except InvalidExtractionData as e:
            logger.error(f"Error validating extracted data: {e}", exc_info=True)
            extracted_event = ExtractedInvalidEvent(data=e.invalid_item)
        except Exception as e:
            logger.error(
                f"Error extracting data from file {state.filename}: {e}", exc_info=True
            )
            ctx.write_event_to_stream(
                Status(
                    level="error",
                    message=f"Error extracting data from file {state.filename}: {e}",
                )
            )
            raise e

        ctx.write_event_to_stream(extracted_event)

        extracted_data = extracted_event.data
        data_dict = extracted_data.model_dump()
        if extracted_data.file_hash is not None:
            delete_result = await llama_cloud_client.beta.agent_data.delete_by_query(
                deployment_name=agent_name or "_public",
                collection=EXTRACTED_DATA_COLLECTION,
                filter={
                    "file_hash": {
                        "eq": extracted_data.file_hash,
                    },
                },
            )
            if delete_result.deleted_count > 0:
                logger.info(
                    f"Removed {delete_result.deleted_count} existing record(s) "
                    f"for file {extracted_data.file_name}"
                )
        item = await llama_cloud_client.beta.agent_data.agent_data(
            data=data_dict,
            deployment_name=agent_name or "_public",
            collection=EXTRACTED_DATA_COLLECTION,
        )
        logger.info(
            f"Recorded extracted data for file {extracted_data.file_name or ''}"
        )
        ctx.write_event_to_stream(
            Status(
                level="info",
                message=f"Recorded extracted data for file {extracted_data.file_name or ''}",
            )
        )
        return StopEvent(result=item.id)


workflow = ProcessFileWorkflow(timeout=None)

if __name__ == "__main__":
    from pathlib import Path

    from dotenv import load_dotenv

    load_dotenv()
    logging.basicConfig(level=logging.INFO)

    async def main():
        file = await get_llama_cloud_client().files.create(
            file=Path("test.pdf").open("rb"),
            purpose="extract",
        )
        await workflow.run(start_event=FileEvent(file_id=file.id))

    asyncio.run(main())
