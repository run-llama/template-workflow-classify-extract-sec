This is a LlamaAgents powered project. It is meant to be modified and adapted to novel use cases.

When implementing a new workflow, or adding functionality, always first search for high-quality reference implementations. Make use of the `tmpl` `search-templates` tool to find matching snippets. It uses keyword based search. These are the best source of examples, as they are similar apps achieving similar goals.

When you cannot find examples, always reference the llama-index-docs MCP tool when integrating with llama-index libraries or llama-cloud. This will ensure you are using the latest syntax and library names to install, etc.

The llama-index-docs MCP tool documents:
- workflows - LlamaIndex's library for building durable agentic applications
- LlamaAgents - a suite of tools for building agents, across workflows and LlamaCloud
  - `llamactl` - the CLI for developing and deploying LlamaAgents, powered by LlamaIndex workflows
  - LlamaAgents configuration
  - Agent Data - a way to store ad-hoc data in LlamaCloud
- LlamaCloud - best in class primitives for parsing file formats to text, extracting structured data from docs or text, and indexing and querying for retrieval.
- LlamaIndex - LlamaIndex's core OSS framework for creating generative AI applications. Abstracts away common LLM providers, and other generate AI application integrations, and common application patterns.


Toolchain:
Package Manager: `uv` is the package manager for this project. It is used to install dependencies, run tests, and build the project. Install dependencies with `uv add <package>`.

Linting: `hatch`/`ruff`/`ty` - run the provided linters with the hatch commands

e.g. `uv run hatch run format` to format the code.

All commands:
- `format` - format the code with ruff
- `format-check` - check the code with ruff
- `lint` - lint the code with ruff
- `lint-check` - check the code with ruff
- `typecheck` - typecheck the code with ty
- `test` - run the tests with pytest
- `all-check` - run all the checks
- `all-fix` - run all the fixes. Prefer using this over `all-check`,
  as it will just fix things, and tell you if there's anything additional
  that needs to be fixed.


System Tools:
- Install missing dependencies. Use tools at your disposal to find correct dependencies.
- Use `uv` for python code. Make sure you have its venv activated, or prefix commands with `uv run`.
- If there is a `/ui` directory, use the configured javascript package manager to install dependencies. Refer to the version in the `package.json`'s `packageManager` field.

Coding Style:
- Do not make messy or defensive code. Avoid unnecessary try catches. Do not add try catches or other optional imports. Do not use getattr/setattr. These are signs of underlying issues, or an incorrectly configured linter or environment.
- When adding new code or installing a dependency, use the latest version, and make sure to use the latest interface, looking up the interfaces where applicable.
- Don't pass through silent failures, better to explicitly fail if you can
- Err on the side of generating LLM-powered flows instead of heavy code/heuristic based decision making - especially in cases where you're dealing with a lot of text inputs and want the logic to be generalizable.
- Don't mix environment variable parsing, and client or service configuration into the main code files. Organize dependencies and env var configuration into a stand-alone file. E.g. `config.py`. If dependencies grow, split up the files further.
- Add and run unit tests to validate your changes.

Workflows and Workflows served via `llamactl` CLI:
- workflow state and events are stored durably. Avoid storing large amounts of data in the state, or passing around large amounts of data in events.
- Try to split steps up into different workflow steps if possible, instead of putting too much logic per workflow step.
- Data that should be published to the client should be written with `ctx.write_event_to_stream()` from the workflow's steps. 
- Prefer to use typed APIs with the workflows library: 
  - Subclass `StartEvent`, `StopEvent`, `InputRequiredEvent`, `HumanResponseEvent` with custom
    types in order to clearly define the expected input and output of the workflow step.
  - When using the Workflow state store, create a custom state type, and use typed Context, e.g. `Context[MyStateType]`, then calls to `state = await ctx.store.get_state()` and `async with ctx.store.edit_state() as state` will have `MyStateType` as the type of the `state` variable.
  - Use annotated resource parameters in workflow steps for dependency injection. e.g. `def my_step(ctx: Context, ev: StartEvent, llm: Annotated[OpenAI, Resource(get_llm)])`
- When adding new workflows that should be exposed, make sure to configure the pyproject.toml for the `llamactl` CLI with a `[tool.llamadeploy]` section.
- Usually, just configure workflows with a None timeout unless they really should have a timeout.

LlamaCloud:
- Use llama cloud services (Parsing, Extracting, Indexes, Agent Data) where relevant. LlamaAgent projects, like this one, are meant to be built on top of these services.
- Make use of Agent Data to store useful information that may want to be queried by a client, without requiring a workflow as a go-between
- Types in LlamaExtract's extracted schema should generally be optional - to allow LlamaExtract room to fail (it can sometimes return None for fields, and if the field is typed as required the script will break).
- AsyncAgentDataClient has a generic for the schema of the data. Make use of it to facilitate type safety and autocomplete. For example `AsyncAgentDataClient[ExtractedData[InvoiceData]]` for extracted data, or `AsyncAgentDataClient[SomeOtherDataSchema]` for misc data.

LlamaIndex
- If you use an LLM, use llama_index's openai, and `PromptTemplate` abstractions. Use an LLMs structured prediction functions for simple and fast typed outputs where the detailed parsing and high-accuracy of LlamaExtract is not necessary.
- Prefer using `FunctionAgent` for modelling chat interactions powered by tools, such as retrieval.


Integrations:
- When using llama-cloud-services make sure to add `llama_cloud = true` to the `[tool.llamadeploy]` section of `pyproject.toml`. This will set appropriate environment variables to enable the use of llama-cloud-services in the workflow automatically when using `llamactl`.
- When building llama cloud based workflows, pass around llama cloud file references, rather than file paths. Reference and search the other existing templates to understand llama cloud file integrations to upload and download files.
- When storing results from LlamaExtract, use `ExtractedData.from_extraction_result(extraction_result)`. `ExtractedData` parses, and has  fields to store: citations, confidence scores, and track human corrections to the extracted data.
- When adding new environment variables that are critical to the functionality of the workflow, update the `pyproject.toml` with `required_env_vars = ["NEW_ENV_VAR"]` in the `[tool.llamadeploy]` section. This will prompt users to input them before starting the workflow.
