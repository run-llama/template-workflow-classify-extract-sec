# SEC Filing Data Extraction and Analysis

A LlamaAgents application for extracting structured information from SEC filings using LlamaClassify and LlamaExtract. This application automatically classifies SEC documents (10-K, 10-Q, 8-K, or other) and extracts relevant financial and business information tailored to each filing type.

# Running the application

This is a starter for LlamaAgents. See the [LlamaAgents (llamactl) getting started guide](https://developers.llamaindex.ai/python/llamaagents/llamactl/getting-started/) for context on local development and deployment.

To run the application locally, clone this repo, install [`uv`](https://docs.astral.sh/uv/) and run `uvx llamactl serve`.

This application can also be deployed directly to [LlamaCloud](https://cloud.llamaindex.ai) via the UI, or with `llamactl deployment create`.

## Features

- **Intelligent Classification**: Uses LlamaClassify to automatically identify SEC filing types (10-K, 10-Q, 8-K, other)
- **Dynamic Schema Selection**: Applies specialized extraction schemas based on document type
- **Comprehensive Data Extraction**: Extracts filing-specific information:
  - **10-K**: Annual reports with financial metrics, risk factors, business descriptions, executive information
  - **10-Q**: Quarterly reports with period-over-period comparisons and updates
  - **8-K**: Current reports with material event information and impact analysis
  - **Other**: Catch-all for S-1, DEF 14A, 13F, and other filing types
- **Agent Data Storage**: Stores extracted data in LlamaCloud Agent Data for easy querying and analysis
- **UI Integration**: Web interface for reviewing and managing extracted data

## Example Documents

You can find sample SEC filings PDFs to test the application with [here](https://github.com/run-llama/llama-datasets/tree/main/llama_agents/sec/).


## Configuration

All main configuration is in `src/extraction_review/config.py`

## How It Works

The application uses a multi-step workflow powered by LlamaIndex:

1. **File Upload**: User uploads an SEC filing document through the UI
2. **Download**: File is downloaded from LlamaCloud storage
3. **Classification**: LlamaClassify analyzes the first 5 pages to determine filing type (10-K, 10-Q, 8-K, or other)
4. **Schema Selection**: Appropriate extraction schema is selected based on classification
5. **Extraction**: LlamaExtract processes the document using the selected schema
6. **Storage**: Extracted data is stored in Agent Data with deduplication by file hash
7. **Review**: UI displays extracted data for review and editing

### Workflows

The application includes two main workflows:

- **`process-file`** (`src/extraction_review/process_file.py`): Main workflow for processing SEC filings
  - Steps: download → classify → extract → store
  - Uses typed context to pass state between steps
  - Streams progress updates to UI via `Status` events

- **`metadata`** (`src/extraction_review/metadata_workflow.py`): Exposes configuration metadata to UI
  - Returns JSON schema and collection name for dynamic UI generation

## Linting and Type Checking

Python and javascript packages contain helpful scripts to lint, format, and type check the code.

To check and fix python code:

```bash
uv run hatch run lint
uv run hatch run typecheck
uv run hatch run test
# run all at once
uv run hatch run all-fix
```

To check and fix javascript code, within the `ui` directory:

```bash
pnpm run lint
pnpm run typecheck
pnpm run test
# run all at once
pnpm run all-fix
```
