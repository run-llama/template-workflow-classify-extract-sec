from random import randint
from typing import TypedDict, Any
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.status import Status
from rich.pretty import Pretty
from prompt_toolkit import prompt as ask_user_input
from prompt_toolkit.key_binding import KeyBindings
from ..agent import Message, AgentType
from .constants import VERBS
from ..workflow.workflow import (
    CodingAgentWorkflow,
    InputConfig,
    OutputSummary,
    MessageEvent,
    HumanDecision,
    QuestionToHuman,
)


def prompt(
    console: Console, question: str, options: list[str] | None, status: Status
) -> str:
    status.stop()
    if options:
        for option in options:
            question += f"\n- {option}"
    question += "\n"
    if not options:
        kb = KeyBindings()

        @kb.add("c-s")
        def _(event):
            # Accept input on Enter (or use a different key combo)
            event.current_buffer.validate_and_handle()

        question += "> _use `ctrl+s` to submit_\n"
        multiline = True
    else:
        kb = KeyBindings()

        @kb.add("enter")
        def _(event):
            # Accept input on Enter (or use a different key combo)
            event.current_buffer.validate_and_handle()

        multiline = False
    console.print(
        Panel(Markdown(question), border_style="blue", title="Human Input Required")
    )
    answer = ask_user_input("→ ", multiline=multiline, key_bindings=kb, in_thread=True)
    console.print(
        Panel(f"Your Answer: {answer}", title="Submitted", border_style="green")
    )
    status.start()
    return answer


def display_message(console: Console, message: Message, status: Status):
    if message["type"] == "text":
        status.update(VERBS[randint(0, len(VERBS) - 1)] + "...")
        status.stop()
        console.print(
            Panel(Markdown(message["text"]), title="Agent Message", title_align="left")
        )
        status.start()
    elif message["type"] == "thinking":
        status.update(VERBS[randint(0, len(VERBS) - 1)] + "...")
        status.stop()
        console.print(
            Panel(
                Markdown(message["thinking"]),
                title="Agent Thoughts",
                title_align="left",
                border_style="yellow",
            )
        )
        status.start()
    elif message["type"] == "tool_call":
        status.update(f"Calling tool {message['name']}...")
        status.stop()
        console.print(
            Panel(
                Pretty(message["input"]),
                title="Tool Call Input",
                title_align="left",
                border_style="red",
            )
        )
        status.start()
    elif message["type"] == "tool_result":
        status.update("Retrieving tool result...")
        status.stop()
        if "error" in message and message["error"]:
            console.print(
                Panel(
                    f"An error occurred while executing tool call {message['id']}",
                    title=f"Tool Result for {message['id']}",
                    title_align="left",
                    border_style="red",
                )
            )
        else:
            if isinstance(message["result"], str):
                console.print(
                    Panel(
                        Markdown(message["result"]),
                        title=f"Tool Result for {message['id']}",
                        title_align="left",
                        border_style="cyan",
                    )
                )
            else:
                console.print(
                    Panel(
                        Pretty(message["result"]),
                        title=f"Tool Result for {message['id']}",
                        title_align="left",
                        border_style="cyan",
                    )
                )
        status.start()
    elif message["type"] == "final_result":
        status.update("Getting the final result...")
        status.stop()
        res = message["result"] or "No result produced"
        console.print(
            Panel(
                Markdown(res),
                title="Final result",
                title_align="left",
                border_style="green",
            )
        )
        status.update("Working on your request...")
        status.start()


class Configuration(TypedDict):
    tools: list[str]
    mcp_servers_file: str
    system_prompt: str
    agent_specific_args: dict[str, Any]
    enable_persistence: bool
    provided_prompt: str | None
    provided_mode: str | None


async def run_workflow(console: Console, config: Configuration, agent_type: AgentType):
    wf = CodingAgentWorkflow(timeout=1800)
    start_event = InputConfig(
        agent_specific_options=config["agent_specific_args"],
        enable_persistence=config["enable_persistence"],
        mcp_file=config["mcp_servers_file"],
        system_prompt=config["system_prompt"],
        tools=config["tools"],
        agent_type=agent_type,
        provided_prompt=config["provided_prompt"],
        provided_mode=config["provided_mode"],
    )
    handler = wf.run(start_event=start_event)
    with Status("Starting to work on your request...") as status:
        async for ev in handler.stream_events():
            if isinstance(ev, MessageEvent):
                display_message(message=ev.message, console=console, status=status)
            elif isinstance(ev, QuestionToHuman):
                answer = prompt(
                    console=console,
                    question=ev.question,
                    options=ev.options,
                    status=status,
                )
                handler.ctx.send_event(HumanDecision(response=answer, type=ev.type))  # type: ignore
            elif isinstance(ev, OutputSummary):
                console.print(Markdown("## OUTPUT SUMMARY"))
                console.print(Markdown(ev.summary))
            else:
                pass
    await handler

    return None


def print_welcome_message(console: Console, agent_type: AgentType):
    console.print(
        Markdown(
            f"## Welcome to Coder!\n\nHi, I am Coder, your assistant, based on {agent_type}, for everything concerning building and editing **LlamaIndex Workflows**.\n\n> _Tip: If you with to exit, do so by using the `/exit` command_\n\n---\n\n"
        )
    )
    print()
