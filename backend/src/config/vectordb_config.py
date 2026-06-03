import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection
from sentence_transformers import SentenceTransformer

chroma_path: str="./data/chroma_db"
collection_name: str="codegraph_semantic"
embedding_model: str = "unsloth/embeddinggemma-300m"
bm25_path: str = "./data/bm25.pkl"

_chroma_client: ClientAPI | None = None
_collection: Collection | None = None 
_embedder: SentenceTransformer | None = None

def get_chroma_client() -> ClientAPI:
    global _chroma_client

    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=chroma_path)

    return _chroma_client

def get_collection():
    global _collection

    if _collection is None:
        chroma_client=get_chroma_client()
        _collection = chroma_client.get_collection(collection_name)

    return _collection

def get_embedder():
    global _embedder

    if _embedder is None:
        _embedder=SentenceTransformer(embedding_model)
    
    return _embedder