import chromadb
# from opentelemetry import trace

from src.agent.models import GraphNode
from src.retrievers.implementations.graphdb_retriever import RelationshipExtractor
from src.retrievers.implementations.vectordb_retriever import SemanticSearch
from src.retrievers.interfaces.graphdb_retriever import IRelationshipExtractor
from src.retrievers.interfaces.vectordb_retriever import ISemanticSearch

class RetrievalPipeline:
    def __init__(self):
        """Injects the decoupled database retrievers."""
        self.semantic_search: ISemanticSearch = SemanticSearch()
        self.relationship_extractor: IRelationshipExtractor = RelationshipExtractor()

    def execute_pipeline(self, user_query: str) -> str:
        """
        Executes the fixed retrieval sequence: Semantic -> Structural -> Assembly.
        """
        # Phase 1: Semantic Search (Chroma)
        # Extracts top deterministic IDs based on the natural language query.
        # seed_ids = self.semantic_search.get_seed_ids(user_query)
        seed_ids=["pricing.js::addTax"]
        
        # Graceful Degradation: If Chroma returns [], halt before hitting Neo4j.
        if not seed_ids:
            return "I don't have relevant code indexed for this query yet."

        # Phase 2: Tiered Graph Fetch (Neo4j)
        # Path A: Fetch the heavy raw source code (Tier 1)
        raw_code_context = self.relationship_extractor.get_raw_source_code(seed_ids)
        
        # Path B: Fetch the 1-hop architectural blast radius (Tier 2)
        structural_context = self.relationship_extractor.get_related_nodes(seed_ids)
        
        # Phase 3: Context Assembly
        return self._format_as_markdown(raw_code_context, structural_context)
    
    def retrieve_nodes(self, seed_ids: list[str]) -> str:
        """
        Retrieves the asked nodes' source code and relationship.
        """
        # Graceful Degradation: If Chroma returns [], halt before hitting Neo4j.
        if not seed_ids:
            return "I don't have relevant code indexed for this query yet."

        # Phase 2: Tiered Graph Fetch (Neo4j)
        # Path A: Fetch the heavy raw source code (Tier 1)
        raw_code_context = self.relationship_extractor.get_raw_source_code(seed_ids)
        
        # Path B: Fetch the 1-hop architectural blast radius (Tier 2)
        structural_context = self.relationship_extractor.get_related_nodes(seed_ids)
        
        # Phase 3: Context Assembly
        return self._format_as_markdown(raw_code_context, structural_context)

    def _format_as_markdown(self, raw_code: str, structural_context: str) -> str:
        """
        Compiles the raw code and dependencies into a single, clean Markdown string.
        """
        prompt_payload = (
            "Use the Target Node Source Code to understand the logic, and use the "
            "Structural Dependencies to understand the blast radius.\n\n"
            f"{raw_code}\n"
            f"{structural_context}\n"
        )
        return prompt_payload
    
    def retrieve_node(self, node_id: str) -> GraphNode:
        pass