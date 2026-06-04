import logging
from typing import Any, Dict, List, Optional
from src.retrievers.interfaces.vectordb_retriever import IBM25Retriever
from src.chromadb.BM25_Ingest import BM25Index
from src.config.vectordb_config import bm25_path


class BM25Retriever(IBM25Retriever):

    def __init__(self):
        self.index: BM25Index = BM25Index.load(bm25_path)

    def search(self, query: str, top_k: int = 60, where_filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        tokens = query.lower().split()
        bm25 = self.index.bm25

        if bm25 is None:
            logging.exception("BM25 index is not initialized.")
            raise ValueError("BM25 index is not initialized.")

        # 1. Get raw BM25 scores for the entire corpus
        scores = bm25.get_scores(tokens)
        ids = list(self.index.doc_lookup.keys())

        # 2. Pre-filter the candidate indices based on the where_filter
        valid_indices = []
        for idx, doc_id in enumerate(ids):
            if where_filter:
                doc_meta = self.index.doc_lookup[doc_id].get("metadata", {})
                
                # Check if this document matches all filter criteria
                is_match = True
                for key, val in where_filter.items():
                    if doc_meta.get(key) != val:
                        is_match = False
                        break
                
                if is_match:
                    valid_indices.append(idx)
            else:
                valid_indices.append(idx)

        # 3. Sort ONLY the filtered indices by their corresponding BM25 scores
        ranked_indices = sorted(
            valid_indices,
            key=lambda i: scores[i],
            reverse=True
        )[:top_k]

        # 4. Build output
        results = []
        for idx in ranked_indices:
            doc = self.index.doc_lookup[ids[idx]]
            results.append({
                "id": doc["metadata"]["node_id"],
                "score": float(scores[idx]),
                "document": doc.get("document", ""),
                "metadata": doc["metadata"]
            })

        return results