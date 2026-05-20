from src.config.vectordb_config import get_collection, get_embedder
from src.retrievers.interfaces.vectordb_retriever import ISemanticSearch


class SemanticSearch(ISemanticSearch):
    def __init__(self, top_k=2):
        self.collection = get_collection()
        self.embedder = get_embedder()
        self.top_k = top_k 

    def get_seed_ids(self, query: str) -> list[str]:
        """
        Phase 1: Embeds the query and fetches deterministic IDs.
        """
        query_vector = self.embedder.encode(query, normalize_embeddings=True).tolist()
        
        results = self.collection.query(
            query_embeddings=query_vector,
            n_results=self.top_k,
            include=["metadatas"]
        )
        
        # Graceful degradation if the DB is empty
        if not results['metadatas'] or not results['metadatas'][0]:
            return []
            
        # Strictly extract the deterministic neo4j_node_id
        seed_ids = []
        for metadata in results['metadatas'][0]:
            if "neo4j_node_id" in metadata:
                seed_ids.append(metadata["neo4j_node_id"])
                
        return seed_ids