"""
FastAPI server — exposes the indexer + graph over HTTP for the frontend.

Run from project root:
    uvicorn api.main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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