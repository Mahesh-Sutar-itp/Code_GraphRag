# CodeGraph-RAG

CodeGraph-RAG is a full-stack project that lets you index a Python GitHub repository and then ask questions about that codebase in plain English.

The backend reads the repository, extracts functions/classes and call relationships, stores the structure in Neo4j, stores searchable code chunks in ChromaDB/BM25, and uses an agent workflow to answer questions with relevant code context. The frontend gives a simple UI for indexing a repo, chatting with the codebase, viewing related graph nodes, and opening source snippets.

## What You Can Do

- Index a public Python repository from a GitHub URL.
- Browse indexed files from the UI.
- Ask questions like "Where is authentication handled?" or "Explain this pipeline."
- See the related code graph for an answer.
- Open the exact code nodes used as context.
- Re-index a repo when its latest commit changes.

## Project Structure

```text
codegraph-rag/
  backend/     FastAPI API, indexer, retrievers, agents, Neo4j and ChromaDB logic
  frontend/    React + Vite UI for indexing, chatting, graph view, and code viewer
  docs/        Simple detailed documentation for each topic
```

## Quick Start

### 1. Start Required Services

Neo4j must be running before indexing.

The backend also registers tracing with Phoenix at `http://localhost:6006/v1/traces`. Run Phoenix if you want tracing. If Phoenix is not running, check backend startup behavior in your environment.

### 2. Configure Backend Environment

Create `backend/.env`:

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password
GITHUB_TOKEN=your_github_models_or_azure_openai_token
```

### 3. Run Backend

```bash
cd backend
uv sync
uv run uvicorn main:app --reload
```

Backend API runs at:

```text
http://localhost:8000
```

### 4. Run Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at:

```text
http://localhost:5173
```

## Main Workflow

1. Open the frontend.
2. Click index/new repository.
3. Paste a GitHub repository URL.
4. Wait for indexing to finish.
5. Ask a question about the codebase.
6. Read the answer, inspect the graph, and open related source code.

## Documentation

For more depth, read the topic docs:

- [Setup Guide](docs/setup.md)
- [Architecture](docs/architecture.md)
- [Backend Guide](docs/backend.md)
- [Frontend Guide](docs/frontend.md)
- [Indexing Pipeline](docs/indexing-pipeline.md)
- [Query Resolution Flow](docs/query-resolution-flow.md)
- [API Reference](docs/api-reference.md)
- [Data Stores](docs/data-stores.md)
- [Operational Hardening](docs/operational-hardening.md)
- [Troubleshooting](docs/troubleshooting.md)

There are also older backend notes in [backend/docs](backend/docs).

## Tech Stack

- Backend: Python, FastAPI, Google ADK, LiteLLM, Tree-sitter, Neo4j, ChromaDB, BM25, sentence-transformers
- Frontend: React, TypeScript, Vite, Tailwind CSS, TanStack Query, Zustand, React Flow
- Databases: Neo4j for graph data, ChromaDB for semantic search, BM25 pickle index for lexical search

## Current Scope

The project is currently focused on Python repositories. It indexes one repository at a time in Neo4j, stores repo metadata as a singleton node, and uses in-memory job status for indexing progress. Job status is reset when the backend restarts.
