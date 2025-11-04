import aiosqlite

from coding_agent.agent import BaseCodingAgent, AgentType
from typing import Type, AsyncIterator
from .errors import UnsupportAgentError
from .constants import SUPPORTED_AGENTS
from contextlib import asynccontextmanager


def agent_type_to_agent_class(agent: AgentType) -> Type[BaseCodingAgent]:
    if agent in SUPPORTED_AGENTS:
        return SUPPORTED_AGENTS[agent]
    else:
        raise UnsupportAgentError(
            f"Agent {agent} is not supported. Supported agents are: {', '.join(list(SUPPORTED_AGENTS.keys()))}"
        )


def check_if_yes(s: str) -> bool:
    return s.strip().lower() in ("y", "yes", "ys", "yse")


@asynccontextmanager
async def sqlite_connection() -> AsyncIterator[aiosqlite.Connection]:
    async with aiosqlite.connect("sessions.db") as db:
        yield db
