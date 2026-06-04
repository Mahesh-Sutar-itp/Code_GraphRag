from typing import Any, Dict, List
from src.config.vectordb_config import get_collection, get_embedder
from src.retrievers.interfaces.vectordb_retriever import ISemanticSearch
import logging
# Dense vector retriever using ChromaDB
class SemanticSearch(ISemanticSearch):
    def __init__(self, top_k=20):
        self.collection = get_collection()
        self.embedder = get_embedder()
        self.top_k = top_k 

    def get_seeds(self, query: str) -> List[Dict[str, Any]]:
        """
        Phase 1: Embeds the query and fetches deterministic IDs.
        """

        query_text = f"task: code retrieval | query: {query}"
        query_vector = self.embedder.encode(query_text, normalize_embeddings=True).tolist()
        
        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=self.top_k,
            include=["metadatas",
                     "distances",
                     "documents"]
        )
        
        # Graceful degradation if the DB is empty
        if not results['metadatas'] or not results['metadatas'][0]:
            return []
        
        
        if not results["distances"] or not results["distances"][0]:
            return []
            
        output = []

        metadatas = results["metadatas"][0] if results["metadatas"] else []
        distances = results["distances"][0] if results["distances"] else []
        documents = results["documents"][0] if results["documents"] else []

        for meta, distance, doc in zip( metadatas, distances, documents):
            
            if meta is None:
                continue

            node_id = meta.get("node_id")

            if node_id is None:
                continue

            output.append(
                {
                    "id": node_id,
                    "score": 1 - distance,
                    "document": doc,
                    "metadata": meta
                }
            )
        logging.info(f"Semantic search for query: '{query}' completed. Retrieved {len(output)} candidates.")
        return output