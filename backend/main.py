import threading
import uuid
from dotenv import load_dotenv

load_dotenv()

from phoenix.otel import register

trace_provider = register(
    endpoint="http://localhost:6006/v1/traces",
    project_name="CodeGraph-RAG"
)

from openinference.instrumentation.google_adk import GoogleADKInstrumentor

GoogleADKInstrumentor().instrument(trace_provider=trace_provider)


import logging

logging.basicConfig(
    filename="app.log",
    level=logging.ERROR,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)


from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from src.index_repo import index_repository

app=FastAPI(title="CodeGraph-RAG")

# Frontend (Vite dev) runs on a different origin — allow it
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job store (resets on server restart — fine for single-repo dev)
index_jobs: dict[str, dict] = {}

def _run_index_job(job_id: str, url: str) -> None:
    def on_progress(stage: str, progress: int) -> None:
        index_jobs[job_id].update(status="running", stage=stage, progress=progress)

    try:
        index_repository(url, on_progress=on_progress)
        index_jobs[job_id].update(status="completed", stage="done", progress=100)
    except BaseException as e:
        # catches SystemExit from the indexer's sys.exit too
        index_jobs[job_id].update(status="failed", error=str(e))


from src.agent.query_resolution_workflow import QueryResolutionWorkflow
from src.utils.models import IndexRequest, QueryResolutionRequest, QueryResolutionResponse, SubgraphRequest
from src.utils.util_functions import build_file_tree, parse_query_resolution_response_or_raise
from src.indexer.neo4j_writer import (
    read_repo_info,
    read_file_paths,
    read_file_content,
    read_subgraph,
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


@app.get("/index-repository/{job_id}/status")
def index_status(job_id: str):
    """Poll the status of a background indexing job."""
    job = index_jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job



@app.post("/index-repository")
def start_index(req: IndexRequest):
    """Start indexing a repo URL in the background; returns a job id to poll."""
    job_id = str(uuid.uuid4())
    index_jobs[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "stage": "cloning",
        "progress": 0,
        "error": None,
    }
    threading.Thread(
        target=_run_index_job, args=(job_id, req.url), daemon=True
    ).start()
    return {"job_id": job_id, "status": "queued"}

@app.post("/resolve-query", response_model=QueryResolutionResponse)
def resolve_user_query(request: QueryResolutionRequest):
    if not request.user_id:
        return QueryResolutionResponse(status="Bad Request", code="400", msg="Not Found user-id", node_ids=[])
    if not request.session_id:
        return QueryResolutionResponse(status="Bad Request", code="400", msg="Not Found session-id", node_ids=[])
    if not request.user_query:
        return QueryResolutionResponse(status="Bad Request", code="400", msg="No query found. Please try again after entering question/query.", node_ids=[])

    query_resolver=QueryResolutionWorkflow(user_id=request.user_id, session_id=request.session_id)
    response=query_resolver.resolve_query(query=request.user_query)
    print(f"Raw response from QueryResolutionWorkflow: {response}")
    logging.info(f"Raw response from QueryResolutionWorkflow: {response}")
    try:
        structured_response=parse_query_resolution_response_or_raise(response)
    except Exception:
        return QueryResolutionResponse(status="Internal Server Error", code="500", msg="Error while parsing response to user's query. Please try again.", node_ids=[])
    
    return structured_response