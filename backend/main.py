import threading
import uuid
import json
import logging
from contextvars import ContextVar
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from phoenix.otel import register

trace_provider = register(
    endpoint="http://localhost:6006/v1/traces",
    project_name="CodeGraph-RAG"
)

from openinference.instrumentation.google_adk import GoogleADKInstrumentor

GoogleADKInstrumentor().instrument(trace_provider=trace_provider)

# Structured JSON logging
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "event": getattr(record, "event", record.name),
            "message": record.getMessage(),
        }
        
        # Add request ID if available
        request_id = request_id_context.get()
        if request_id:
            log_data["request_id"] = request_id
        
        # Add extra fields if present
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)
        
        return json.dumps(log_data)

logging.basicConfig(
    filename="app.log",
    level=logging.INFO,
    format="%(message)s",
)

# Set JSON formatter
logger = logging.getLogger(__name__)
for handler in logger.handlers:
    handler.setFormatter(JSONFormatter())

# Context variable to store request ID across async contexts
request_id_context: ContextVar[str] = ContextVar("request_id", default=None)

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from src.index_repo import index_repository
from src.exceptions import (
    CodeGraphException,
    RepoValidationError,
    RepoCloneError,
    RepoCloneTimeoutError,
    GitDependencyError,
    StorageUnavailableError,
)

app=FastAPI(title="CodeGraph-RAG")

# Add request ID middleware
@app.middleware("http")
async def add_request_id_middleware(request: Request, call_next):
    """Extract or generate request ID and make it available to handlers."""
    request_id = request.headers.get("x-request-id") or f"req_{uuid.uuid4().hex[:12]}"
    request_id_context.set(request_id)
    
    response = await call_next(request)
    response.headers["x-request-id"] = request_id
    return response

# Global exception handlers
@app.exception_handler(RepoValidationError)
async def repo_validation_error_handler(request: Request, exc: RepoValidationError):
    logger.warning(
        "Repo validation error",
        extra={"extra_fields": {"error_code": exc.error_code, "request_id": request_id_context.get()}}
    )
    return JSONResponse(
        status_code=exc.http_status_code,
        content={
            "status": "error",
            "code": exc.error_code,
            "message": exc.message,
            "request_id": request_id_context.get(),
        },
    )

@app.exception_handler(CodeGraphException)
async def code_graph_exception_handler(request: Request, exc: CodeGraphException):
    logger.error(
        "Application error",
        extra={"extra_fields": {"error_code": exc.error_code, "request_id": request_id_context.get()}}
    )
    return JSONResponse(
        status_code=exc.http_status_code,
        content={
            "status": "error",
            "code": exc.error_code,
            "message": exc.message,
            "request_id": request_id_context.get(),
        },
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(
        "Unhandled exception",
        extra={"extra_fields": {
            "error_type": type(exc).__name__,
            "request_id": request_id_context.get()
        }}
    )
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "code": "INTERNAL_ERROR",
            "message": "An internal error occurred. Please try again later.",
            "request_id": request_id_context.get(),
        },
    )

# Frontend (Vite dev) runs on a different origin — allow it
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job store (resets on server restart — fine for single-repo dev)
index_jobs: dict[str, dict] = {}
_index_lock: threading.Lock = threading.Lock()

def _run_index_job(job_id: str, url: str) -> None:
    """Run indexing in a background thread with concurrency control."""
    def on_progress(stage: str, progress: int) -> None:
        index_jobs[job_id].update(status="running", stage=stage, progress=progress)

    # Set request ID context for logging
    request_id_context.set(f"job_{job_id[:8]}")
    
    # Check if another job is already running
    if not _index_lock.acquire(blocking=False):
        index_jobs[job_id].update(
            status="failed",
            error="Another index job is already running. Please wait for it to complete."
        )
        logger.warning(
            "Concurrent index job attempted",
            extra={"extra_fields": {"job_id": job_id}}
        )
        return

    try:
        index_repository(url, on_progress=on_progress)
        index_jobs[job_id].update(status="completed", stage="done", progress=100)
        logger.info(
            "Index job completed",
            extra={"extra_fields": {"job_id": job_id, "repo": url}}
        )
    except CodeGraphException as e:
        index_jobs[job_id].update(status="failed", error=e.message)
        logger.error(
            "Index job failed with domain error",
            extra={"extra_fields": {
                "job_id": job_id,
                "error_code": e.error_code,
                "repo": url
            }}
        )
    except Exception as e:
        index_jobs[job_id].update(status="failed", error=str(e))
        logger.error(
            "Index job failed",
            extra={"extra_fields": {
                "job_id": job_id,
                "error_type": type(e).__name__,
                "repo": url
            }}
        )
    finally:
        _index_lock.release()


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
    # Note: Pydantic validation now ensures non-empty values
    try:
        query_resolver=QueryResolutionWorkflow(user_id=request.user_id, session_id=request.session_id)
        response=query_resolver.resolve_query(query=request.user_query)
        
        # Log structured metadata about the resolution, NOT raw response
        logger.info(
            "Query resolved",
            extra={"extra_fields": {
                "user_id": request.user_id,
                "session_id": request.session_id,
                "request_id": request_id_context.get()
            }}
        )
        
        try:
            structured_response=parse_query_resolution_response_or_raise(response)
        except Exception as e:
            logger.error(
                "Query parse error",
                extra={"extra_fields": {
                    "error": "Invalid response format",
                    "request_id": request_id_context.get()
                }}
            )
            return QueryResolutionResponse(
                status="Internal Server Error",
                code="500",
                msg="Error while parsing response to user's query. Please try again.",
                node_ids=[]
            )
        
        return structured_response
    except Exception as e:
        logger.error(
            "Query resolution failed",
            extra={"extra_fields": {
                "error_type": type(e).__name__,
                "request_id": request_id_context.get()
            }}
        )
        return QueryResolutionResponse(
            status="Internal Server Error",
            code="500",
            msg="Failed to resolve your query. Please try again.",
            node_ids=[]
        )