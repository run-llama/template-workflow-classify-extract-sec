from claude_agent_sdk import tool, create_sdk_mcp_server
from typing import Any
from ..db import get_matches
from dataclasses import asdict


@tool(
    name="get_memory",
    description="Get relevant pieces of memory matching with a specific pattern",
    input_schema={"pattern": str},
)
async def get_memory(args: dict[str, Any]) -> dict[str, Any]:
    pattern = args.get("pattern", "")
    results = await get_matches(pattern=pattern)
    return {"matches": [asdict(result) for result in results]}


sdk_mcp_server = create_sdk_mcp_server(name="local_memory_mcp", tools=[get_memory])
