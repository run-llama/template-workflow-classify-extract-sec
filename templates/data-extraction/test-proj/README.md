# Data Extraction and Ingestion

This is a starter for a [`llama_deploy`](https://github.com/run-llama/cloud_llama_deploy) powered app.
See it's [getting started guide](https://github.com/run-llama/cloud_llama_deploy/tree/main/docs/guides/01-getting-started.md)
for more info on how to run this project.

The backend contains a single workflow that runs LlamaCloud Extraction, given your schema. The frontend exposes an
extraction review UI, where you can review and correct extractions. 

## Customizing the schema.

The starter contains a placeholder `MySchema` that is used for extraction. See [`schema.py`](./src/test-proj/schema.py). 

You should customize this `schema.py` for your use case to modify the extracted data. You can also rename the schema from `MySchema` to 
something more appropriate for your use case. Do a find and replace on "MySchema" to also fix the frontend references.

The frontend has a copy of the schema as a json schema, that it uses to introspect and generate an editing UI. Run `uv run export-types` to regenerate the frontend json schema.

## Customizing the application

This is meant to just be a starting place. You can add more workflows, and trigger them from the UI. For example, you could
add functionality sync to a downstream data sink to export the corrected data after review. Or you could add a workflow
that monitors a data source, and automatically triggers the extraction against the file.

### Running Workflows

The core value of this template is good extraction. The main python code is in the `src` directory.

Workflows can be triggered from the UI using `useWorkflow` react hooks from the `@llamaindex/ui` library.
You can also add a `if __name__ == "__main__":` handler to individual workflows to run and debug them directly.
The `process_file.py` has main handler that will upload a `test.pdf` from your current working directory so you
can test your extraction directly. Note, while `llamactl serve` will inject your LlamaCloud API key, you will need
to set a `LLAMA_CLOUD_API_KEY` in your `.env` file or set an env var to run the `__main__` handler directly.
