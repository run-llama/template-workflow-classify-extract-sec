import asyncio
import random
import time

from pydantic import BaseModel, Field
from workflows import Context, Workflow, step
from workflows.events import Event, StartEvent, StopEvent, HumanResponseEvent

import logging

logger = logging.getLogger(__name__)


class TickEvent(Event):
    value: float
    timestamp_ms: int

    def scale(self, scale: float) -> "TickEvent":
        return TickEvent(
            value=self.value * scale,
            timestamp_ms=self.timestamp_ms,
        )

    @staticmethod
    def now() -> "TickEvent":
        return TickEvent(
            value=TickEvent.random(), timestamp_ms=int(time.monotonic() * 1000)
        )

    @staticmethod
    def random() -> float:
        return random.uniform(0.0, 1.0)


class ProbeEvent(HumanResponseEvent):
    n_ticks: int = 10


class SignalScaleEvent(HumanResponseEvent):
    scale: float


class WaitUntilEvent(Event):
    wake_at_ms: int


class SnapshotEvent(Event):
    last_tick_ms: int | None
    recent_ticks: list[TickEvent]
    scale: float


class TickerState(BaseModel):
    history: list[TickEvent] = Field(default_factory=list)
    last_tick_ms: int | None = None
    end_at_ms: int | None = None
    scale: float = 1.0


class CancelEvent(HumanResponseEvent):
    pass


class TickerWorkflow(Workflow):
    @step
    async def start(self, ev: StartEvent, ctx: Context[TickerState]) -> TickEvent:
        async with ctx.store.edit_state() as state:
            # 10 minutes
            state.end_at_ms = (int(time.monotonic()) + 60) * 1000
        return TickEvent.now()

    @step
    async def tick(
        self, ev: TickEvent, ctx: Context[TickerState]
    ) -> StopEvent | WaitUntilEvent:
        state = await ctx.store.get_state()
        scaled_ev = ev.scale(state.scale)
        async with ctx.store.edit_state() as state:
            state.last_tick_ms = scaled_ev.timestamp_ms
            state.history.append(scaled_ev)

        ctx.write_event_to_stream(scaled_ev)

        if state.end_at_ms is not None and ev.timestamp_ms >= state.end_at_ms:
            logger.info(f"completed at {ev.timestamp_ms}")
            return StopEvent()

        return WaitUntilEvent(wake_at_ms=(int(time.monotonic()) + 0.5) * 1000)

    @step
    async def wait_until(
        self, ev: WaitUntilEvent, ctx: Context[TickerState]
    ) -> TickEvent:
        now_ms = int(time.monotonic()) * 1000
        remaining_ms = max(0, ev.wake_at_ms - now_ms)
        if remaining_ms:
            await asyncio.sleep(remaining_ms / 1000)
        return TickEvent(value=TickEvent.random(), timestamp_ms=ev.wake_at_ms)

    @step
    async def probe(self, ev: ProbeEvent, ctx: Context[TickerState]) -> None:
        state = await ctx.store.get_state()
        ctx.write_event_to_stream(
            SnapshotEvent(
                last_tick_ms=state.last_tick_ms,
                recent_ticks=state.history[-ev.n_ticks :],
                scale=state.scale,
            )
        )

    @step
    async def signal_scale(
        self, ev: SignalScaleEvent, ctx: Context[TickerState]
    ) -> None:
        async with ctx.store.edit_state() as state:
            state.scale = ev.scale

    @step
    async def cancel(self, ev: CancelEvent) -> StopEvent:
        return StopEvent(complete=True)


state_query_workflow = TickerWorkflow(timeout=None)
