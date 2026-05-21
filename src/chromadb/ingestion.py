import hashlib
import json
import chromadb
from typing import List, Dict, Union
from dotenv import load_dotenv
import os

load_dotenv()  # Load environment variables from .env file if present

def generate_safe_chroma_id(node_id: str) -> str:
    """
    Generates a deterministic, safe-length ID for ChromaDB (< 128 bytes).
    We use MD5 hashing to ensure the ID is always exactly 32 characters long,
    and deterministic so re-ingesting the same node updates it rather than duplicating.
    """
    return hashlib.md5(node_id.encode('utf-8')).hexdigest()

def ingest_nodes_to_chroma(
    nodes: List[Dict], 
    collection_name: str = os.getenv("CHROMA_COLLECTION_NAME", "codegraph_semantic"),
    persist_directory: str = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma_db"),
    batch_size: int = 1000
):
    """
    Ingests a list of parsed AST nodes into ChromaDB.
    
    Args:
        nodes: List of dictionaries containing node data.
        collection_name: Name of the ChromaDB collection.
        persist_directory: Local path to save the vector database.
        batch_size: Number of documents to insert at once.
    """
    print(f"Initializing ChromaDB client at {persist_directory}...")
    client = chromadb.PersistentClient(path=persist_directory)
    
    # We use the default embedding model (all-MiniLM-L6-v2) under the hood.
    collection = client.get_or_create_collection(name=collection_name,
                                                 metadata={"hnsw:space": "cosine",     # Best formula for text/code search
                                                           "hnsw:search_ef": 100       # Forces deep searching to prevent missing the top match
                                                           })
    
    total_nodes = len(nodes)
    print(f"Starting ingestion of {total_nodes} nodes into collection '{collection_name}'...")

    for i in range(0, total_nodes, batch_size):
        batch = nodes[i:i + batch_size]
        
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
        
        # Insert or update the batch in ChromaDB
        collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        print(f"Processed batch {i // batch_size + 1} ({min(i + batch_size, total_nodes)}/{total_nodes})")

    print("Ingestion complete! Full source-code semantic index is ready.")


# ==========================================
# Helper functions for flexibility
# ==========================================

def load_nodes_from_file(filepath: str) -> List[Dict]:
    """Optional helper if you decide to write nodes to a JSON intermediary file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)