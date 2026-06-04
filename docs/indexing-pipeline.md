# Indexing Pipeline

The indexing pipeline turns a Python repository into searchable graph data.

Main file:

```text
backend/src/index_repo.py
```

## Input

The indexer accepts:

- A GitHub URL
- A local path when called directly from Python

From the UI/API, the normal input is a GitHub URL.

## API Start

The frontend sends:

```http
POST /index-repository
```

With body:

```json
{
  "url": "https://github.com/pallets/click"
}
```

The backend creates a job ID and starts indexing in a background thread.

## Progress Stages

The job status can show these stages:

- `cloning`
- `parsing`
- `edges`
- `writing`
- `done`

The frontend polls the status endpoint until the job is completed or failed.

## Step 1: Verify Neo4j

The indexer checks that Neo4j is reachable before doing heavy work.

If Neo4j is not running or credentials are wrong, indexing stops.

## Step 2: Check Remote SHA

For Git URLs, the indexer runs `git ls-remote` to get the latest commit SHA.

If the same repo URL and SHA are already stored in Neo4j metadata, the indexer skips the full process.

## Step 3: Resolve Source

For URLs:

- The repo is shallow-cloned into a temporary directory.
- Only the latest default branch state is downloaded.

For local paths:

- The path is validated and used directly.

## Step 4: Discover Python Files

File:

```text
backend/src/parser/file_discovery.py
```

The scanner finds `.py` files and skips folders like:

- `.git`
- `node_modules`
- `venv`
- `.venv`
- `__pycache__`
- `build`
- `dist`

It also computes repository stats such as total files and total lines.

## Step 5: Parse Definitions

File:

```text
backend/src/parser/ast_parser.py
```

Tree-sitter extracts:

- Functions
- Methods
- Classes
- Names
- File paths
- Start/end lines
- Docstrings
- Source code

Each graph node gets a stable ID:

```text
relative/path.py::symbol_name
relative/path.py::ClassName.method_name
```

## Step 6: Extract Call Edges

File:

```text
backend/src/parser/call_extractor.py
```

The call extractor finds in-project calls and writes them as:

```text
caller_node_id -> callee_node_id
```

Only calls that can be resolved to indexed project nodes are kept.

External calls like built-ins and third-party libraries are skipped.

## Step 7: Build Search Indexes

Files:

```text
backend/src/chromadb/node_chunker.py
backend/src/chromadb/ingestion.py
backend/src/chromadb/BM25_Ingest.py
```

The code nodes are prepared for retrieval:

- Large nodes can be chunked.
- ChromaDB stores embeddings for semantic search.
- BM25 stores a lexical keyword index.
- Metadata keeps the original Neo4j `node_id`.

## Step 8: Write Neo4j Graph

File:

```text
backend/src/indexer/neo4j_writer.py
```

The writer stores:

- `:Function` nodes
- `:Class` nodes
- `:File` nodes
- `:CALLS` relationships
- `:IndexMetadata` singleton node

Before writing, it wipes the old graph so the current repo is clean and consistent.

## Output

After indexing, the app can:

- List the indexed repo.
- Show the file tree.
- Show file content.
- Retrieve nodes through semantic and lexical search.
- Expand graph context from Neo4j.
- Answer questions using the indexed source code.

