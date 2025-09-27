from pydantic import BaseModel
from workflows import Workflow, step, Context
from workflows.events import Event, StartEvent, StopEvent
from typing import Annotated, cast
from workflows.resource import Resource
from llama_index.llms.openai import OpenAI


class EmailClient:
    """A mock email client for sending emails."""

    def __init__(self, sender_email: str):
        self.sender_email = sender_email

    def send(self, receiver_email: str, subject: str, content: str) -> bool:
        print(
            f"Sent an email from {self.sender_email} to {receiver_email} with subject '{subject}' and content:\n{content}"
        )
        return True


class EmailStart(StartEvent):
    """An event that starts the email workflow."""

    receiver: str
    draft: str


async def get_llm(*args, **kwargs) -> OpenAI:
    return OpenAI("gpt-4.1")


class PreparedEmail(Event):
    sender: str
    receiver: str
    subject: str
    content: str


class SubjectAndContent(BaseModel):
    subject: str
    content: str


class EmailFlow(Workflow):
    @step
    async def prepare_email(
        self,
        ev: EmailStart,
        ctx: Context,
        llm: Annotated[OpenAI, Resource(get_llm)],
    ) -> PreparedEmail:
        email_content_response = await llm.as_structured_llm(
            SubjectAndContent
        ).acomplete(
            f"Given this email draft\n\n<draft>\n{ev.draft}\n</draft>\n\nplease create a fully-formed email message and subject to send. Respond in the format {{'subject': '...', 'content': '...'}}"
        )
        email_content = cast(SubjectAndContent, email_content_response.raw)

        return PreparedEmail(
            sender="noreply@example.com",
            receiver=ev.receiver,
            subject=email_content.subject,
            content=email_content.content,
        )

    @step
    async def send_email(
        self,
        ev: PreparedEmail,
        ctx: Context,
    ) -> StopEvent:
        client = EmailClient(sender_email=ev.sender)
        ctx.write_event_to_stream(ev)  # publish event to clients
        success = client.send(ev.receiver, ev.subject, ev.content)
        return StopEvent(
            result=(
                f"Email successfully sent from {ev.sender} to {ev.receiver}\nSubject: {ev.subject}\nContent: {ev.content}"
                if success
                else f"Failed to send email from {ev.sender} to {ev.receiver}\nSubject: {ev.subject}\nContent: {ev.content}"
            )
        )


async def main(sender: str, receiver: str, subject: str, draft: str) -> None:
    w = EmailFlow(timeout=60, verbose=False)
    result = await w.run(sender=sender, receiver=receiver, subject=subject, draft=draft)
    print(str(result))


workflow = EmailFlow(timeout=None)

if __name__ == "__main__":
    import asyncio
    import os
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument(
        "-r",
        "--receiver",
        required=True,
        help="Email for the receiver",
    )

    parser.add_argument("-d", "--draft", required=True, help="Draft for the email")

    args = parser.parse_args()

    if not os.getenv("OPENAI_API_KEY", None):
        raise ValueError(
            "You need to set OPENAI_API_KEY in your environment before using this workflow"
        )

    asyncio.run(
        main(
            receiver=args.receiver,
            draft=args.draft,
        )
    )
