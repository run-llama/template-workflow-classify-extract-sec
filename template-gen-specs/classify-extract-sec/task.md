We are creating a database of SEC filings, along with extracted structured information from the filings.

The goal of the database is for financial analysis & investment research.

Using LlamaClassify and LlamaExtract, create a workflow that will extract meaningful details about SEC filing documents.
Consider how the data may be queried and structured in a database.

Specifically, classify the document types into the following categories:
- 10-K
- 10-Q
- 8-K
- other

Each document type should have a distinct schema. Define the schema as a pydantic model using
structured fields. Make data optional if it may not be present or difficult to extract.

The different types should be displayed together in the UI as a table of documents, and clicking into the item should show the extracted data, according to the documents extracted schema.