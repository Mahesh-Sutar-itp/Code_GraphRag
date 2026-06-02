from phoenix.otel import register

from src.agent.query_resolution_workflow import QueryResolutionWorkflow
from src.utils.models import QueryResolutionRequest, QueryResolutionResponse
from src.utils.util_functions import parse_query_resolution_response_or_raise

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


from fastapi import FastAPI

app=FastAPI(title="CodeGraph-RAG")

@app.post("/resolve_query", response_model=QueryResolutionResponse)
def resolve_user_query(request: QueryResolutionRequest):
    if not request.user_id:
        return QueryResolutionResponse(status="Bad Request", code="400", msg="Not Found user-id")
    if not request.session_id:
        return QueryResolutionResponse(status="Bad Request", code="400", msg="Not Found session-id")
    if not request.user_query:
        return QueryResolutionResponse(status="Bad Request", code="400", msg="No query found. Please try again after entering question/query.")

    query_resolver=QueryResolutionWorkflow(user_id=request.user_id, session_id=request.session_id)
    response=query_resolver.resolve_query(query=request.user_query)
    try:
        structured_response=parse_query_resolution_response_or_raise(response)
    except Exception:
        return QueryResolutionResponse(status="Internal Server Error", code="500", msg="Error while parsing response to user's query. Please try again.")
    
    return structured_response