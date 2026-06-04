# from opentelemetry import trace
import logging
from src.agent.models import GraphEdge, GraphNode
from src.retrievers.implementations.graphdb_retriever import RelationshipExtractor
from src.retrievers.interfaces.graphdb_retriever import IRelationshipExtractor
from src.retrievers.implementations.hybrid_retriever import HybridRetriever

class RetrievalPipeline:
    def __init__(self):
        """Injects the decoupled database retrievers."""
        self.relationship_extractor: IRelationshipExtractor = RelationshipExtractor()
        self.hybrid_retriever: HybridRetriever = HybridRetriever()

    def retrieve_structure(self, user_query: str) -> tuple[list[GraphNode], list[GraphEdge]]:
        """
        Executes the fixed retrieval sequence: Semantic -> Structural -> Assembly.
        """
        # Phase 1: Semantic Search (Chroma)
        # Extracts top deterministic IDs based on the natural language query.
        seed_ids = self.hybrid_retriever.get_seed_ids(user_query)
        # seed_ids=["pricing.js::addTax"]
        
        # Graceful Degradation: If Chroma returns [], halt before hitting Neo4j.
        if not seed_ids:
            return ([],[])

        # Phase 2: Tiered Graph Fetch (Neo4j)
        # Fetch the related nodes and edges for the seed IDs.
        graph_nodes, graph_edges, seeds = self.relationship_extractor.get_related_nodes(seed_ids, num_hops=1)
        logging.info(f"Graph structure retrieval for query: '{user_query}' completed. Nodes retrieved: {len(graph_nodes)}, Edges retrieved: {len(graph_edges)}")
        return graph_nodes, graph_edges
        
    
    def retrieve_node(self, seed_id: str) -> GraphNode | None:
        """
        Retrieves the asked nodes' source code and relationship.
        """
        # Graceful Degradation: If Chroma returns [], halt before hitting Neo4j.
        if not seed_id:
            return None

        # Phase 2: Tiered Graph Fetch (Neo4j)
        # Path A: get the raw source code for the asked nodes.
        graph_node: GraphNode | None = self.relationship_extractor.get_node_data(seed_id)
        logging.info(f"Graph structure retrieval for node: '{seed_id}' completed. Node retrieved: {graph_node is not None}")
        return graph_node