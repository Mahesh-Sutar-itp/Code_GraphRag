"""
Typed domain exceptions for CodeGraph-RAG API and indexing layers.

Each exception maps to a stable error code that can be handled consistently
across the API, logs, and frontend.
"""


class CodeGraphException(Exception):
    """Base exception for all CodeGraph-RAG domain errors."""
    
    error_code: str = "INTERNAL_ERROR"
    http_status_code: int = 500
    safe_message: str = "An internal error occurred."
    
    def __init__(self, message: str = None, details: dict = None):
        self.message = message or self.safe_message
        self.details = details or {}
        super().__init__(self.message)


class RepoValidationError(CodeGraphException):
    """Repository URL or path validation failed."""
    
    error_code = "INVALID_REPO_URL"
    http_status_code = 400
    safe_message = "Repository URL must be a public GitHub HTTPS URL (https://github.com/owner/repo)."


class RepoCloneError(CodeGraphException):
    """Failed to clone or resolve the repository."""
    
    error_code = "GIT_CLONE_FAILED"
    http_status_code = 500
    safe_message = "Failed to clone the repository. Please check the URL and try again."


class RepoCloneTimeoutError(CodeGraphException):
    """Git clone operation timed out."""
    
    error_code = "GIT_CLONE_TIMEOUT"
    http_status_code = 500
    safe_message = "Git clone operation timed out. The repository may be very large."


class GitDependencyError(CodeGraphException):
    """Git executable not found or unavailable."""
    
    error_code = "DEPENDENCY_UNAVAILABLE"
    http_status_code = 500
    safe_message = "Git is not installed or not available. Please install Git."


class IndexingError(CodeGraphException):
    """Generic indexing pipeline error."""
    
    error_code = "INDEXING_FAILED"
    http_status_code = 500
    safe_message = "Indexing failed. Please check the logs for details."


class StorageUnavailableError(CodeGraphException):
    """Neo4j, ChromaDB, or other storage layer is unavailable."""
    
    error_code = "STORAGE_UNAVAILABLE"
    http_status_code = 503
    safe_message = "Storage backend is unavailable. Please try again later."


class RepoNotIndexedError(CodeGraphException):
    """The requested repository has not been indexed yet."""
    
    error_code = "REPO_NOT_INDEXED"
    http_status_code = 409
    safe_message = "No repository has been indexed yet. Please index a repository first."


class QueryParseError(CodeGraphException):
    """Failed to parse or resolve the user query."""
    
    error_code = "QUERY_PARSE_ERROR"
    http_status_code = 500
    safe_message = "Failed to parse your query. Please try again with a different query."


class RequestValidationError(CodeGraphException):
    """Request validation failed (size, format, or content limits)."""
    
    error_code = "INVALID_REQUEST"
    http_status_code = 400
    safe_message = "The request is invalid. Please check the request parameters."


class QueryTooLargeError(RequestValidationError):
    """Query string exceeds maximum allowed size."""
    
    error_code = "QUERY_TOO_LARGE"
    safe_message = "Query is too long. Please enter a shorter query."


class TooManyNodesError(RequestValidationError):
    """Node IDs list exceeds maximum allowed count."""
    
    error_code = "TOO_MANY_NODES"
    safe_message = "Too many nodes requested. Please request fewer nodes."


class ConcurrencyError(CodeGraphException):
    """Concurrency or locking error (e.g., another index job is running)."""
    
    error_code = "CONCURRENT_INDEX_JOB"
    http_status_code = 409
    safe_message = "Another index job is already running. Please wait for it to complete."
