# Troubleshooting

This page lists common problems and simple fixes.

## Backend Fails Because Neo4j Password Is Missing

Error may look like:

```text
NEO4J_PASSWORD not set
```

Fix:

Create `backend/.env` and set:

```env
NEO4J_PASSWORD=your_neo4j_password
```

Also check:

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
```

## Backend Cannot Connect to Neo4j

Check that Neo4j is running.

Check browser:

```text
http://localhost:7474
```

Check bolt URI:

```text
bolt://localhost:7687
```

Make sure the password in `.env` matches the Neo4j password.

## Frontend Cannot Call Backend

The backend CORS config allows:

```text
http://localhost:5173
```

Make sure the frontend is running on that URL.

Set frontend environment variables if needed:

```env
VITE_INDEXER_API=http://localhost:8000
VITE_INFERENCE_API=http://localhost:8000
```

## Query Endpoint Calls `/api` Instead of Backend

In `frontend/src/api/client.ts`, inference defaults to:

```text
/api
```

For local real backend usage, set:

```env
VITE_INFERENCE_API=http://localhost:8000
```

Then restart the frontend dev server.

## Indexing Works but Query Returns No Useful Context

Most likely ChromaDB ingestion and retrieval are using different folders.

Use this in `backend/.env`:

```env
CHROMA_PERSIST_DIR=./data/chroma_db
CHROMA_COLLECTION_NAME=codegraph_semantic
```

Then re-index the repository.

## Index Job Disappears After Backend Restart

Index jobs are stored in memory in `backend/main.py`.

If the backend restarts, job status is lost. Start indexing again from the frontend.

The indexed graph data in Neo4j is still available if indexing completed before restart.

## Re-Index Skips the Repository

For Git URLs, the indexer checks the remote commit SHA.

If the stored SHA matches the latest remote SHA, it skips indexing because the repo has not changed.

To force a full re-index, clear the graph metadata in Neo4j or index a different repo/version.

## Git Clone Fails

Check:

- Git is installed.
- The repo URL is correct.
- The repo is public or your Git credentials can access it.
- Network access is available.

The current UI flow is mainly designed for public GitHub URLs.

## Model Token Is Missing

The backend model setup uses `GITHUB_TOKEN`.

Set:

```env
GITHUB_TOKEN=your_github_models_or_azure_openai_token
```

Then restart the backend.

## Phoenix Tracing Connection Issues

`backend/main.py` registers tracing to:

```text
http://localhost:6006/v1/traces
```

If backend startup or tracing fails because Phoenix is not running, start Phoenix locally or adjust the tracing registration for your environment.

