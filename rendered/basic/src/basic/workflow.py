from workflows import Workflow, step, Context
from workflows.events import StartEvent, StopEvent, Event
import asyncio


class Start(StartEvent):
    pass


class Hello(Event):
    message: str


class BasicWorkflow(Workflow):
    @step
    async def hello(self, event: Start, context: Context) -> StopEvent:
        context.write_event_to_stream(
            Hello(message="🦙 Hello from the basic template.")
        )
        await asyncio.sleep(0)
        return StopEvent(result=("Edit src/basic/workflow.py to get started."))


workflow = BasicWorkflow(timeout=None)


if __name__ == "__main__":

    async def main() -> None:
        print(await BasicWorkflow().run())

    asyncio.run(main())
