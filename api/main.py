"""
FastAPI server — exposes the indexer + graph over HTTP for the frontend.

Run from project root:
    uvicorn api.main:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.indexer.neo4j_writer import (
    read_repo_info,
    read_file_paths,
    read_file_content,
    read_subgraph,
)


class SubgraphRequest(BaseModel):
    node_ids: list[str]

app = FastAPI(title="CodeGraph Indexer API")

# Frontend (Vite dev) runs on a different origin — allow it
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def build_file_tree(paths: list[str]) -> list[dict]:
    """Build a nested FileNode tree from flat repo-relative file paths."""
    root: dict = {}

    for path in sorted(paths):
        parts = path.split("/")
        cursor = root
        for i, part in enumerate(parts):
            if part not in cursor:
                is_file = i == len(parts) - 1
                cursor[part] = {
                    "node": {
                        "path": "/".join(parts[: i + 1]),
                        "name": part,
                        "kind": "file" if is_file else "dir",
                    },
                    "children": {},
                }
            cursor = cursor[part]["children"]

    def to_list(level: dict) -> list[dict]:
        # dirs first, then files; alphabetical within each group
        keys = sorted(level.keys(), key=lambda k: (level[k]["node"]["kind"] == "file", k))
        items = []
        for key in keys:
            entry = level[key]
            node = dict(entry["node"])
            if node["kind"] == "dir":
                node["children"] = to_list(entry["children"])
            items.append(node)
        return items

    return to_list(root)


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


@app.get("/repos/{repo_id}/tree")
def get_tree(repo_id: str):
    """Return the repo's file tree (built from stored :File nodes)."""
    return build_file_tree(read_file_paths())


@app.get("/repos/{repo_id}/files")
def get_file(repo_id: str, path: str):
    """Return a single file's content by repo-relative path."""
    content = read_file_content(path)
    if content is None:
        raise HTTPException(status_code=404, detail="File not found")
    language = "python" if path.endswith(".py") else "text"
    return {"path": path, "content": content, "language": language}


@app.post("/subgraph")
def get_subgraph(req: SubgraphRequest):
    """Return full nodes + CALLS edges among the given node_ids."""
    return read_subgraph(req.node_ids)