from uuid import uuid4
from typing import Literal
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    content: str
    role: Literal["user", "assistant", "result"]


def _get_session_id() -> str:
    return str(uuid4())


class CodingWorkflowState(BaseModel):
    session_id: str = Field(default_factory=_get_session_id)
    chat_history: list[ChatMessage] = Field(default_factory=list)
    enable_persistance: bool = False
    current_mode: Literal["plan", "build"] | None = None
    current_prompt: str | None = None
    current_plan: str = ""
    current_result: str = ""
