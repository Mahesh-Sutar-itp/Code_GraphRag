# ==========================================
# BM25 Search Implementation
# ==========================================
from src.chromadb.BM25_Ingest import BM25Index
from src.config.vectordb_config import bm25_path
class BM25Retriever:

    def __init__(self):

        self.index = BM25Index.load(bm25_path)

    def search(self, query, top_k=20):

        tokens = query.lower().split()

        scores = self.index.bm25.get_scores(tokens)

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
                    "score": score,
                    "metadata": doc["metadata"]
                }
            )

        return results