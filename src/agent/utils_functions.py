import json
import logging
from typing import Any

from google.genai.types import Content
from pydantic import ValidationError

from src.agent.models import GraphEdge, GraphNode, PlannerInput, PlannerOutput, RankedNode, ResolverInput
from src.retrievers.retrieval_pipeline import RetrievalPipeline

def extract_text_from_content(content: Content) -> str:
    """
    Extract user query text from google.genai.types.Content.

    Handles normal ADK Content structure:
    Content(parts=[Part(text="...")])
    """

    if not content or not content.parts:
        return ""

    text_parts: list[str] = []

    for part in content.parts:
        text = getattr(part, "text", None)
        if text:
            text_parts.append(text)

    return "\n".join(text_parts).strip()


def parse_planner_input_or_raise(context: Any) -> PlannerInput:
    """
    Parse and validate Query Context as Planner Input which contains list of nodes and edges.
    Raises ValueError if invalid.
    """

    if isinstance(context, PlannerInput):
        return context
    
    planner_llm_input=context
    if isinstance(context, str):
        planner_llm_input = context.strip()

        if not planner_llm_input:
            raise ValueError("Planner LLM input is empty.")

        try:
            planner_llm_input = json.loads(planner_llm_input)
        except json.JSONDecodeError as exc:
            logging.exception("Planner LLM input is not valid JSON")
            raise ValueError(f"Planner LLM input is not valid JSON: {exc}") from exc

    try:
        return PlannerInput.model_validate(planner_llm_input)
    except ValidationError as exc:
        logging.exception("Planner LLM input does not match PlannerInput schema")
        raise ValueError(f"Planner LLM Input does not match PlannerInput schema: {exc}") from exc
    
def parse_planner_output_or_raise(plan: Any) -> PlannerOutput:
    """
    Parse and validate LLM output as Planner Output which contains RankedNodes.
    Raises ValueError if invalid.
    """

    if isinstance(plan, PlannerOutput):
        return plan

    planner_llm_output=plan
    if isinstance(plan, str):
        planner_llm_output = plan.strip()

        if not planner_llm_output:
            raise ValueError("Planner LLM output is empty.")

        try:
            planner_llm_output = json.loads(planner_llm_output)
        except json.JSONDecodeError as exc:
            logging.exception("Planner LLM output is not valid JSON")
            raise ValueError(f"Planner LLM output is not valid JSON: {exc}") from exc

    try:
        return PlannerOutput.model_validate(planner_llm_output)
    except ValidationError as exc:
        logging.exception("Planner LLM output does not match PlannerOutput schema")
        raise ValueError(f"Planner LLM output does not match PlannerOutput schema: {exc}") from exc

def parse_resolver_input_or_raise(relevant_input: Any):
    """
    Parse and validate LLM output as Planner Output which contains RankedNodes.
    Raises ValueError if invalid.
    """

    if isinstance(relevant_input, ResolverInput):
        return relevant_input

    resolver_llm_input=relevant_input
    if isinstance(relevant_input, str):
        resolver_llm_input = relevant_input.strip()

        if not resolver_llm_input:
            raise ValueError("Resolver LLM input is empty.")

        try:
            resolver_llm_input = json.loads(resolver_llm_input)
        except json.JSONDecodeError as exc:
            logging.exception("Resolver LLM input is not valid JSON")
            raise ValueError(f"Resolver LLM input is not valid JSON: {exc}") from exc

    try:
        return ResolverInput.model_validate(resolver_llm_input)
    except ValidationError as exc:
        logging.exception("Resolver LLM input does not match ResolverInput schema")
        raise ValueError(f"Resolver LLM input does not match ResolverInput schema: {exc}") from exc

def estimate_tokens(text: str, chars_per_token:int = 4) -> int:
    return max(1, len(text) // chars_per_token)

def compute_final_score(node: RankedNode) -> float:
    """
    Compute deterministic final_score for a RankedNode.

    Note:
    The raw score can become negative because genericity_penalty is subtracted.
    That is okay for sorting. If you need to expose this score externally, you may
    clamp it separately, but do not clamp before sorting unless you intentionally
    want to collapse low-quality nodes.
    """
    d = node.dimensions

    return (
        0.30 * d.direct_relevance
        + 0.20 * d.structural_relevance
        + 0.15 * d.execution_path_importance
        + 0.10 * d.evidence_strength
        + 0.10 * d.source_usefulness
        + 0.06 * d.specificity
        + 0.06 * d.layer_coverage_contribution
        + 0.03 * d.confidence
        - d.genericity_penalty
    )


def sort_ranked_nodes_by_final_score(ranked_nodes: list[RankedNode]) -> list[RankedNode]:
    """
    Sort nodes in non-increasing order of computed final_score.

    Non-increasing means:
        highest score first, then lower scores.

    Tie-breaker:
        node_id ascending, for deterministic ordering.
    """
    return sorted(
        ranked_nodes,
        key=lambda node: (
            -compute_final_score(node),
            node.node_id,
        ),
    )


def sorted_node_ids_by_final_score(ranked_nodes: list[RankedNode]) -> list[str]:
    """
    Return only node_ids sorted in non-increasing order of final_score.
    """
    sorted_nodes = sort_ranked_nodes_by_final_score(ranked_nodes)
    return [node.node_id for node in sorted_nodes]


def get_relevant_nodes_for_resolver(
    user_query: str,
    planner_output: PlannerOutput,
    retrieval_pipeline: RetrievalPipeline | None,
    total_input_context_window_tokens: int,
    max_context_fraction_for_source: float = 0.50,
) -> ResolverInput:
    """
    Build ResolverInput from PlannerOutput using source-code token budgeting.

    Steps:
        1. Compute final_score for each RankedNode.
        2. Sort nodes by final_score descending.
        3. Allocate max 50% of total input context window to source code.
        4. Fetch source code using retrieval_pipeline.retrieve_source_code(node_id).
        5. Estimate source tokens using estimate_tokens(source_code).
        6. If current node would exceed budget, break immediately.
        7. If used source tokens reaches 95% of source budget, break early.
        8. Return ResolverInput with selected GraphNode objects.

    Important:
        Only source-code tokens are counted against the source budget.
        Metadata/properties, user query, static instructions, and planner output
        are not counted here.
    """

    if total_input_context_window_tokens <= 0:
        raise ValueError("total_input_context_window_tokens must be positive.")

    if not 0 < max_context_fraction_for_source <= 1:
        raise ValueError("max_context_fraction_for_source must be in range (0, 1].")

    source_token_budget = int(
        total_input_context_window_tokens * max_context_fraction_for_source
    )

    sorted_ranked_nodes = sort_ranked_nodes_by_final_score(planner_output.rankedNodes)

    selected_code_nodes: list[GraphNode] = []
    used_source_tokens = 0

    for ranked_node in sorted_ranked_nodes:

        # Uncomment below retrieval pipeline function call once setup is done and comment function returning dummy data.
        # retrieved_node: GraphNode = retrieval_pipeline.retrieve_node(ranked_node.node_id)
        retrieved_node: GraphNode = get_static_pricing_node_by_id(ranked_node.node_id)

        properties = dict(retrieved_node.properties or {})
        source_code: str = str(properties.get("source_code", None) or "")

        if not source_code:
            logging.warning(msg=f"Not Found source-code for node-id: {ranked_node.node_id}. Continuing to next node.")
            continue

        source_tokens = estimate_tokens(source_code)

        # If the current node would exceed the budget, stop immediately.
        # Do not include this node.
        if used_source_tokens + source_tokens > source_token_budget:
            break

        properties['include_reason']=ranked_node.include_reason
        selected_code_node=GraphNode(node_id=retrieved_node.node_id, properties=properties)
        selected_code_nodes.append(selected_code_node)
        used_source_tokens += source_tokens

        # Optional early stop:
        # If budget is nearly full, stop to avoid tiny remaining fragments.
        if used_source_tokens >= int(source_token_budget * 0.95):
            break

    return ResolverInput(
        user_query=user_query,
        code_nodes=selected_code_nodes,
    )


def success_response(msg: str, relevant_node_ids: list[str] = []) -> str:
    """
    Return JSON string for successful workflow completion.
    Suitable for sending as final event-stream payload.
    """
    return json.dumps({
        "status": "Success",
        "code": 200,
        "msg": msg,
        "node_ids": relevant_node_ids,
    })


def error_response(code: str, msg: str) -> str:
    """
    Return JSON string for failed workflow completion.
    Suitable for sending as final event-stream payload.
    """
    return json.dumps({
        "status": "Internal Server Error",
        "code": code,
        "msg": msg,
        "node_ids": []
    })


# Removable Temporary functions returning the data to test the agent workflow
def get_pricing_graph_data() -> tuple[list[GraphNode], list[GraphEdge]]:
    """
    Static graph data for pricing.js example.
    Includes all functions as nodes and CALLS relations as edges.
    """

    nodes = [
        GraphNode(
            node_id="pricing.js::addTax",
            properties={
                "name": "addTax",
                "kind": "function",
                "file_path": "pricing.js",
                "docstring": "Adds a fixed tax of 10 units to the given price."
            },
        ),
        GraphNode(
            node_id="pricing.js::applyDiscount",
            properties={
                "name": "applyDiscount",
                "kind": "function",
                "file_path": "pricing.js",
                "docstring": "Applies a flat discount of 5 units to the given price."
            },
        ),
        GraphNode(
            node_id="pricing.js::calculateFinalPrice",
            properties={
                "name": "calculateFinalPrice",
                "kind": "function",
                "file_path": "pricing.js",
                "docstring": "Calculates the final price by first adding tax using addTax and then applying a discount using applyDiscount.",
            },
        ),
    ]

    edges = [
        GraphEdge(
            caller_node_id="pricing.js::calculateFinalPrice",
            callee_node_id="pricing.js::addTax",
            relation_type="CALLS",
        ),
        GraphEdge(
            caller_node_id="pricing.js::calculateFinalPrice",
            callee_node_id="pricing.js::applyDiscount",
            relation_type="CALLS",
        ),
    ]

    return nodes, edges

def get_static_pricing_node_by_id(node_id: str) -> GraphNode:
    """
    Return static pricing GraphNode data by node_id.

    This simulates retrieval_pipeline.retrieve_source_code(node_id).

    Raises:
        KeyError: If node_id is not found.
    """

    nodes_by_id: dict[str, GraphNode] = {
        "pricing.js::addTax": GraphNode(
            node_id="pricing.js::addTax",
            properties={
                "name": "addTax",
                "kind": "function",
                "file_path": "pricing.js",
                "docstring": "Adds a fixed tax of 10 units to the given price.",
                "source_code": """
function addTax(price) {
    return price + 10;
}
""".strip(),
            },
        ),
        "pricing.js::applyDiscount": GraphNode(
            node_id="pricing.js::applyDiscount",
            properties={
                "name": "applyDiscount",
                "kind": "function",
                "file_path": "pricing.js",
                "docstring": "Applies a flat discount of 5 units to the given price.",
                "source_code": """
function applyDiscount(price) {
    return price - 5;
}
""".strip(),
            },
        ),
        "pricing.js::calculateFinalPrice": GraphNode(
            node_id="pricing.js::calculateFinalPrice",
            properties={
                "name": "calculateFinalPrice",
                "kind": "function",
                "file_path": "pricing.js",
                "docstring": (
                    "Calculates the final price by first adding tax using addTax "
                    "and then applying a discount using applyDiscount."
                ),
                "source_code": """
function calculateFinalPrice(price) {
    const priceWithTax = addTax(price);
    return applyDiscount(priceWithTax);
}
""".strip(),
            },
        ),
    }

    if node_id not in nodes_by_id:
        raise KeyError(f"Unknown node_id: {node_id}")

    return nodes_by_id[node_id]


def get_dummy_planner_output() -> PlannerOutput:
    """
    Return dummy PlannerOutput using updated rankedNodes data.
    """

    dummy_data = {
        "rankedNodes": [
            {
                "node_id": "pricing.js::addTax",
                "include_reason": (
                    "The query directly discusses modifying the 'addTax()' function, "
                    "making it the primary focus of the request."
                ),
                "dimensions": {
                    "direct_relevance": 1,
                    "structural_relevance": 0.9,
                    "execution_path_importance": 0.8,
                    "evidence_strength": 1,
                    "source_usefulness": 0.9,
                    "specificity": 1,
                    "layer_coverage_contribution": 0.6,
                    "confidence": 1,
                    "genericity_penalty": 0,
                },
            },
            {
                "node_id": "pricing.js::calculateFinalPrice",
                "include_reason": (
                    "The 'calculateFinalPrice' function is directly impacted by any "
                    "modifications to the 'addTax()' function, as it calls this function."
                ),
                "dimensions": {
                    "direct_relevance": 0.8,
                    "structural_relevance": 1,
                    "execution_path_importance": 0.9,
                    "evidence_strength": 0.8,
                    "source_usefulness": 0.8,
                    "specificity": 0.9,
                    "layer_coverage_contribution": 0.7,
                    "confidence": 0.9,
                    "genericity_penalty": 0,
                },
            },
            {
                "node_id": "pricing.js::applyDiscount",
                "include_reason": (
                    "Although not directly related to 'addTax()', this function is part "
                    "of the overall pricing calculation process and is interconnected "
                    "with 'calculateFinalPrice()'."
                ),
                "dimensions": {
                    "direct_relevance": 0.5,
                    "structural_relevance": 0.7,
                    "execution_path_importance": 0.5,
                    "evidence_strength": 0.6,
                    "source_usefulness": 0.5,
                    "specificity": 0.6,
                    "layer_coverage_contribution": 0.5,
                    "confidence": 0.7,
                    "genericity_penalty": 0.1,
                },
            },
        ]
    }

    return PlannerOutput.model_validate(dummy_data)
