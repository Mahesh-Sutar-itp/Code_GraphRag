from sentence_transformers import CrossEncoder

class CodeReranker:

    def __init__(self):

        self.model = CrossEncoder(
            "Alibaba-NLP/gte-reranker-modernbert-base",
            trust_remote_code=True
        )

    def rerank(self, query, candidates, top_k=10):

        pairs = []

        for c in candidates:

            pairs.append((query, c.get("document") or ""))

        scores = self.model.predict(pairs)

        ranked = sorted(
            zip(candidates, scores),
            key=lambda x: x[1],
            reverse=True
        )

        return [item[0] for item in ranked[:top_k]]