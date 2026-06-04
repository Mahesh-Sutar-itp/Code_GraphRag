# Architecture

CodeGraph-RAG has two main parts:

- Backend: indexes repositories, stores code knowledge, retrieves relevant code, and answers questions.
- Frontend: lets the user index a repository, ask questions, view graph context, and inspect code.

## High-Level Flow

```text
GitHub repo URL
   |
   v
Backend indexer
   |
   +--> Tree-sitter parses Python files
   +--> Call extractor builds code relationships
   +--> Neo4j stores functions, classes, files, and CALLS edges
   +--> ChromaDB stores semantic code chunks
   +--> BM25 stores lexical search index

User question
   |
   v
Retrieval pipeline
   |
   +--> Dense semantic search
   +--> BM25 lexical search
   +--> Fusion and reranking
   +--> Neo4j graph expansion
   +--> Planner agent ranks nodes
   +--> Resolver agent answers with source context
```

## Backend Layers

### API Layer

File: `backend/main.py`

This exposes FastAPI routes for:

- Health check
- Listing indexed repositories
- Reading the file tree
- Reading file content
- Starting repository indexing
- Polling indexing job status
- Resolving user queries
- Fetching graph nodes/edges for selected node IDs

### Indexing Layer

Main file: `backend/src/index_repo.py`

This is the end-to-end indexing pipeline. It checks Neo4j, checks whether a remote repo changed, clones the repo when needed, discovers Python files, parses definitions, extracts edges, writes vector indexes, writes Neo4j data, and records metadata.

### Parser Layer

Folder: `backend/src/parser`

Important files:

- `repo_fetcher.py`: resolves a local path or Git URL.
- `file_discovery.py`: finds Python files and skips noisy folders.
- `ast_parser.py`: extracts functions, methods, classes, line numbers, docstrings, and source code.
- `call_extractor.py`: extracts in-project function/method calls and creates graph edges.

### Storage Layer

Important files:

- `backend/src/indexer/neo4j_writer.py`
- `backend/src/chromadb/ingestion.py`
- `backend/src/chromadb/BM25_Ingest.py`
- `backend/src/config/graphdb_config.py`
- `backend/src/config/vectordb_config.py`

Neo4j is the source of truth for graph structure and source code. ChromaDB and BM25 help find likely relevant nodes for a user query.

### Retrieval Layer

Folder: `backend/src/retrievers`

The retrieval pipeline uses:

- ChromaDB dense semantic search
- BM25 keyword search
- Reciprocal rank fusion
- Code reranking
- Neo4j graph expansion up to 2 hops

### Agent Layer

Folder: `backend/src/agent`

The agent workflow has two main LLM steps:

- Planner agent: ranks candidate graph nodes.
- Resolver agent: answers the user's question using selected source code.

## Frontend Layers

### App Shell

File: `frontend/src/App.tsx`

This controls the main UI state, repository selection, theme, and index modal.

### Layout

Folder: `frontend/src/components`

The layout has:

- Top bar
- Activity rail
- Left file pane
- Main chat panel
- Right drawer for graph/code context

### Features

Folder: `frontend/src/features`

Important feature areas:

- `repo`: empty state, repository dropdown, indexing modal
- `file-tree`: indexed file tree
- `chat`: chat messages, markdown rendering, input
- `graph`: React Flow graph view
- `code-viewer`: syntax-highlighted source viewer

## Important Design Choices

- The app indexes one repository at a time.
- Neo4j data is wiped before a new full graph write.
- Repo metadata is stored as a singleton `IndexMetadata` node.
- Index job status is in memory, so it resets when the backend restarts.
- The frontend polls indexing status every 700ms.
- The frontend expects backend CORS from `http://localhost:5173`.

