import asyncio
import time

from workflows import Context, Workflow, step
from workflows.events import (
    HumanResponseEvent,
    InputRequiredEvent,
    StartEvent,
    StopEvent,
    Event,
)
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class PingEvent(StartEvent):
    message: str


class PongEvent(Event):
    message: str


class WorkflowCompletedEvent(StopEvent):
    timestamp: str


class PauseEvent(InputRequiredEvent):
    timestamp: str


class ResumeEvent(HumanResponseEvent):
    should_continue: bool


class OkGoEvent(Event):
    message: str


class DefaultWorkflow(Workflow):
    @step
    async def start(self, event: PingEvent, context: Context) -> OkGoEvent:
        return OkGoEvent(message="OK GO")

    @step
    async def loop(
        self, event: ResumeEvent | OkGoEvent, context: Context
    ) -> PauseEvent | WorkflowCompletedEvent:
        if isinstance(event, ResumeEvent) and not event.should_continue:
            return WorkflowCompletedEvent(
                timestamp="workflow completed at "
                + datetime.now().isoformat(timespec="seconds")
            )
        start = time.monotonic()
        logger.info(f"Received message!!!!!: {event}")
        for i in range(5):
            logger.info(f"Processing message: {event} {i}")
            elapsed = (time.monotonic() - start) * 1000
            context.write_event_to_stream(
                PongEvent(message=f"+{elapsed:.0f}ms PONG {i + 1}/5 ")
            )
            await asyncio.sleep(0.2)

        return PauseEvent(
            timestamp="workflow paused at "
            + datetime.now().isoformat(timespec="seconds")
        )


workflow = DefaultWorkflow(timeout=None)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    async def main():
        print(await DefaultWorkflow().run(message="Hello!"))

    asyncio.run(main())
