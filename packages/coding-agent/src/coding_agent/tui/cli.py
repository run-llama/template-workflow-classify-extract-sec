"""Fully lifted from https://click.palletsprojects.com/en/stable/extending-click/"""

import click
import json
from pathlib import Path
from rich import print as rprint
from rich.markdown import Markdown
from .utils import Configuration
from .ui import AgentUI
from ..agent import AgentType
from ..adapters.claude_code.agent import BASE_SYSTEM_PROMPT as CLAUDE_BASE_SYSTEM_PROMPT


class AliasedGroup(click.Group):
    """
    Implements a subclass of Group that accepts a prefix for a command.
    If there was a command called push, it would accept pus as an alias (so long as it was unique):
    """

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        rv = super().get_command(ctx, cmd_name)

        if rv is not None:
            return rv

        matches = [x for x in self.list_commands(ctx) if x.startswith(cmd_name)]

        if not matches:
            return None

        if len(matches) == 1:
            return click.Group.get_command(self, ctx, matches[0])

        ctx.fail(f"Too many matches: {', '.join(sorted(matches))}")

    def resolve_command(
        self, ctx: click.Context, args: list[str]
    ) -> tuple[str, click.Command, list[str]]:
        # always return the full command name
        _, cmd, args = super().resolve_command(ctx, args)
        return cmd.name, cmd, args  # type: ignore


@click.group(
    help="Convert notebooks to python scripts and run them for testing purposes",
    cls=AliasedGroup,
)
def app():
    pass


@app.command("claude", help="Use Claude Code as the backend for the coding agent")
@click.option(
    "--system",
    is_flag=True,
    default=False,
    required=False,
    help="Show the base system prompt and exit",
)
@click.option(
    "--prompt",
    default=None,
    required=False,
    help="The task to perform. If not specified, will prompt the user for a task",
)
@click.option(
    "--mode",
    default=None,
    required=False,
    help="The mode to use for the coding agent. Either 'build' or 'plan'. If not specified, will prompt the user for a mode",
)
def code_with_claude(
    system: bool = False,
    prompt: str | None = None,
    mode: str | None = None,
) -> None:
    if system:
        rprint(Markdown(f"## SYSTEM PROMPT\n\n{CLAUDE_BASE_SYSTEM_PROMPT}"))
        return None
    else:
        agent_type: AgentType = "Claude Code"
        configuration: Configuration = {
            "agent_specific_args": {
                "model": "claude-sonnet-4-5",
                "max_turns": None,
                "permissions": "acceptEdits",
                "cwd": ".",
                "skills": [
                    "PDF Parsing",
                    "Structured Data Extraction",
                    "Text Classification",
                    "Llamactl Usage",
                ],
            },
            "enable_persistence": True,
            "mcp_servers_file": ".mcp.json",
            "system_prompt": "",
            "tools": ["Read", "Write"],
            "provided_prompt": prompt,
            "provided_mode": mode,
        }
        if not Path(".mcp.json").exists():
            with open(".mcp.json", "w") as f:
                json.dump(
                    {
                        "mcpServers": {
                            "llama-index-docs": {
                                "type": "http",
                                "url": "https://developers.llamaindex.ai/mcp",
                            }
                        }
                    },
                    f,
                    indent=2,
                )

        ui = AgentUI(agent_type, configuration)
        return ui.run()
