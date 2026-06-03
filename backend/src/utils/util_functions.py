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
