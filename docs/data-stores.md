# Data Stores

CodeGraph-RAG uses three main storage systems.

## Neo4j

Neo4j stores the code graph and source code.

Main writer:

```text
backend/src/indexer/neo4j_writer.py
```

Main reader/config:

```text
backend/src/config/graphdb_config.py
backend/src/retrievers/implementations/graphdb_retriever.py
```

## Neo4j Nodes

### Function Nodes

Functions and methods are stored with the `:Function` label.

Common properties:

- `node_id`
- `name`
- `kind`
- `file_path`
- `start_line`
- `end_line`
- `source_code`
- `docstring`

### Class Nodes

Classes are stored with the `:Class` label.

Common properties are similar to function nodes.

### File Nodes

Source files are stored with the `:File` label.

Common properties:

- `path`
- `name`
- `content`

These nodes let the frontend show a file tree and file content without needing the cloned repo to stay on disk.

### Index Metadata Node

The project stores one metadata node:

```text
:IndexMetadata { id: "singleton" }
```

It stores:

- Repo URL
- Commit SHA
- Repo name
- Total files
- Total lines
- Indexed timestamp

This is used by `/repos` and by the SHA cache check.

## Neo4j Relationships

The main relationship is:

```text
(caller)-[:CALLS]->(callee)
```

It represents one indexed code node calling another indexed code node.

## Constraints

The writer creates uniqueness constraints for:

- Function `node_id`
- Class `node_id`
- File `path`

These help prevent duplicate graph data and make lookups faster.

## ChromaDB

ChromaDB stores embeddings for code chunks.

Main files:

```text
backend/src/chromadb/ingestion.py
backend/src/chromadb/node_chunker.py
backend/src/config/vectordb_config.py
```

Each Chroma document contains text built from:

- Node type
- Node name
- Docstring
- Source code or source chunk

Each Chroma metadata record keeps:

- `node_id`
- `parent_node_id`
- `file_path`
- `name`
- `kind`
- `docstring`
- `content_hash`
- Chunk information

The `node_id` connects Chroma search results back to Neo4j nodes.

## BM25

BM25 stores a keyword search index.

Main file:

```text
backend/src/chromadb/BM25_Ingest.py
```

Default path from config:

```text
./data/bm25.pkl
```

BM25 helps when the user query contains exact terms, function names, filenames, or keywords.

## Important Path Note

Make sure Chroma ingestion and retrieval use the same folder.

Recommended backend `.env`:

```env
CHROMA_PERSIST_DIR=./data/chroma_db
CHROMA_COLLECTION_NAME=codegraph_semantic
```

The retrieval config currently reads from:

```text
./data/chroma_db
```

If indexing writes to a different folder, queries may return no semantic results.

