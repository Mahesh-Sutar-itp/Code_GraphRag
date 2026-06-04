import logging

def rrf_fusion( rankings, k=10):

    scores = {}

    metadata_lookup = {}

    for ranking in rankings:

        for rank, item in enumerate(ranking):

            doc_id = item["id"]

            metadata_lookup[doc_id] = item

            scores[doc_id] = (scores.get(doc_id, 0) + 1 / (k + rank + 1))

    ranked = sorted(
        scores.items(),
        key=lambda x: x[1],
        reverse=True
    )
    logging.info(f"RRF fusion completed on {len(rankings)} rankings. Total unique documents scored: {len(scores)}")
    return [metadata_lookup[doc_id] for doc_id, _ in ranked]