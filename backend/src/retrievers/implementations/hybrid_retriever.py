import logging

from src.retrievers.implementations.BM25_retriever import BM25Retriever
from src.retrievers.implementations.vectordb_retriever import SemanticSearch
from src.retrievers.implementations.rrf_fusion import rrf_fusion
from src.retrievers.implementations.code_reranker import CodeReranker
from typing import List
from src.retrievers.interfaces.vectordb_retriever import IHybridRetriever

class HybridRetriever(IHybridRetriever):

    def __init__(self):

        self.dense = SemanticSearch(top_k=20)
        self.bm25 = BM25Retriever()
        self.reranker = CodeReranker()

    def get_seed_ids( self, query: str) -> List[str]:

        dense_results = (self.dense.get_seeds(query))
        bm25_results = (self.bm25.search(query,top_k=20))
        fused = rrf_fusion([ dense_results, bm25_results])
        reranked = (self.reranker.rerank( query, fused, top_k=5))

        seen = set()

        seed_ids = []

        for item in reranked:

            node_id = item["metadata"]["node_id"]

            if node_id not in seen:
                seed_ids.append(node_id)
                seen.add(node_id)
        logging.info(f"Hybrid retrieval for query: '{query}' completed. Seed IDs retrieved: {seed_ids}")
        return seed_ids