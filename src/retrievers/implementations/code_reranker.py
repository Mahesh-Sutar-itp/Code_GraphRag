from sentence_transformers import CrossEncoder

class CodeReranker:

    def __init__(self):

        self.model = CrossEncoder(
            "jinaai/jina-reranker-v2-base-multilingual"
        )

    def rerank(self, query, candidates, top_k=10):

        pairs = []

        for c in candidates:

            pairs.append((query, c["metadata"]["document"]))

        scores = self.model.predict(pairs)

        ranked = sorted(
            zip(candidates, scores),
            key=lambda x: x[1],
            reverse=True
        )

        return [item[0] for item in ranked[:top_k]]