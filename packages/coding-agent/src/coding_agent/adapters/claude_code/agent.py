from os import getenv as os_getenv
from json import load as load_json
from pathlib import Path
from typing import AsyncIterator, AsyncGenerator, Any
from contextlib import asynccontextmanager
from claude_agent_sdk import ClaudeSDKClient
from claude_agent_sdk.types import (
    McpHttpServerConfig,
    McpSSEServerConfig,
    McpStdioServerConfig,
    AssistantMessage,
    TextBlock,
    ResultMessage,
    ClaudeAgentOptions,
    ToolUseBlock,
    ToolResultBlock,
    ThinkingBlock,
    PermissionMode,
    ToolPermissionContext,
    PermissionResultAllow,
    PermissionResultDeny,
)
from vibe_llama_core.docs.utils import get_claude_code_skills, write_file
from .memory.mcp import sdk_mcp_server as memory_mcp
from .templates import sdk_mcp_server as templates_mcp
from .memory.db import insert_record, MemoryMatch, init_db
from ...agent import BaseCodingAgent, SkillType, Message
from .errors import MalformedMCPSpecification, UnsupportedMCPType, MissingAPIKey
from .instructions import BASE_SYSTEM_PROMPT, get_claude_md


async def _can_use_tool(t: str, d: dict[str, Any], c: ToolPermissionContext):
    if t != "Bash" and "Bash" not in d:
        return PermissionResultAllow()
    else:
        return PermissionResultDeny()


class ClaudeCodingAgent(BaseCodingAgent):
    def __init__(
        self,
        tools: list[str],
        mcp_servers_file: str,
        system_prompt: str,
        skills: list[SkillType] | None = None,
        permissions: PermissionMode = "acceptEdits",
        cwd: str | Path | None = None,
        model: str = "claude-sonnet-4-5",
        max_turns: int | None = None,
    ) -> None:
        if not os_getenv("ANTHROPIC_API_KEY"):
            raise MissingAPIKey(
                "You need to provide an ANTHROPIC_API_KEY in your environment."
            )
        if system_prompt != "":
            system_prompt = (
                BASE_SYSTEM_PROMPT + "\n\nFURTHER INSTRUCTIONS:\n" + system_prompt
            )
        super().__init__(
            "Claude Code", tools, mcp_servers_file, permissions, system_prompt
        )
        self.options = ClaudeAgentOptions(
            allowed_tools=self.tools,
            system_prompt=self.system_prompt,
            permission_mode=self.permissions,
            max_turns=max_turns,
            model=model,
            cwd=cwd or Path.cwd(),
            disallowed_tools=["Bash", "Glob"],
        )
        self.skills = skills
        self._is_db_inited = False

    @asynccontextmanager
    async def _get_client(self) -> AsyncIterator[ClaudeSDKClient]:
        async with ClaudeSDKClient(self.options) as client:
            yield client

    def _mcp_config_from_file(self) -> None:
        with open(self.mcp_file, "r") as f:
            mcp_config = load_json(f)
        if "mcpServers" not in mcp_config:
            raise MalformedMCPSpecification(
                "Could not find `mcpServers` in the MCP specification file"
            )
        servers = {}
        for k, v in mcp_config["mcpServers"].items():
            if v.get("type", "") == "http":
                servers.update({k: McpHttpServerConfig(**v)})
            elif v.get("type", "") == "sse":
                servers.update({k: McpSSEServerConfig(**v)})
            elif v.get("type", "") == "stdio":
                servers.update({k: McpStdioServerConfig(**v)})
            else:
                raise UnsupportedMCPType(f"Unsupported MCP type: {v.get('type', '')}")
        servers.update({"memory": memory_mcp})
        servers.update({"templates": templates_mcp})
        self.options.allowed_tools.extend(
            [
                "__mcp__memory__get_memory",
                "__mcp__templates__get_template",
                "__mcp__templates_download_template",
                "__mcp__templates_search_templates",
            ]
        )
        self.options.can_use_tool = _can_use_tool
        self.options.mcp_servers = servers
        return None

    async def warmup(self, skills: list[SkillType] | None = None) -> None:
        if not self._is_db_inited:
            await init_db()
            self._is_db_inited = True
        return await super().warmup(skills)

    async def generate(self, prompt: str) -> AsyncGenerator[Message, Any]:
        if self.options.permission_mode == "plan":
            if self.permissions != "plan":
                self.options.permission_mode = self.permissions
            else:
                self.options.permission_mode = "acceptEdits"
        await self.warmup(self.skills)

        async def gen():
            async for message in self._query(prompt=prompt):
                if message["type"] == "final_result":
                    await insert_record(
                        MemoryMatch(content=message["result"] or "No result")
                    )
                yield message

        return gen()

    async def plan(self, prompt: str) -> AsyncGenerator[Message, Any]:
        await self.warmup(self.skills)
        self.options.permission_mode = "plan"

        async def gen():
            async for message in self._query(prompt=prompt):
                if message["type"] == "final_result":
                    await insert_record(
                        MemoryMatch(content=message["result"] or "No result")
                    )
                yield message

        return gen()

    async def _query(self, prompt: str) -> AsyncIterator[Message]:
        async with self._get_client() as client:
            await client.query(prompt=prompt)

            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    blocks = message.content
                    for block in blocks:
                        if isinstance(block, TextBlock):
                            yield {"text": block.text, "type": "text"}
                        elif isinstance(block, ThinkingBlock):
                            yield {"thinking": block.thinking, "type": "thinking"}
                        elif isinstance(block, ToolUseBlock):
                            yield {
                                "id": block.id,
                                "input": block.input,
                                "name": block.name,
                                "type": "tool_call",
                            }
                        elif isinstance(block, ToolResultBlock):
                            yield {
                                "id": block.tool_use_id,
                                "result": block.content,
                                "error": block.is_error,
                                "type": "tool_result",
                            }
                elif isinstance(message, ResultMessage):
                    yield {
                        "result": message.result,
                        "metadata": {
                            "error": message.is_error,
                            "subtype": message.subtype,
                            "duration_ms": message.duration_ms,
                            "turns": message.num_turns,
                            "total_cost_usd": message.total_cost_usd,
                        },
                        "type": "final_result",
                    }
                else:
                    pass

    async def _get_rules(self, skills: list[SkillType] | None = None) -> None:
        await get_claude_code_skills(skills=skills, overwrite_files=True)  # type: ignore
        claude_md = get_claude_md()
        write_file("CLAUDE.md", claude_md, overwrite_file=True, service_url="")
