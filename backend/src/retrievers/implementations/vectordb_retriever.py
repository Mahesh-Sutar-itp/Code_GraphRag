from typing import Any, Dict, List, Optional
from src.config.vectordb_config import get_collection, get_embedder
from src.retrievers.interfaces.vectordb_retriever import ISemanticSearch
import logging
import re
import os
# Dense vector retriever using ChromaDB
class SemanticSearch(ISemanticSearch):
    def __init__(self, top_k=60):
        self.collection = get_collection()
        self.embedder = get_embedder()
        self.top_k = top_k 

    def get_seeds(
        self, 
        query: str, 
        top_k: int = 60, 
        where_filter: Optional[Dict[str, Any]] = None, 
        original_query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        
        # 1. Format for EmbeddingGemma-300m
        primary_query_text = f"task: code retrieval | query: {query}"
        primary_vector = self.embedder.encode(primary_query_text, normalize_embeddings=True).tolist()

        # 2. Build ChromaDB search parameters
        search_kwargs = {
            "query_embeddings": [primary_vector],
            "n_results": top_k,
            "include": ["metadatas", "distances", "documents"]
        }

        if where_filter:
            search_kwargs["where"] = where_filter

        # 3. Execute primary search
        results = self.collection.query(**search_kwargs)

        # 4. The Safety Fallback
        # If the user used a strict file filter but Chroma returned nothing, try again using 
        # purely semantic search with the original un-stripped query.
        if where_filter and (not results or not results.get("documents") or not results["documents"][0]):
            logging.info("Dense Retriever: Hard file filter returned 0 results. Falling back to global semantic search.")
            
            # Remove the strict filter
            del search_kwargs["where"]
            
            # Re-encode using the original query so the embedding model can "see" the file name
            fallback_text = original_query if original_query else query
            fallback_query_text = f"task: code retrieval | query: {fallback_text}"
            fallback_vector = self.embedder.encode(fallback_query_text, normalize_embeddings=True).tolist()
            
            search_kwargs["query_embeddings"] = [fallback_vector]
            results = self.collection.query(**search_kwargs)
                
        # Graceful degradation if the DB is empty
        if not results.get("metadatas") or not results["metadatas"][0]:
            return []
        
        if not results.get("distances") or not results["distances"][0]:
            return []
            
        if not results.get("documents") or not results["documents"][0]:
            return []
            
        output = []

        # 2. Safe extraction (we know they exist because of the guards above)
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]
        documents = results["documents"][0]

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