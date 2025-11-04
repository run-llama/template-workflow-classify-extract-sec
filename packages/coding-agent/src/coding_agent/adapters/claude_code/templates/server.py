from __future__ import annotations

from .search import (
    format_results_pretty,
    search_templates_impl,
    get_template as get_template_impl,
)
from typing import Any
from vibe_llama_core.templates.scaffold import ProjectName
from vibe_llama_core.templates import download_template as download_template_impl
from claude_agent_sdk import tool, create_sdk_mcp_server


@tool(
    name="search_templates",
    description="Search the templates directory for files relevant to a query. This tool is useful when developing LlamaAgent applications, in order to identify relevant best-practice code snippets to re-use or adapt to a new use case. Use only if you already have downlaoded templates.",
    input_schema={"query": str, "context": int},
)
async def search_templates(args: dict[str, Any]) -> dict[str, Any]:
    query = args.get("query", "")
    context = args.get("context", 10)
    results = search_templates_impl(query, context_lines=max(0, int(context)))
    return {"results": format_results_pretty(results)}


@tool(
    name="get_template",
    description="Read the full content of a template file by path. Can only be used once you downloaded at least one template.\n\nArgs:\n\tpath: Path relative to templates directory (e.g. 'basic/src/basic/workflow.py')\n\tstart_line: Optional starting line number (1-indexed, inclusive)\n\tend_line: Optional ending line number (1-indexed, inclusive)\nReturns:\n\tFile contents with line numbers. Limited to 1000 lines by default.",
    input_schema={"path": str, "start_line": int | None, "end_line": int | None},
)
async def get_template(args: dict[str, Any]) -> dict[str, Any]:
    path = args.get("path", "")
    start_line = args.get("start_line")
    end_line = args.get("end_line")
    return {
        "results": get_template_impl(path, start_line=start_line, end_line=end_line)
    }


@tool(
    name="download_template",
    description="Download a template by name (among the available ones).\n\nArgs:\n\tname (Literal['basic', 'document_parsing', 'human_in_the_loop', 'invoice_extraction', 'rag', 'web_scraping']): name of the template to download.\n\nReturns:\t\nPath to which the template was downloaded.",
    input_schema={"name": ProjectName},
)
async def download_template(args: dict[str, Any]) -> dict[str, Any]:
    name = args.get("name", "basic")
    retval = await download_template_impl(request=name)
    if "SUCCESS" in retval:
        return {"path": f".vibe-llama/scaffold/{name}/"}
    else:
        return {"error": retval}


sdk_mcp_server = create_sdk_mcp_server(
    name="templates_mcp", tools=[download_template, get_template, search_templates]
)
