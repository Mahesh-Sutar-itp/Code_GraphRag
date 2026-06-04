import hashlib
import json
import chromadb
from typing import List, Dict, Union
from dotenv import load_dotenv
import os
from sentence_transformers import SentenceTransformer
from src.chromadb.BM25_Ingest import BM25Index
from src.config.vectordb_config import embedding_model, bm25_path, chroma_path, collection_name
import logging

load_dotenv()  # Load environment variables from .env file if present

embed_model: SentenceTransformer = SentenceTransformer(
    embedding_model
)

def generate_safe_chroma_id(node_id: str) -> str:
    """
    Generates a deterministic, safe-length ID for ChromaDB (< 128 bytes).
    We use MD5 hashing to ensure the ID is always exactly 32 characters long,
    and deterministic so re-ingesting the same node updates it rather than duplicating.
    """
    return hashlib.md5(node_id.encode('utf-8')).hexdigest()

def get_existing_hashes(collection, ids):
    result = collection.get(
        ids=ids,
        include=["metadatas"]
    )

    hashes = {}

    
    metadatas = result.get("metadatas") or []
    ids = result.get("ids") or []

    for idx, meta in zip(ids, metadatas):
        hashes[idx] = meta.get("content_hash") if meta else None

    return hashes

def ingest_nodes_to_chroma(
    nodes: List[Dict], 
    collection_name: str = collection_name,
    persist_directory: str = chroma_path,
    chroma_batch_size: int = 1000
):
    """
    Ingests a list of parsed AST nodes into ChromaDB.
    
    Args:
        nodes: List of dictionaries containing node data.
        collection_name: Name of the ChromaDB collection.
        persist_directory: Local path to save the vector database.
        chroma_batch_size: Number of documents to insert at once.
    """
    print(f"Initializing ChromaDB client at {persist_directory}...")
    logging.info(f"Initializing ChromaDB client at {persist_directory}...")
    client = chromadb.PersistentClient(path=persist_directory)
    
    # We use the embedding model ("google/embeddinggemma-300m") under the hood.
    collection = client.get_or_create_collection(name=collection_name,
                                                 metadata={"hnsw:space": "cosine",     # Best formula for text/code search
                                                           "hnsw:search_ef": 100       # Forces deep searching to prevent missing the top match
                                                           })
    
    total_nodes = len(nodes)
    print(f"Starting ingestion of {total_nodes} nodes into collection '{collection_name}'...")
    logging.info(f"Starting ingestion of {total_nodes} nodes into collection '{collection_name}'...")


    existing = collection.get(include=["metadatas"])

    existing_hashes = {
        idx: meta.get("content_hash")
        for idx, meta in zip(
            existing.get("ids", []),
            existing.get("metadatas") or []
        )
    }

    def bm25_ingest(nodes: List[Dict], path: str = "bm25.pkl"):
        bm25 = BM25Index()

        bm25.build(nodes)

        bm25.save(path)

    bm25_ingest(nodes, path=bm25_path)

    for i in range(0, total_nodes, chroma_batch_size):
        batch = nodes[i:i + chroma_batch_size]
        
        ids = []
        documents = []
        metadatas = []
                
        for node in batch:
            # 1. Generate the safe < 128 byte ID
            # safe_id = generate_safe_chroma_id(node["node_id"])
            safe_id = f"{node.get('chroma_id', 'unknown_id')}"
             # 2. Format the document text (this is what gets vectorized/embedded)
            # We combine kind, name, docstring and source codeto give the embedding model good context
            doc_text = ( 
                f"{node.get('document', '')}" )
            # 3. Build the metadata
            # The metadata holds the bridge back to Neo4j.
            # We omit storing 'source_code' here to save disk space, 
            # because Neo4j acts as the source of truth for the raw text.
            meta = node.get('metadata', {})
            
            ids.append(safe_id)
            documents.append(doc_text)
            metadatas.append(meta)


        filtered_ids = []
        filtered_docs = []
        filtered_meta = []

        for id_, doc, meta in zip( ids, documents, metadatas):
            existing_hash = existing_hashes.get(id_)

            if existing_hash == meta.get("content_hash"):
                continue

            filtered_ids.append(id_)
            filtered_docs.append(doc)
            filtered_meta.append(meta)

        if not filtered_docs:
            continue

        embeddings = embed_model.encode(
            filtered_docs,
            batch_size=64,
            normalize_embeddings=True,
            show_progress_bar=False,
            device='cpu'
        )

        # Insert or update the batch in ChromaDB
        collection.upsert(
            ids=filtered_ids,
            documents=filtered_docs,
            metadatas=filtered_meta,
            embeddings=embeddings.tolist()
        )
        print(f"Processed batch {i // chroma_batch_size + 1} ({min(i + chroma_batch_size, total_nodes)}/{total_nodes})")
        logging.info(f"Processed batch {i // chroma_batch_size + 1} ({min(i + chroma_batch_size, total_nodes)}/{total_nodes})")
        
    current_ids = {node.get("chroma_id", "unknown_id") for node in nodes}

    existing = collection.get(include=[])

    existing_ids = set(existing["ids"])

    stale_ids = list(
        existing_ids - current_ids
    )

    if stale_ids:
        collection.delete(ids=stale_ids)
    logging.info("Ingestion complete! Full source-code semantic index is ready.")


# ==========================================
# Helper functions for flexibility
# ==========================================

def load_nodes_from_file(filepath: str) -> List[Dict]:
    """Optional helper if you decide to write nodes to a JSON intermediary file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)