import json
from workflows import Workflow, step, Context
from typing import cast
from .models import CodingWorkflowState, ChatMessage
from .events import (
    InputConfig,
    Plan,
    Build,
    Finalize,
    OutputSummary,
    HumanDecision,
    QuestionToHuman,
    MessageEvent,
)
from .utils import agent_type_to_agent_class, check_if_yes, sqlite_connection
from .errors import UnrecognizedMode
from .constants import CREATE_TABLE_STATEMENT
from ..persistence.query import create_message
from ..agent import BaseCodingAgent


class CodingAgentWorkflow(Workflow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._agent: BaseCodingAgent | None = None
        self._is_db_inited = False

    async def _init_db(self) -> None:
        async with sqlite_connection() as db:
            await db.execute("PRAGMA journal_mode=WAL;")
            await db.execute(CREATE_TABLE_STATEMENT)
            await db.commit()
        self._is_db_inited = True

    @step
    async def configure_agent(
        self, ctx: Context[CodingWorkflowState], ev: InputConfig
    ) -> QuestionToHuman | Build | Plan:
        agent_cls = agent_type_to_agent_class(ev.agent_type)
        self._agent = agent_cls(
            tools=ev.tools,
            system_prompt=ev.system_prompt,
            mcp_servers_file=ev.mcp_file,
            **ev.agent_specific_options,
        )  # type: ignore
        async with ctx.store.edit_state() as state:
            state.enable_persistance = ev.enable_persistence
            if ev.provided_prompt:
                state.current_prompt = ev.provided_prompt
            if ev.provided_mode:
                state.current_mode = ev.provided_mode
        return await self.resolve_agent(ctx)

    async def resolve_agent(
        self, ctx: Context[CodingWorkflowState]
    ) -> QuestionToHuman | Build | Plan:
        state = await ctx.store.get_state()
        if not state.current_prompt:
            return QuestionToHuman(
                question="What would you like me to do today?",
                type="prompt",
            )
        elif not state.current_mode:
            return QuestionToHuman(
                question="Please choose a mode:",
                type="mode_choice",
            )
        else:
            if state.current_mode == "plan":
                return Plan()
            elif state.current_mode == "build":
                return Build()
            else:
                raise UnrecognizedMode(f"Unrecognized mode: {state.current_mode}")

    @step
    async def handle_human_response(
        self, ctx: Context[CodingWorkflowState], ev: HumanDecision
    ) -> Build | Plan | QuestionToHuman | Finalize:
        if ev.response == "/exit":
            return Finalize(event="build")
        elif ev.type == "prompt":
            async with ctx.store.edit_state() as state:
                state.chat_history.append(ChatMessage(content=ev.response, role="user"))
                state.current_prompt = ev.response
            return await self.resolve_agent(ctx)
        elif ev.type == "mode_choice":
            if ev.response.strip().lower() not in ["build", "plan"]:
                return await self.resolve_agent(ctx)
            async with ctx.store.edit_state() as state:
                state.current_mode = ev.response.strip().lower()
            return await self.resolve_agent(ctx)
        elif ev.type == "approve_final_result":
            state = await ctx.store.get_state()
            if check_if_yes(ev.response):
                return Finalize(event=state.current_mode)
            else:
                return QuestionToHuman(
                    question="Since the above result did not satisfy you, what would you like to do different?",
                    type="prompt",
                )
        elif ev.type == "approve_mode_change":
            if check_if_yes(ev.response):
                async with ctx.store.edit_state() as state:
                    other = {"build", "plan"} - {state.current_mode}
                    state.current_mode = other.pop()
                return await self.resolve_agent(ctx)
            else:
                async with ctx.store.edit_state() as state:
                    state.current_prompt = ev.response
                return await self.resolve_agent(ctx)
        else:
            raise UnrecognizedMode(f"Unrecognized mode: {ev.type}")

    @step
    async def handle_finalize(
        self, ev: Finalize, ctx: Context[CodingWorkflowState]
    ) -> QuestionToHuman | OutputSummary:
        state = await ctx.store.get_state()
        if ev.event == "plan":
            return QuestionToHuman(
                type="approve_mode_change",
                question="Should we now change the mode of the coding agent to 'build'?",
            )
        else:
            summary = f"Session {state.session_id} leveraged {self._agent.agent_type} as agent and consisted of {len(state.chat_history)} messages. The final result of this session was:\n{state.current_result}\n"  # type: ignore
            if state.enable_persistance:
                if not self._is_db_inited:
                    await self._init_db()
                async with sqlite_connection() as db:
                    try:
                        for message in state.chat_history:
                            await create_message(
                                conn=db,
                                session_id=state.session_id,
                                message_role=message.role,
                                content=message.content,
                            )
                        await db.commit()
                    except Exception as e:
                        summary += f"There was an error while saving the session to the database: {e}."
                    else:
                        summary += " The session history was correctly exported to the local database."
                return OutputSummary(summary=summary)
            else:
                return OutputSummary(summary=summary)

    @step
    async def handle_build(
        self, ev: Build, ctx: Context[CodingWorkflowState]
    ) -> QuestionToHuman:
        state = await ctx.store.get_state()
        agent = cast(BaseCodingAgent, self._agent)
        prompt = state.current_prompt
        if state.current_plan != "":
            prompt += f"\n\nNOTE:\nBe aware of the plan you just made for this:\n{state.current_plan}\n"
        messages = await agent.generate(prompt=prompt)
        async for message in messages:
            is_result = False
            if message["type"] == "final_result":
                state.current_result = message["result"] or "No result was produced"
                content = message["result"] or "No result was produced"
                is_result = True
            elif message["type"] == "text":
                content = message["text"]
            elif message["type"] == "thinking":
                content = message["thinking"]
            elif message["type"] == "tool_call" or message["type"] == "tool_result":
                try:
                    content = json.dumps(
                        {k: v for k, v in message.items() if k != "type"}
                    )
                except Exception:
                    content = str({k: v for k, v in message.items() if k != "type"})
            else:
                content = ""
            async with ctx.store.edit_state() as state:
                state.chat_history.append(
                    ChatMessage(
                        content=content, role="assistant" if not is_result else "result"
                    )
                )
            ctx.write_event_to_stream(MessageEvent(message=message))
        return QuestionToHuman(
            question="Do you approve this result as the final result?",
            type="approve_final_result",
        )

    @step
    async def handle_plan(
        self, ev: Plan, ctx: Context[CodingWorkflowState]
    ) -> QuestionToHuman:
        state = await ctx.store.get_state()
        agent = cast(BaseCodingAgent, self._agent)
        prompt = state.current_prompt
        if state.current_plan != "":
            prompt += f"\n\nNOTE:\nBe aware of the previous plan you made:\n{state.current_plan}\n"
        messages = await agent.plan(prompt=prompt)
        async for message in messages:
            is_result = False
            if message["type"] == "final_result":
                state.current_result = message["result"] or "No result was produced"
                content = message["result"] or "No result was produced"
                is_result = True
            elif message["type"] == "text":
                content = message["text"]
            elif message["type"] == "thinking":
                content = message["thinking"]
            elif message["type"] == "tool_call" or message["type"] == "tool_result":
                try:
                    content = json.dumps(
                        {k: v for k, v in message.items() if k != "type"}
                    )
                except Exception:
                    content = str({k: v for k, v in message.items() if k != "type"})
            else:
                content = ""
            async with ctx.store.edit_state() as state:
                state.chat_history.append(
                    ChatMessage(
                        content=content, role="assistant" if not is_result else "result"
                    )
                )
            ctx.write_event_to_stream(MessageEvent(message=message))
        return QuestionToHuman(
            question="Do you approve the plan?", type="approve_final_result"
        )
