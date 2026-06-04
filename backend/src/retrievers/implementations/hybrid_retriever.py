import logging
import re
import os
from src.retrievers.implementations.BM25_retriever import BM25Retriever
from src.retrievers.implementations.vectordb_retriever import SemanticSearch
from src.retrievers.implementations.rrf_fusion import rrf_fusion
from src.retrievers.implementations.code_reranker import CodeReranker
from typing import List
from src.retrievers.interfaces.vectordb_retriever import IHybridRetriever

class HybridRetriever(IHybridRetriever):

    def __init__(self):

        self.dense = SemanticSearch(top_k=60)
        self.bm25 = BM25Retriever()
        self.reranker = CodeReranker()

    def get_seed_ids( self, query: str) -> List[str]:
        final_top_k: int = 10
        rrf_pool_size: int = 60
        
        # 1. Parse for explicit file targets
        files = re.findall(r'([\w./\\-]+\.(?:py|js|ts|go|cpp|java|cs))', query)
        target_files = []
        where_filter = None
        clean_query = query

        if len(files) == 1:
            raw_path = files[0]
            target_file = os.path.basename(raw_path.replace("\\", "/"))
            target_files.append(target_file)
            
            clean_query = query.replace(raw_path, " ")
            clean_query = re.sub(r"\s+", " ", clean_query).strip()
            
            # Safeguard for extremely short remaining queries
            if len(clean_query) < 5:
                clean_query = f"contents of {target_file}"
                
            where_filter = {"file_name": target_file}
            logging.info(f"Hard file target detected. Applying filter: {where_filter}")

        # 2. Stage 1: Fetch from Dense (Vector) and Sparse (BM25)
        # NOTE: Ensure your `self.dense.get_seeds` method is updated to accept these new arguments!
        dense_results = self.dense.get_seeds(
             query=clean_query, 
             top_k= rrf_pool_size,
             where_filter=where_filter,
             original_query=query # Optional: If you implemented the fallback logic inside get_seeds
        )
        
        bm25_results = self.bm25.search(
             query=clean_query, 
             top_k=rrf_pool_size,
             where_filter=where_filter
        )

        # 3. Stage 2: Reciprocal Rank Fusion
        # Pass the target_files so RRF can apply the 2.0x multiplier to exact file matches
        fused = rrf_fusion(
             rankings=[dense_results, bm25_results], 
             target_files=target_files,
             k=60
        )

        if not fused:
             return []

        # 4. Stage 3: CrossEncoder Reranking
        # We pass the ORIGINAL query to the reranker so it sees the full file path context!
        reranked = self.reranker.rerank(
             query=query, 
             candidates=fused, 
             top_k=final_top_k
        )

        seen = set()

        seed_ids = []

        for item in reranked:

            node_id = item["metadata"]["node_id"]

            if node_id not in seen:
                seed_ids.append(node_id)
                seen.add(node_id)
        logging.info(f"Hybrid retrieval for query: '{query}' completed. Seed IDs retrieved: {seed_ids}")
        return seed_ids