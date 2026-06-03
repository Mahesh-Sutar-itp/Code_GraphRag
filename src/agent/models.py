from typing import Any, List

from pydantic import BaseModel, Field

class AgentDecision(BaseModel):
    is_sufficient: bool = Field(description="True if context is enough to answer, False if more files are needed.")
    required_context_node_ids: List[str] = Field(description="List of exact node IDs needed. Maximum 3.")
    final_answer: str = Field(description="The comprehensive answer to the user's query if is_sufficient is true.")


# It must be stable enough to later retrieve the corresponding source code.
class GraphNode(BaseModel):
    node_id: str = Field(
        description=(
            "Unique identifier for the graph node. "
            "This may represent a file, symbol, function, class, module, test, config file, or other code artifact. "
        )
    )
    properties: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Structured metadata about the node excluding full source code. "
            "Examples include name, file path, docstring, node type, source code, start line, end line. "
        )
    )


class GraphEdge(BaseModel):
    caller_node_id: str = Field(
        description=(
            "Identifier of the source/origin node for this relationship. "
            "For call edges, this is typically the caller. "
            "For import/reference/dependency edges, this is the node that depends on, references, imports, or points to another node. "
        )
    )

    callee_node_id: str = Field(
        description=(
            "Identifier of the target/destination node for this relationship. "
            "For call edges, this is typically the callee. "
            "For import/reference/dependency edges, this is the node being depended on, referenced, imported, or pointed to. "
        )
    )

    relation_type: str = Field(
        description=(
            "Type of relationship between the two nodes. Examples: CALLS, IMPORTS, DEFINES, REFERENCES, IMPLEMENTS, EXTENDS, TESTS, CONFIGURES, DEPENDS_ON, CO_CHANGED, STACK_TRACE_FRAME, or RELATED. "
            "The planner should use this to estimate structural relevance and execution-path importance. "
        )
    )


class NodeRankingDimensions(BaseModel):
    direct_relevance: float = Field(
        ge=0,
        le=1,
        description=(
            "How directly the node matches the user's query text and intent. "
            "High values mean the node contains or strongly relates to mentioned identifiers, symbols, filenames, error strings, concepts, or requested behavior. "
        ),
    )

    structural_relevance: float = Field(
        ge=0,
        le=1,
        description=(
            "How relevant the node is based on graph structure. "
            "High values mean the node is close to important retrieved nodes, connected through strong relationships such as CALLS, DEFINES, TESTS, or REFERENCES, and is not merely connected through weak or generic edges. "
        ),
    )

    execution_path_importance: float = Field(
        ge=0,
        le=1,
        description=(
            "How likely the node is to participate in the runtime or business-logic path needed to answer the query. "
            "High values are appropriate for entrypoints, middleware, controllers, service methods, core domain logic, and functions directly executed during the relevant flow. "
        ),
    )

    evidence_strength: float = Field(
        ge=0,
        le=1,
        description=(
            "How many independent signals indicate this node is relevant. "
            "Signals may include semantic retrieval, lexical matches, symbol matches, stack trace mentions, test references, recent edits, graph proximity, or exact query identifier matches. "
        ),
    )

    source_usefulness: float = Field(
        ge=0,
        le=1,
        description=(
            "How useful it would be to retrieve and inspect this node's actual source code. "
            "High values mean the implementation details are likely necessary to answer, debug, modify, or explain the user's query. "
        ),
    )

    specificity: float = Field(
        ge=0,
        le=1,
        description=(
            "How specific the node is to the user's problem. "
            "High values should be given to feature-specific or query-specific code. "
            "Low values should be given to generic infrastructure, broad utility files, shared constants, index files, or highly connected hub nodes unless they are explicitly relevant. "
        ),
    )

    layer_coverage_contribution: float = Field(
        ge=0,
        le=1,
        description=(
            "How much this node adds a missing perspective or architectural layer to the selected context. "
            "High values are appropriate when the node contributes an important layer such as entrypoint, routing, middleware, service, repository, model, config, test, error handling, or type definition that is not already well represented. "
        ),
    )

    confidence: float = Field(
        ge=0,
        le=1,
        description=(
            "The planner's confidence in the assigned scores and inclusion decision for this node. "
            "High confidence means the metadata and relationships provide clear evidence that the node should be ranked highly. "
            "Low confidence means the node may be relevant but the signal is weak, ambiguous, or incomplete. "
        ),
    )

    
    genericity_penalty: float = Field(
            ge=0,
            le=1,
            description=(
                "Penalty for nodes that are too generic, overly broad, or highly connected hubs. "
                "High values should be assigned to nodes such as generic utility files, shared "
                "constants, common type files, index/barrel files, base classes, framework glue, "
                "or infrastructure code that is connected to many areas but is unlikely to be "
                "specific to the user's problem. "
                "Use 0 for highly specific nodes and higher values as the node becomes more generic or noisy."
            ),
        )



class PlannerInput(BaseModel):
    user_query: str = Field(
        description=(
            "The original user request or question that the planner must understand."
            "The planner should infer the task type, important entities, likely execution flow, and required evidence from this query."
        )
    )

    code_nodes: list[GraphNode] = Field(description="Candidate graph nodes with metadata only, excluding full source code.")

    code_edges: list[GraphEdge] = Field(
        description=(
            "Directed relationships between candidate graph nodes."
            "The planner should use these edges to reason about call flow, imports, references, tests, config connections, dependency structure, and proximity between relevant nodes."
        )
    )


class RankedNode(BaseModel):
    node_id: str = Field(description="Identifier of the ranked graph node. This must match a node_id from the PlannerInput.codeNodes list so the system can retrieve its source code later.")

    include_reason: str = Field(
        description=(
            "Brief explanation of why this node should be considered for source-code retrieval."
            "The reason should mention the strongest signals, such as direct query match, important graph relationship, execution-path role, test evidence, config relevance, or layer coverage contribution."
        )
    )

    dimensions: NodeRankingDimensions = Field(description="Detailed scoring dimensions.")


class PlannerOutput(BaseModel):
    rankedNodes: list[RankedNode] = Field(description="Planner-ranked list of nodes with dimensional scores of each node.")

class ResolverInput(BaseModel):
    user_query: str = Field(
        description=(
            "The original user request or question that the planner must understand."
            "The resolver should infer the task type, important entities, likely execution flow, and required evidence from this query."
        )
    )

    code_nodes: list[GraphNode] = Field(description="Candidate graph nodes with metadata including full source code.")