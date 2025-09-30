import asyncio
import random
import time
from typing import Annotated

from workflows import Context, Workflow, step
from workflows.events import StartEvent, StopEvent, Event
from workflows.resource import Resource


class BatchPlannedEvent(Event):
    task_ids: list[int]


class TaskWorkEvent(Event):
    task_id: int


class TaskStartedEvent(Event):
    task_id: int
    started_at_ms: int


class TaskProgressEvent(Event):
    task_id: int
    percent: int
    stage_index: int
    timestamp_ms: int


class TaskCompletedEvent(Event):
    task_id: int
    started_at_ms: int
    finished_at_ms: int
    duration_ms: int


def _semaphore_factory(*_args, **_kwargs) -> asyncio.Semaphore:
    return asyncio.Semaphore(3)


class FanOutWorkflow(Workflow):
    @step
    async def start(self, ev: StartEvent, ctx: Context) -> TaskWorkEvent | None:
        num_tasks = 8
        await ctx.store.set("num_to_collect", num_tasks)
        task_ids = list(range(num_tasks))
        ctx.write_event_to_stream(BatchPlannedEvent(task_ids=task_ids))
        for task_id in task_ids:
            ctx.send_event(TaskWorkEvent(task_id=task_id))
        return None

    @step(num_workers=3)
    async def process_task(
        self,
        ev: TaskWorkEvent,
        ctx: Context,
        sem: Annotated[asyncio.Semaphore, Resource(_semaphore_factory)],
    ) -> TaskCompletedEvent:
        await sem.acquire()
        try:
            start_ms = int(time.time() * 1000)
            ctx.write_event_to_stream(
                TaskStartedEvent(task_id=ev.task_id, started_at_ms=start_ms)
            )

            total_stages = 20
            # make some especially slow to demonstrate later tasks completing before earlier tasks
            slowness_multiplier = (
                3 if ev.task_id == 0 else random.choice([0.1, 0.2, 0.5, 4])
            )
            for stage in range(total_stages):
                await asyncio.sleep(random.uniform(0.05, 0.15) * slowness_multiplier)
                percent = int(((stage + 1) / total_stages) * 100)
                ctx.write_event_to_stream(
                    TaskProgressEvent(
                        task_id=ev.task_id,
                        percent=percent,
                        stage_index=stage,
                        timestamp_ms=int(time.time() * 1000),
                    )
                )

            finished_ms = int(time.time() * 1000)
            duration_ms = finished_ms - start_ms
            return TaskCompletedEvent(
                task_id=ev.task_id,
                started_at_ms=start_ms,
                finished_at_ms=finished_ms,
                duration_ms=duration_ms,
            )
        finally:
            try:
                sem.release()
            except Exception:
                pass

    @step
    async def finalize(self, ev: TaskCompletedEvent, ctx: Context) -> StopEvent | None:
        num_to_collect = await ctx.store.get("num_to_collect")
        events = ctx.collect_events(ev, [TaskCompletedEvent] * num_to_collect)
        if events is None:
            return None
        return StopEvent(complete=True)


fanout_workflow = FanOutWorkflow(timeout=None)
