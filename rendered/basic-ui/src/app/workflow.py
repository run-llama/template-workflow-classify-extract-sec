from workflows import Context, Workflow, step
from workflows.events import StartEvent, StopEvent


class Start(StartEvent):
    pass


class BasicWorkflow(Workflow):
    @step
    async def hello(self, event: Start, context: Context) -> StopEvent:
        return StopEvent(
            result=(
                "Hello from the basic-ui backend. Edit src/app/workflow.py to get started."
            )
        )


workflow = BasicWorkflow(timeout=None)
