import logging
from typing import List, Dict, Any, Optional

def rrf_fusion(rankings: List[List[Dict[str, Any]]], target_files: Optional[List[str]] = None, k: int = 60):
    """
    RRF Fusion with an optional file-match multiplier.
    Note: Industry standard for 'k' in RRF is 60, rather than 10. 
    """
    scores = {}
    metadata_lookup = {}

    # 1. Calculate base RRF scores
    for ranking in rankings:
        for rank, item in enumerate(ranking):
            doc_id = item["id"]
            metadata_lookup[doc_id] = item
            
            # Base RRF calculation
            base_score = 1 / (k + rank + 1)
            scores[doc_id] = scores.get(doc_id, 0) + base_score

    # 2. Apply the exact-match semantic boost
    if target_files:
        for doc_id in scores:
            doc_file_name = metadata_lookup[doc_id]["metadata"].get("file_name")
            if doc_file_name in target_files:
                # Give a 100% boost to documents that strictly match the requested files
                scores[doc_id] *= 2.0 

    # 3. Sort final rankings
    ranked = sorted(
        scores.items(),
        key=lambda x: x[1],
        reverse=True
    )
    
    logging.info(f"RRF fusion completed on {len(rankings)} rankings. Total unique documents: {len(scores)}")
    
    # Return the enriched metadata dictionaries in their newly fused order
    return [metadata_lookup[doc_id] for doc_id, _ in ranked]