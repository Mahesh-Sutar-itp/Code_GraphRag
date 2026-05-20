import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection
from sentence_transformers import SentenceTransformer

path: str="./db"
collection_name: str="codegraph"
embedding_model: str = "BAAI/bge-base-en-v1.5"

_chroma_client: ClientAPI | None = None
_collection: Collection | None = None 
_embedder: SentenceTransformer | None = None

def get_chroma_client() -> ClientAPI:
    global _chroma_client

    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path)

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