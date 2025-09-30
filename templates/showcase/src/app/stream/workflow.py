import asyncio

from workflows import Context, Workflow, step
from workflows.events import Event, StartEvent, StopEvent


class WordStreamEvent(Event):
    word: str


class FullTextStopEvent(StopEvent):
    text: str


class StreamWorkflow(Workflow):
    @step
    async def stream_text(self, ev: StartEvent, ctx: Context) -> FullTextStopEvent:
        # Simple text to stream
        text = (
            "Workflows enable powerful streaming patterns for AI applications. "
            "By emitting events as data becomes available, you can create responsive "
            "user experiences that show progress in real-time. This approach works "
            "beautifully for text generation, data processing pipelines, and long-running "
            "operations where immediate feedback improves the user experience significantly."
        )
        words = text.split()

        # Stream each word with a short delay
        for word in words:
            ctx.write_event_to_stream(WordStreamEvent(word=word))
            await asyncio.sleep(0.08)

        # Return the full text at the end
        return FullTextStopEvent(text=text)


stream_workflow = StreamWorkflow(timeout=None)
