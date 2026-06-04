# Backend Guide

The backend is a FastAPI application with indexing, retrieval, and agent-based query answering.

## Entry Point

Main file:

```text
backend/main.py
```

Run it with:

```bash
cd backend
uv run uvicorn main:app --reload
```

## Main Backend Responsibilities

- Accept repository indexing requests.
- Track indexing progress in memory.
- Store and read indexed repository metadata.
- Serve file tree and file content to the frontend.
- Resolve user questions through the retrieval and agent workflow.
- Return graph context for the frontend graph view.

## Important Routes

- `GET /health`
- `GET /repos`
- `GET /repos/{repo_id}/tree`
- `GET /repos/{repo_id}/files?path=...`
- `POST /index-repository`
- `GET /index-repository/{job_id}/status`
- `POST /resolve-query`
- `POST /subgraph`

See [API Reference](api-reference.md) for request and response details.

## Indexing Code

Main orchestrator:

```text
backend/src/index_repo.py
```

It runs these steps:

1. Verify Neo4j connection.
2. Check remote commit SHA for cache skipping.
3. Clone repo or use local path.
4. Discover Python files.
5. Parse functions, methods, and classes.
6. Extract call edges.
7. Chunk and ingest nodes into ChromaDB and BM25.
8. Write nodes, edges, files, and metadata to Neo4j.

## Query Code

Main route:

```text
POST /resolve-query
```

Main workflow:

```text
backend/src/agent/query_resolution_workflow.py
backend/src/agent/nodes.py
```

The query flow:

1. Receive user question.
2. Retrieve candidate nodes and edges.
3. Planner agent ranks the most useful nodes.
4. Source code for selected nodes is fetched.
5. Resolver agent writes the answer.
6. Response includes answer text and relevant `node_ids`.

## Retrieval Code

Main file:

```text
backend/src/retrievers/retrieval_pipeline.py
```

The retrieval pipeline combines:

- Dense vector search from ChromaDB
- BM25 keyword search
- Reciprocal rank fusion
- Reranking
- Neo4j graph expansion

## Configuration

Neo4j config:

```text
backend/src/config/graphdb_config.py
```

Vector DB config:

```text
backend/src/config/vectordb_config.py
```

Model config:

```text
backend/src/agent/llm_models.py
```

Common environment variables:

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password
GITHUB_TOKEN=your_github_models_or_azure_openai_token
```

## Notes

- The backend currently indexes Python files only.
- `index_jobs` is an in-memory dictionary, so job data is lost on restart.
- `build_graph()` wipes existing Neo4j data before writing a new graph.
- `NEO4J_PASSWORD` is required at import time for Neo4j writer/config code.
- Exception handling, security, performance, observability, and structured logging guidance lives in [Operational Hardening](operational-hardening.md).
