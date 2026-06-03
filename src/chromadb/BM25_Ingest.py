from rank_bm25 import BM25Okapi
import pickle

class BM25Index:

    def __init__(self):
        self.bm25 = None
        self.doc_lookup = {}

    def build(self, chunked_payload):

        corpus = []

        for node in chunked_payload:

            doc_id = node["chroma_id"]

            corpus.append(
                node["document"].lower().split()
            )

            self.doc_lookup[doc_id] = node

        self.bm25 = BM25Okapi(corpus)

    def save(self, path):

        with open(path, "wb") as f:
            pickle.dump(
                {
                    "bm25": self.bm25,
                    "lookup": self.doc_lookup
                },
                f
            )

    @classmethod
    def load(cls, path):

        with open(path, "rb") as f:
            data = pickle.load(f)

        obj = cls()
        obj.bm25 = data["bm25"]
        obj.doc_lookup = data["lookup"]

        return obj

    