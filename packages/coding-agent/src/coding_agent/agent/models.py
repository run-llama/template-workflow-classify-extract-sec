from typing import Literal, TypedDict, Any
from typing_extensions import NotRequired

AgentType = Literal[
    "GitHub Copilot",
    "Claude Code",
    "OpenAI Codex CLI",
    "Jules",
    "Cursor",
    "Windsurf",
    "Cline",
    "Amp",
    "Firebase Studio",
    "Open Hands",
    "Gemini CLI",
    "Junie",
    "AugmentCode",
    "Kilo Code",
    "OpenCode",
    "Goose",
]

SkillType = Literal[
    "PDF Parsing",
    "Structured Data Extraction",
    "Information Retrieval",
    "Text Classification",
    "Llamactl Usage",
]


class ThinkingMessage(TypedDict):
    type: Literal["thinking"]
    thinking: str


class TextMessage(TypedDict):
    type: Literal["text"]
    text: str


class ToolMessage(TypedDict):
    type: Literal["tool_call"]
    id: str
    name: str
    input: dict[str, Any]


class ToolResultMessage(TypedDict):
    type: Literal["tool_result"]
    id: str
    result: Any | None
    error: NotRequired[bool | None]


class FinalResultMessage(TypedDict):
    type: Literal["final_result"]
    result: str | None
    metadata: NotRequired[dict[str, Any]]


Message = (
    ThinkingMessage | FinalResultMessage | TextMessage | ToolMessage | ToolResultMessage
)
