# CodeGraph-RAG Backend

This folder contains the FastAPI backend for CodeGraph-RAG.

It handles:

- Repository indexing
- Python AST parsing
- Call graph extraction
- Neo4j graph storage
- ChromaDB and BM25 indexing
- Retrieval pipeline
- Planner/resolver agent workflow

Run locally:

```bash
uv sync
uv run uvicorn main:app --reload
```

Read the main project documentation from the repository root:

- [Project README](../README.md)
- [Backend Guide](../docs/backend.md)
- [Setup Guide](../docs/setup.md)
- [API Reference](../docs/api-reference.md)
- [Indexing Pipeline](../docs/indexing-pipeline.md)
- [Query Resolution Flow](../docs/query-resolution-flow.md)
