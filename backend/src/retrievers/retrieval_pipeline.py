import chromadb
# from opentelemetry import trace

from src.agent.models import GraphEdge, GraphNode
from src.retrievers.implementations.graphdb_retriever import RelationshipExtractor
from src.retrievers.implementations.vectordb_retriever import SemanticSearch
from src.retrievers.interfaces.graphdb_retriever import IRelationshipExtractor
from src.retrievers.interfaces.vectordb_retriever import ISemanticSearch
from src.retrievers.implementations.vectordb_retriever import HybridRetriever

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
        
        return graph_node