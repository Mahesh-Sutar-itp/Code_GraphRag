# Setup Guide

This guide explains how to run the project locally.

## Requirements

- Python 3.11 or newer
- `uv` for Python dependency management
- Node.js and npm
- Git
- Neo4j
- A token for the model provider used by the backend

## Backend Setup

Go to the backend folder:

```bash
cd backend
```

Install Python dependencies:

```bash
uv sync
```

Create a `.env` file in `backend/`:

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password
GITHUB_TOKEN=your_github_models_or_azure_openai_token
```

The backend uses `GITHUB_TOKEN` when creating LiteLLM models for `openai/gpt-4o` and `openai/gpt-4.1` through `https://models.inference.ai.azure.com`.

## Neo4j Setup

Neo4j must be available at the URI in `NEO4J_URI`.

The default code expects:

```text
bolt://localhost:7687
```

Neo4j Browser is usually available at:

```text
http://localhost:7474
```

## ChromaDB Setup

ChromaDB is created on disk by the backend.

Use this setting:

```vectordb_config.py
chroma_path: str="./data/chroma_db"
```

This matters because retrieval reads from `./data/chroma_db` in `backend/src/config/vectordb_config.py`.

## Phoenix Tracing

`backend/main.py` registers tracing to:

```text
http://localhost:6006/v1/traces
```

Run Phoenix locally if you want trace visibility. If Phoenix is not running and backend startup fails in your environment, start Phoenix first or adjust the tracing setup.

## Run Backend

From `backend/`:

```bash
uv run uvicorn main:app --reload
```

Check health:

```text
GET http://localhost:8000/health
```

Expected response:

```json
{ "status": "ok" }
```

## Frontend Setup

Go to the frontend folder:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Run the frontend:

```bash
npm run dev
```

Open:

```text
http://localhost:5173
```

## Frontend API Settings

The frontend reads these environment variables:

```env
VITE_INDEXER_API=http://localhost:8000
VITE_INFERENCE_API=http://localhost:8000
```

If not set, `VITE_INDEXER_API` defaults to `http://localhost:8000` and `VITE_INFERENCE_API` defaults to `/api`.

For the real backend query endpoint, set `VITE_INFERENCE_API` to the backend URL.

