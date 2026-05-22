import json
import hashlib
from pydoc import text
from langchain_text_splitters import RecursiveCharacterTextSplitter
from transformers import AutoTokenizer
from typing import List, Dict



def generate_safe_chroma_id(node_id: str, chunk_index: int = 0) -> str:
    """
    Generates a unique 32-char ID for EACH chunk of a node.
    """
    unique_string = f"{node_id}_chunk_{chunk_index}"
    return hashlib.md5(unique_string.encode('utf-8')).hexdigest()

def chunk_ast_nodes(nodes: List[Dict], max_tokens: int = 180) -> List[Dict]:
    """
    Processes AST nodes. If a node's source code is too large, it chunks it.
    Maintains the mapping back to the original Neo4j node_id.
    """

    tokenizer = AutoTokenizer.from_pretrained(
    "google/embeddinggemma-300m"
    )

    def token_count(text: str) -> int:
        return len(tokenizer.tokenize(text))

    splitter = RecursiveCharacterTextSplitter.from_huggingface_tokenizer(
        tokenizer,
        chunk_size=max_tokens,
        chunk_overlap=30,
        separators=["\nclass ", "\ndef ","\nasync def ", "\n\n", "\n", " ", ""]
    )
    
    chunked_payload = []
    
    for node in nodes:
        node_id = node["node_id"]
        source_code = node.get("source_code", "")
        
        # 1. Create the persistent header that goes on EVERY chunk
        header = (
            f"Type: {node.get('kind', 'unknown')}\n"
            f"Name: {node.get('name', 'unknown')}\n"
            f"Docstring: {node.get('docstring', '')}\n"
            f"Code:\n"
        )
        
        # 2. Check if the WHOLE thing fits in one chunk to save processing
        full_text = header + source_code
        if len(tokenizer.encode(full_text)) <= 180:
            # It fits! No need to split the code.
            chunk_record = {
                "chroma_id": generate_safe_chroma_id(node_id, 0),
                "document": full_text,
                "metadata": {
                    "node_id": node_id, 
                    "file_path": node.get("file_path", ""),
                    "name": node.get("name", ""),
                    "kind": node.get("kind", "unknown"),
                    "docstring": node.get("docstring", ""),
                    "is_chunked": False,
                    "chunk_index": 0
                }
            }
            chunked_payload.append(chunk_record)
            continue

        # 3. If it's too big, split ONLY the source code
        code_chunks = splitter.split_text(source_code)
        
        for i, code_chunk in enumerate(code_chunks):
            # 4. Re-attach the header to this specific piece of code
            chunk_document = header + code_chunk
            
            chunk_record = {
                "chroma_id": generate_safe_chroma_id(node_id, i),
                "document": chunk_document, # Header + Code snippet
                "metadata": {
                    "node_id": node_id, 
                    "file_path": node.get("file_path", ""),
                    "name": node.get("name", ""),
                    "kind": node.get("kind", "unknown"),
                    "docstring": node.get("docstring", ""),
                    "is_chunked": True,
                    "chunk_index": i
                }
            }
            chunked_payload.append(chunk_record)
            
    return chunked_payload