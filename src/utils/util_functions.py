import json
import logging
from typing import Any

from pydantic import ValidationError

from src.utils.models import QueryResolutionResponse


def parse_query_resolution_response_or_raise(context: Any) -> QueryResolutionResponse:
    """
    Parse and validate Query Context as Planner Input which contains list of nodes and edges.
    Raises ValueError if invalid.
    """

    if isinstance(context, QueryResolutionResponse):
        return context
    
    workflow_response=context
    if isinstance(context, str):
        workflow_response = context.strip()

        if not workflow_response:
            raise ValueError("Workflow response to User Query is empty.")

        try:
            workflow_response = json.loads(workflow_response)
        except json.JSONDecodeError as exc:
            logging.exception("Workflow response to User Query is not valid JSON")
            raise ValueError(f"Workflow response to User Query is not valid JSON: {exc}") from exc

    try:
        return QueryResolutionResponse.model_validate(workflow_response)
    except ValidationError as exc:
        logging.exception("Workflow response to User Query does not match QueryResolutionResponse schema")
        raise ValueError(f"Workflow response to User Query does not match QueryResolutionResponse schema: {exc}") from exc
