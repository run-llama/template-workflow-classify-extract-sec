# Data Extraction and Ingestion

This is a starter for a Llama Agents. See the [documentation](https://developers.llamaindex.ai/python/cloud/llamaagents/getting-started) for more info.

The backend contains a single workflow that runs LlamaCloud Extraction, given your schema. The frontend exposes an
extraction review UI, where you can review and correct extractions. 

## Customizing the schema.

The starter contains a placeholder `MySchema` that is used for extraction. See [`schema.py`](./src/extraction_review/schemas.py). 

You should customize this `schema.py` for your use case to modify the extracted data. You can also rename the schema from `MySchema` to 
something more appropriate for your use case. Do a find and replace on "MySchema" to also fix the frontend references.

The frontend has a copy of the schema as a json schema, that it uses to introspect and generate an editing UI. Run `uv run export-types` to regenerate the frontend json schema.

## Customizing the application

This is meant to just be a starting place. You can add more workflows, and trigger them from the UI. For example, you could
add functionality sync to a downstream data sink to export the corrected data after review. Or you could add a workflow
that monitors a data source, and automatically triggers the extraction against the file.
