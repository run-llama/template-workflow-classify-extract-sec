from __future__ import annotations
from datetime import datetime
import logging
import os
import tempfile
from typing import Any, Literal

import httpx
from llama_index.core import Settings
from llama_index.core.chat_engine.types import (
    BaseChatEngine,
    ChatMode,
)
from llama_index.core.llms import ChatMessage
import asyncio
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from pydantic import BaseModel, Field
from workflows import Workflow, step, Context
from workflows.events import (
    StartEvent,
    StopEvent,
    Event,
    InputRequiredEvent,
    HumanResponseEvent,
)
from workflows.retry_policy import ConstantDelayRetryPolicy

from .clients import (
    get_index,
    get_llama_cloud_client,
    get_llama_parse_client,
    LLAMA_CLOUD_PROJECT_ID,
)

logger = logging.getLogger(__name__)


class FileEvent(StartEvent):
    file_id: str
    index_name: str


class DownloadFileEvent(Event):
    file_id: str


class FileDownloadedEvent(Event):
    file_id: str
    file_path: str
    filename: str


class ChatEvent(StartEvent):
    index_name: str
    conversation_history: list[ConversationMessage] = Field(default_factory=list)


# Configure LLM and embedding model
Settings.llm = OpenAI(model="gpt-4", temperature=0.1)
Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")


class DocumentUploadWorkflow(Workflow):
    """Workflow to upload and index documents using LlamaParse and LlamaCloud Index"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Get API key with validation

        # Initialize LlamaParse with recommended settings
        self.parser = get_llama_parse_client()

    @step(retry_policy=ConstantDelayRetryPolicy(maximum_attempts=3, delay=10))
    async def run_file(self, event: FileEvent, ctx: Context) -> DownloadFileEvent:
        logger.info(f"Running file {event.file_id}")
        await ctx.store.set("index_name", event.index_name)
        return DownloadFileEvent(file_id=event.file_id)

    @step(retry_policy=ConstantDelayRetryPolicy(maximum_attempts=3, delay=10))
    async def download_file(
        self, event: DownloadFileEvent, ctx: Context
    ) -> FileDownloadedEvent:
        """Download the file reference from the cloud storage"""
        logger.info(f"Downloading file {event.file_id}")
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
            raise e

    @step
    async def parse_document(self, ev: FileDownloadedEvent, ctx: Context) -> StopEvent:
        """Parse document and index it to LlamaCloud"""
        try:
            logger.info(f"Parsing document {ev.file_id}")
            # Get file path or content from event
            file_path = ev.file_path
            file_name = file_path.split("/")[-1]
            index_name = await ctx.store.get("index_name")

            # Parse the document
            if file_path:
                # Parse from file path
                result = await self.parser.aparse(file_path)

            # Get parsed documents
            documents = result.get_text_documents()

            # Create or connect to LlamaCloud Index
            index = get_index(index_name)

            # Insert documents to index
            logger.info(f"Inserting {len(documents)} documents to {index_name}")
            for document in documents:
                index.insert(document)

            return StopEvent(
                result={
                    "success": True,
                    "index_name": index_name,
                    "document_count": len(documents),
                    "index_url": f"https://cloud.llamaindex.ai/projects/{LLAMA_CLOUD_PROJECT_ID}/indexes/{index.id}",
                    "file_name": file_name,
                    "message": f"Successfully indexed {len(documents)} documents to '{index_name}'",
                }
            )

        except Exception as e:
            logger.error(f"Error parsing document {ev.file_id}: {e}", exc_info=True)
            return StopEvent(result={"success": False, "error": str(e)})


class AppendChatMessage(Event):
    """Event emitted when chat engine appends a message to the conversation history"""

    message: ConversationMessage


class ChatDeltaEvent(Event):
    """Streaming delta for incremental response output"""

    delta: str


class QueryConversationHistoryEvent(HumanResponseEvent):
    """Client can call this to trigger replaying AppendChatMessage events"""

    pass


class ErrorEvent(Event):
    """Event emitted when an error occurs"""

    error: str


class ChatWorkflowState(BaseModel):
    index_name: str | None = None
    conversation_history: list[ConversationMessage] = Field(default_factory=list)

    def chat_messages(self) -> list[ChatMessage]:
        return [
            ChatMessage(role=message.role, content=message.text)
            for message in self.conversation_history
        ]


class SourceMessage(BaseModel):
    text: str
    score: float
    metadata: dict[str, Any]


class ConversationMessage(BaseModel):
    """
    Mostly just a wrapper for a ChatMessage with extra context for UI. Includes a timestamp and source references.
    """

    role: Literal["user", "assistant"]
    text: str
    sources: list[SourceMessage] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


def get_chat_engine(index_name: str) -> BaseChatEngine:
    index = get_index(index_name)
    return index.as_chat_engine(
        chat_mode=ChatMode.CONTEXT,
        llm=Settings.llm,
        context_prompt=(
            "You are a helpful assistant that answers questions based on the provided documents. "
            "Always cite specific information from the documents when answering. "
            "If you cannot find the answer in the documents, say so clearly."
        ),
    )


class ChatWorkflow(Workflow):
    """Workflow to handle continuous chat queries against indexed documents"""

    @step
    async def initialize_chat(
        self, ev: ChatEvent, ctx: Context[ChatWorkflowState]
    ) -> InputRequiredEvent | StopEvent | None:
        """Initialize the chat session and request first input"""
        try:
            logger.info(f"Initializing chat {ev.index_name}")
            index_name = ev.index_name

            initial_state = await ctx.store.get_state()
            # Store session info in context
            await ctx.store.set("index_name", index_name)
            messages = initial_state.conversation_history

            for item in messages:
                ctx.write_event_to_stream(AppendChatMessage(message=item))

            if ev.conversation_history:
                async with ctx.store.edit_state() as state:
                    state.conversation_history.extend(ev.conversation_history)

        except Exception as e:
            logger.error(f"Error initializing chat: {str(e)}", exc_info=True)
            ctx.write_event_to_stream(
                ErrorEvent(error=f"Failed to initialize chat: {str(e)}")
            )
        return InputRequiredEvent()

    @step
    async def get_conversation_history(
        self, ev: QueryConversationHistoryEvent, ctx: Context[ChatWorkflowState]
    ) -> None:
        """Get the conversation history from the database"""
        hist = (await ctx.store.get_state()).conversation_history
        for item in hist:
            ctx.write_event_to_stream(AppendChatMessage(message=item))

    @step
    async def process_user_response(
        self, ev: HumanResponseEvent, ctx: Context[ChatWorkflowState]
    ) -> InputRequiredEvent | HumanResponseEvent | None:
        """Process user input and generate response"""
        try:
            logger.info(f"Processing user response {ev.response}")
            user_input = ev.response.strip()

            initial_state = await ctx.store.get_state()
            conversation_history = initial_state.conversation_history
            index_name = initial_state.index_name
            if not index_name:
                raise ValueError("Index name not found in context")

            logger.info(f"User input: {user_input}")

            # Check for exit command
            if user_input.lower() == "exit":
                logger.info("User input is exit")
                return StopEvent(
                    result={
                        "success": True,
                        "message": "Chat session ended.",
                        "conversation_history": conversation_history,
                    }
                )

            chat_engine = get_chat_engine(index_name)

            stream_response = await chat_engine.astream_chat(
                user_input, chat_history=initial_state.chat_messages()
            )
            full_text = ""

            # Emit streaming deltas to the event stream
            async for token in stream_response.async_response_gen():
                full_text += token
                ctx.write_event_to_stream(ChatDeltaEvent(delta=token))
                await asyncio.sleep(
                    0
                )  # Temp workaround. Some sort of bug in the server drops events without flushing the event loop

            # Extract source nodes for citations
            sources = []
            if stream_response.source_nodes:
                for node in stream_response.source_nodes:
                    sources.append(
                        SourceMessage(
                            text=node.text[:197] + "..."
                            if len(node.text) >= 200
                            else node.text,
                            score=float(node.score) if node.score else 0.0,
                            metadata=node.metadata,
                        )
                    )

            # After streaming completes, emit a summary response event to stream for frontend/main printing
            assistant_response = ConversationMessage(
                role="assistant", text=full_text, sources=sources
            )
            ctx.write_event_to_stream(AppendChatMessage(message=assistant_response))
            async with ctx.store.edit_state() as state:
                state.conversation_history.extend(
                    [
                        ConversationMessage(role="user", text=user_input),
                        assistant_response,
                    ]
                )

        except Exception as e:
            logger.error(f"Error processing query: {str(e)}", exc_info=True)
            ctx.write_event_to_stream(ErrorEvent(error=str(e)))
        return InputRequiredEvent()


upload = DocumentUploadWorkflow(timeout=None)
chat = ChatWorkflow(timeout=None)
