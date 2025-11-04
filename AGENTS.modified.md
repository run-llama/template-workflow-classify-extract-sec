# LlamaCloud Services Integration Guide for Coding Agents

## Project Setup & Environment

### Package Management
This project uses `uv` for package management. All commands should be run with:

```bash
uv run <command>
```

Or activate the virtual environment first:
```bash
source .venv/bin/activate
<command>
```

### Installing LlamaCloud Services
Add LlamaCloud Services to your project:

```bash
uv add llama-cloud-services
```

### API Key Configuration
Before using any LlamaCloud services, set your API key as an environment variable:

```bash
export LLAMA_CLOUD_API_KEY="llx-..."
```

The API key does not need to be passed directly to service constructors—it will be read from the environment.

---

## LlamaCloud Services Overview

LlamaCloud provides four main services for intelligent document processing:

1. **LlamaParse** - Parse and extract text, charts, tables, and images from unstructured files
2. **LlamaClassify** - Automatically categorize documents using natural-language rules
3. **LlamaExtract** - Extract structured data following specific patterns
4. **LlamaCloud Index** - Store, index, and retrieve documents for RAG applications

---

## Service Integration Examples

### 1. LlamaParse - Document Parsing

#### Basic Usage
```python
from llama_cloud_services import LlamaParse

parser = LlamaParse(
    parse_mode="parse_page_with_agent",
    model="openai-gpt-4-1-mini",
    high_res_ocr=True,
    adaptive_long_table=True,
    outlined_table_extraction=True,
    output_tables_as_HTML=True,
    result_type="markdown",
    project_id=project_id,
    organization_id=organization_id,
)

# Sync parsing
result = parser.parse("./my_file.pdf")

# Async parsing
result = await parser.aparse("./my_file.pdf")

# Batch processing
results = parser.parse(["./file1.pdf", "./file2.pdf"])
```

#### Working with Parse Results
```python
# Get different document formats
markdown_docs = result.get_markdown_documents(split_by_page=True)
text_docs = result.get_text_documents(split_by_page=False)
image_docs = result.get_image_documents(
    include_screenshot_images=True,
    image_download_dir="./images"
)

# Extract tables
result = parser.get_json_result("./my_file.pdf")
tables = parser.get_tables(result)
```

#### Parse Mode Presets
```python
# Cost-Effective Mode
parser = LlamaParse(
    parse_mode="parse_page_with_llm",
    high_res_ocr=True,
    adaptive_long_table=True,
    outlined_table_extraction=True,
    output_tables_as_HTML=True,
    result_type="markdown",
)

# Agentic Mode (Default) - Recommended
parser = LlamaParse(
    parse_mode="parse_page_with_agent",
    model="openai-gpt-4-1-mini",
    high_res_ocr=True,
    adaptive_long_table=True,
    outlined_table_extraction=True,
    output_tables_as_HTML=True,
    result_type="markdown",
)

# Agentic Plus Mode - Highest Quality
parser = LlamaParse(
    parse_mode="parse_page_with_agent",
    model="anthropic-sonnet-4.0",
    high_res_ocr=True,
    adaptive_long_table=True,
    outlined_table_extraction=True,
    output_tables_as_HTML=True,
    result_type="markdown",
)
```

---

### 2. LlamaExtract - Structured Data Extraction

#### Quick Start
```python
from llama_cloud_services import LlamaExtract
from llama_cloud import ExtractConfig, ExtractMode, ExtractTarget
from pydantic import BaseModel, Field

# Initialize
extractor = LlamaExtract(
    show_progress=True,
    check_interval=5,
    project_id=project_id,
    organization_id=organization_id,
)

# Define schema
class Resume(BaseModel):
    name: str = Field(description="Full name of candidate")
    email: str = Field(description="Email address")
    skills: list[str] = Field(description="Technical skills")

# Configure extraction
config = ExtractConfig(
    extraction_mode=ExtractMode.MULTIMODAL,
    extraction_target=ExtractTarget.PER_DOC,
    system_prompt="<context>",
    cite_sources=True,
    use_reasoning=True,
    confidence_scores=True,
)

# Extract
result = extractor.extract(Resume, config, "resume.pdf")
print(result.data)
```

#### Extraction Modes
- **FAST** - Fastest processing, simple documents, no OCR
- **BALANCED** - Good speed/accuracy tradeoff
- **MULTIMODAL** - Recommended for visually rich documents
- **PREMIUM** - Highest accuracy with advanced OCR

#### Multiple Input Types
```python
# From file path
result = extractor.extract(Resume, config, "resume.pdf")

# From file handle
with open("resume.pdf", "rb") as f:
    result = extractor.extract(Resume, config, f)

# From text content
from llama_cloud_services.extract import SourceText
text = "Name: John Doe\nEmail: john@example.com"
result = extractor.extract(Resume, config, SourceText(text_content=text))
```

#### Async Extraction
```python
import asyncio

async def extract_documents():
    # Single file
    result = await extractor.aextract(Resume, config, "resume.pdf")
    
    # Queue multiple jobs
    jobs = await extractor.queue_extraction(
        Resume, config, ["resume1.pdf", "resume2.pdf"]
    )
    
    # Get results
    results = [agent.get_extraction_run_for_job(job.id) for job in jobs]
    return results
```

#### Extraction Agents (Advanced)
For reusable extraction workflows:

```python
# Create agent
agent = extractor.create_agent(
    name="resume-parser",
    data_schema=Resume,
    config=config
)

# Use agent
result = agent.extract("resume.pdf")

# Batch processing
jobs = await agent.queue_extraction(["resume1.pdf", "resume2.pdf"])

# Manage agents
agents = extractor.list_agents()
agent = extractor.get_agent(name="resume-parser")
extractor.delete_agent(agent.id)
```

---

### 3. LlamaClassify - Document Classification

Automatically categorize documents before extraction:

```python
from llama_cloud_services.beta.classifier.client import ClassifyClient
from llama_cloud.types import ClassifierRule

classifier = ClassifyClient.from_api_key(api_key)

# Define classification rules
rules = [
    ClassifierRule(
        type="invoice",
        description="Documents with line items, prices, and payment terms",
    ),
    ClassifierRule(
        type="contract",
        description="Legal agreements with terms and signatures",
    ),
]

# Classify PDF directly
result = await classifier.aclassify_file_path(
    rules=rules,
    file_input_path="document.pdf",
)

classification = result.items[0].result
print(f"Type: {classification.type}")
print(f"Confidence: {classification.confidence:.2%}")
```

#### Parse → Classify → Extract Workflow
```python
# 1. Parse
parser = LlamaParse(result_type="markdown")
parse_result = await parser.aparse("document.pdf")
markdown_content = await parse_result.aget_markdown()

# 2. Classify
classification = await classifier.aclassify_file_path(
    rules=rules, file_input_path="temp.md"
)
doc_type = classification.items[0].result.type

# 3. Extract with appropriate schema
if doc_type == "invoice":
    schema = InvoiceSchema
elif doc_type == "contract":
    schema = ContractSchema

source_text = SourceText(text_content=markdown_content)
extraction_result = extractor.extract(schema, config, source_text)
```

---

## Best Practices for Agents

1. **Always set API key in environment** - Don't hardcode credentials
2. **Use appropriate parse modes** - Balance cost and quality (Agentic Mode recommended)
3. **Choose extraction modes wisely** - MULTIMODAL recommended for most documents
4. **Classify before extracting** - Route different document types to appropriate schemas
5. **Use agents for repeated workflows** - Create extraction agents for reusable patterns
6. **Handle async properly** - Use `aparse`, `aextract` for better performance
7. **Validate code before committing** - Run `uv run hatch run all-fix`

---

## Supported File Types

- **Documents**: PDF, Word (.docx)
- **Text**: .txt, .csv, .json, .html, .md
- **Images**: .png, .jpg, .jpeg