import logging

from src.retrievers.interfaces.vectordb_retriever import ICodeReranker
from sentence_transformers import CrossEncoder
from typing import List

class CodeReranker(ICodeReranker):

    def __init__(self):

        self.model = CrossEncoder(
            "Alibaba-NLP/gte-reranker-modernbert-base",
            trust_remote_code=True
        )

    def rerank(self, query, candidates, top_k=10) -> List[dict]:

        pairs = []

        for c in candidates:

            pairs.append((query, c.get("document") or ""))

        scores = self.model.predict(pairs)

        ranked = sorted(
            zip(candidates, scores),
            key=lambda x: x[1],
            reverse=True
        )
        logging.info(f"Reranking of candidates based on relevance to query: '{query}' done")
        return [item[0] for item in ranked[:top_k]]