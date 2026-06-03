import logging
from typing import Any, Dict, List
from src.chromadb.BM25_Ingest import BM25Index
from src.config.vectordb_config import bm25_path


class BM25Retriever:

    def __init__(self):
        self.index: BM25Index = BM25Index.load(bm25_path)

    def search(self, query: str, top_k: int = 20) -> List[Dict[str, Any]]:

        tokens = query.lower().split()

        bm25 = self.index.bm25

        if bm25 is None:
            logging.exception("BM25 index is not initialized. Build/load failed while searching in BM25Retriever")
            raise ValueError("BM25 index is not initialized. Build/load failed.")

        scores = bm25.get_scores(tokens)

        ranked = sorted(
            enumerate(scores),
            key=lambda x: x[1],
            reverse=True
        )[:top_k]

        results = []

        ids = list(self.index.doc_lookup.keys())

        for idx, score in ranked:
            doc = self.index.doc_lookup[ids[idx]]

            results.append(
                {
                    "id": doc["metadata"]["node_id"],
                    "score": float(score),
                    "document": doc.get("document", ""),
                    "metadata": doc["metadata"]
                }
            )
            print(f"BM25 Candidate: {doc.get('document', '')} with score {score} and results {results}")

        return results