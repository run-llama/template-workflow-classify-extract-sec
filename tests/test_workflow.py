from importlib.metadata import version

import pytest
from extraction_review.config import EXTRACTED_DATA_COLLECTION
from extraction_review.metadata_workflow import DISCRIMINATOR_FIELD, MetadataResponse
from extraction_review.metadata_workflow import workflow as metadata_workflow
from extraction_review.process_file import (
    ExtractedEvent,
    ExtractedInvalidEvent,
    FileEvent,
    Status,
)
from extraction_review.process_file import workflow as process_file_workflow
from llama_cloud_fake import FakeLlamaCloudServer
from workflows.events import StartEvent

FILING_TYPES = {"10-K", "10-Q", "8-K", "other"}
FAKE_HAS_CLASSIFY_V2 = version("llama-cloud-fake") >= "0.1.1"


@pytest.mark.asyncio
async def test_process_file_workflow(
    monkeypatch: pytest.MonkeyPatch,
    fake: FakeLlamaCloudServer,
) -> None:
    monkeypatch.setenv("LLAMA_CLOUD_API_KEY", "fake-api-key")
    file_id = fake.files.preload(path="tests/files/test.pdf")
    try:
        result = await process_file_workflow.run(start_event=FileEvent(file_id=file_id))
    except Exception:
        result = None
    assert result is not None
    assert isinstance(result, str)
    assert len(result) == 7


@pytest.mark.asyncio
@pytest.mark.skipif(
    not FAKE_HAS_CLASSIFY_V2,
    reason="llama-cloud-fake < 0.1.1 does not mock classify v2",
)
async def test_classify_v2_assigns_filing_type(
    monkeypatch: pytest.MonkeyPatch,
    fake: FakeLlamaCloudServer,
) -> None:
    """process_file reports a concrete SEC filing type from classify v2."""
    monkeypatch.setenv("LLAMA_CLOUD_API_KEY", "fake-api-key")
    file_id = fake.files.preload(path="tests/files/test.pdf")

    handler = process_file_workflow.run(start_event=FileEvent(file_id=file_id))
    classified_statuses: list[Status] = []
    async for event in handler.stream_events():
        if isinstance(event, Status):
            if event.level == "error":
                raise AssertionError(f"workflow errored: {event.message}")
            if event.message.startswith("Classified as "):
                classified_statuses.append(event)
    await handler

    # A real classify v2 result produces a "Classified as <type>" info status.
    # The fallback path (classification error -> "other") does *not* emit this.
    assert classified_statuses, (
        "expected a 'Classified as ...' status from a completed classify v2 job"
    )
    message = classified_statuses[-1].message
    matched = next((t for t in FILING_TYPES if f"Classified as {t} " in message), None)
    assert matched is not None, f"unexpected classification status: {message}"


@pytest.mark.asyncio
async def test_metadata_workflow() -> None:
    result = await metadata_workflow.run(start_event=StartEvent())
    assert isinstance(result, MetadataResponse)
    assert result.extracted_data_collection == EXTRACTED_DATA_COLLECTION
    assert result.discriminator_field == DISCRIMINATOR_FIELD
    assert set(result.schemas.keys()) == FILING_TYPES
    assert DISCRIMINATOR_FIELD in result.json_schema.get("properties", {})


@pytest.mark.asyncio
@pytest.mark.skipif(
    not FAKE_HAS_CLASSIFY_V2,
    reason="llama-cloud-fake < 0.1.1 does not mock classify v2",
)
async def test_extraction_uses_the_classified_schema(
    monkeypatch: pytest.MonkeyPatch,
    fake: FakeLlamaCloudServer,
) -> None:
    """The extract job runs the schema of the filing type it was classified as.

    Extracting with one filing type's schema and validating against another's
    fails on every field the two schemas don't share, so the result lands as
    invalid no matter what the document says.
    """
    monkeypatch.setenv("LLAMA_CLOUD_API_KEY", "fake-api-key")
    file_id = fake.files.preload(path="tests/files/test.pdf")

    handler = process_file_workflow.run(start_event=FileEvent(file_id=file_id))
    extracted: list[ExtractedEvent | ExtractedInvalidEvent] = []
    async for event in handler.stream_events():
        if isinstance(event, (ExtractedEvent, ExtractedInvalidEvent)):
            extracted.append(event)
    await handler

    assert len(extracted) == 1
    event = extracted[0]
    assert isinstance(event, ExtractedEvent), (
        "extracted data failed validation against the classified filing schema"
    )
    assert event.data.metadata is not None
    assert event.data.metadata["classification"] in FILING_TYPES
