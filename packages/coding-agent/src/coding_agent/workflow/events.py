from typing import Any, Literal
from typing_extensions import Self
from pydantic import model_validator
from ..agent import AgentType, Message
from workflows.events import (
    StartEvent,
    StopEvent,
    HumanResponseEvent,
    InputRequiredEvent,
    Event,
)


class InputConfig(StartEvent):
    agent_specific_options: dict[str, Any]
    enable_persistence: bool
    agent_type: AgentType
    mcp_file: str
    system_prompt: str
    tools: list[str]


class QuestionToHuman(InputRequiredEvent):
    type: Literal[
        "mode_choice", "prompt", "approve_mode_change", "approve_final_result"
    ]
    question: str
    options: list[str] | None = None

    @model_validator(mode="after")
    def validate_options_by_type(self) -> Self:
        if self.type == "mode_choice":
            self.options = ["build", "plan"]
        elif self.type == "approve_final_result":
            self.options = ["yes", "no"]
        elif self.type == "approve_mode_change":
            self.options = [
                "yes",
                "no, and provide details on what should be done further/differently in the current mode",
            ]
        else:
            self.options = None
        return self


class HumanDecision(HumanResponseEvent):
    type: Literal[
        "mode_choice", "prompt", "approve_mode_change", "approve_final_result"
    ]
    response: str


class MessageEvent(Event):
    message: Message


class Plan(Event):
    pass


class Build(Event):
    pass


class Finalize(Event):
    event: Literal["plan", "build"]


class OutputSummary(StopEvent):
    summary: str
