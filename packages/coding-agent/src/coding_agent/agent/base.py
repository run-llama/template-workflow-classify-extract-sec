from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator
from vibe_llama_core.docs import get_agent_rules
from .models import AgentType, SkillType, Message
from .errors import WarmUpError


class BaseCodingAgent(ABC):
    def __init__(
        self,
        agent_type: AgentType,
        tools: list[Any],
        mcp_servers_file: str,
        permissions: Any,
        system_prompt: str,
        **kwargs,
    ) -> None:
        self.tools = tools
        self.mcp_file = mcp_servers_file
        self.system_prompt = system_prompt
        self.permissions: Any = permissions
        self.agent_type = agent_type
        self._agent: Any | None = None
        self._is_warmed_up = False

    @abstractmethod
    def _mcp_config_from_file(self) -> None: ...

    @abstractmethod
    async def generate(self, prompt: str) -> AsyncGenerator[Message, Any]: ...

    @abstractmethod
    async def plan(
        self, prompt: str
    ) -> AsyncGenerator[Message, Any]:  # returns the plan
        ...

    async def warmup(self, skills: list[SkillType] | None = None) -> None:
        if not self._is_warmed_up:
            try:
                self._mcp_config_from_file()
                await self._get_rules(skills=skills)
            except Exception as e:
                raise WarmUpError(
                    f"An error occurred while fetching rules and skills for the agent: {e}"
                )
            self._is_warmed_up = True
        return None

    async def _get_rules(self, skills: list[SkillType] | None = None) -> None:
        for service in ["llama-index-workflows"]:
            await get_agent_rules(
                agent=self.agent_type,
                service=service,  # type: ignore
                skills=skills or [],  # type: ignore
                overwrite_files=True,
            )
