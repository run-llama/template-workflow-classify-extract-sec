from __future__ import annotations

from fastmcp import FastMCP


from tmpl.mcp.search import (
    format_results_pretty,
    search_templates_impl,
    get_template as get_template_impl,
)


# Initialize MCP server
mcp = FastMCP("tmpl MCP Server")


async def run_stdio() -> None:
    """Start the MCP server."""
    await mcp.run_stdio_async(show_banner=False)


async def run_server() -> None:
    """Start the MCP server."""
    await mcp.run_async()


@mcp.tool
def search_templates(query: str, context: int = 10) -> str:
    """Search the templates directory for files relevant to a query. This tool is useful when developing LlamaAgent applications, in order to
    identify relevant best-practice code snippets to re-use or adapt to a new use case."""
    results = search_templates_impl(query, context_lines=max(0, int(context)))
    return format_results_pretty(results)


@mcp.tool
def get_template(
    path: str, start_line: int | None = None, end_line: int | None = None
) -> str:
    """Read the full content of a template file by path.

    Args:
        path: Path relative to templates directory (e.g. 'basic/src/basic/workflow.py')
        start_line: Optional starting line number (1-indexed, inclusive)
        end_line: Optional ending line number (1-indexed, inclusive)

    Returns:
        File contents with line numbers. Limited to 1000 lines by default.
    """
    return get_template_impl(path, start_line=start_line, end_line=end_line)
