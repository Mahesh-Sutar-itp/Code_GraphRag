"""
FastAPI server — exposes the indexer + graph over HTTP for the frontend.

Run from project root:
    uvicorn api.main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.indexer.neo4j_writer import read_repo_info

app = FastAPI(title="CodeGraph Indexer API")

# Frontend (Vite dev) runs on a different origin — allow it
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/repos")
def list_repos():
    """Return indexed repo(s). Single-repo for now → a list of zero or one."""
    info = read_repo_info()
    if info is None:
        return []
    repo_id = info["name"].replace("/", "-")
    return [
        {
            "id": repo_id,
            "name": info["name"],
            "url": info["url"],
            "indexed_at": info["indexed_at"],
            "total_files": info["total_files"],
            "total_lines": info["total_lines"],
        }
    ]