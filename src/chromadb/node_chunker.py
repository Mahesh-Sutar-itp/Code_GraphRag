import json
import hashlib
from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import List, Dict

def generate_safe_chroma_id(node_id: str, chunk_index: int = 0) -> str:
    """
    Generates a unique 32-char ID for EACH chunk of a node.
    """
    unique_string = f"{node_id}_chunk_{chunk_index}"
    return hashlib.md5(unique_string.encode('utf-8')).hexdigest()

def chunk_ast_nodes(nodes: List[Dict], max_chars: int = 1500) -> List[Dict]:
    """
    Processes AST nodes. If a node's source code is too large, it chunks it.
    Maintains the mapping back to the original Neo4j node_id.
    """
    # We use LangChain's splitter designed specifically for code/text
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=max_chars,
        chunk_overlap=200, # Crucial: overlap prevents cutting a variable name in half
        separators=["\nclass ", "\ndef ", "\n\n", "\n", " ", ""]
    )
    
    chunked_payload = []
    
    for node in nodes:
        node_id = node["node_id"]
        source_code = node.get("source_code", "")
        
        # Combine docstring and code for the full semantic context
        full_text = (
            f"Type: {node.get('kind', 'node')}\n"
            f"Name: {node.get('name', 'unknown')}\n"
            f"Docstring: {node.get('docstring', '')}\n"
            f"Code:\n{source_code}"
        )
        
        # Check if the text exceeds our maximum character limit
        if len(full_text) > max_chars:
            # Split the massive node into smaller pieces
            chunks = splitter.split_text(full_text)
            
            for i, chunk_text in enumerate(chunks):
                chunk_record = {
                    "chroma_id": generate_safe_chroma_id(node_id, i),
                    "document": chunk_text,
                    "metadata": {
                        "node_id": node_id, # The bridge back to Neo4j
                        "file_path": node["file_path"],
                        "name": node["name"],
                        "kind": node.get("kind", "node"),
                        "docstring": node.get("docstring", ""),
                        "is_chunked": True,
                        "chunk_index": i
                    }
                }
                chunked_payload.append(chunk_record)
        else:
            # Node is small enough, keep it as a single chunk
            chunk_record = {
                "chroma_id": generate_safe_chroma_id(node_id, 0),
                "document": full_text,
                "metadata": {
                    "node_id": node_id,
                    "file_path": node["file_path"],
                    "name": node["name"],
                    "kind": node.get("kind", "node"),
                    "docstring": node.get("docstring", ""),
                    "is_chunked": False,
                    "chunk_index": 0
                }
            }
            chunked_payload.append(chunk_record)
            
    return chunked_payload