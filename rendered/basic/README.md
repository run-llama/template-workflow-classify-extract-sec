# Email Workflow Example

This example demonstrates how to build an event-driven, async-first workflow for sending emails using [llama-index-workflows](https://github.com/run-llama/llama-index-workflows). The workflow uses an LLM to generate email content and sends emails to internal recipients only.

## Installation

Install all required dependencies (including llama-index-workflows and OpenAI LLM support):

```bash
pip install -e .
```

## Usage

Run the workflow from the command line:

```bash
python -m basic.workflow \
  --sender you@example.com \
  --receiver recipient@example.com \
  --subject "Quarterly Update" \
  --draft "Here's a draft for the quarterly update email."
```

**Note:** You must set your `OPENAI_API_KEY` in the environment before running.

## Workflow Overview

- **prepare_email**:
  Uses an LLM to generate a fully-formed email from your draft and subject.

- **send_email**:
  Sends the generated email to the single receiver and finishes the workflow.

## Customization

- Replace the `EmailClient` logic with your own email sending implementation
- Extend the workflow with additional steps or validation as needed

## References

- [llama-index-workflows documentation](https://github.com/run-llama/llama-index-workflows)
- [OpenAI LLM integration](https://github.com/run-llama/llama-index-llms-openai)
