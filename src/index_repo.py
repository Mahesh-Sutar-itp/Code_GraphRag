"""
End-to-end indexer — scans a repo, parses it, writes the graph to Neo4j.

Usage:
    python -m src.index_repo <path_to_repo>

Example:
    python -m src.index_repo test_repos/ai-engineering-journey/projects/vector-db-comparison
"""

import os
import sys
from pathlib import Path

from src.chromadb.node_chunker import chunk_ast_nodes
from src.parser.file_discovery import find_python_files
from src.parser.ast_parser import parse_files
from src.parser.call_extractor import extract_all_edges
from src.indexer.neo4j_writer import build_graph, verify_connection
from src.chromadb.ingestion import ingest_nodes_to_chroma


def index_repository(repo_path: str | Path) -> None:
    """
    Run the full pipeline: discover → parse → extract → write.
    """
    repo_path = Path(repo_path).resolve()
    if not repo_path.exists():
        raise FileNotFoundError(f"Repo not found: {repo_path}")

    print(f"\n{'═' * 70}")
    print(f"  Indexing: {repo_path}")
    print(f"{'═' * 70}\n")

    # Step 0: verify Neo4j is alive before doing any work
    print("Step 0/5: Verifying Neo4j connection...")
    if not verify_connection():
        print("  ✗ Cannot reach Neo4j. Is it running?")
        sys.exit(1)
    print("  ✓ Connected\n")

    # Step 1: discover .py files
    print("Step 1/5: Discovering Python files...")
    files = find_python_files(repo_path)
    print(f"  ✓ Found {len(files)} files\n")
    if not files:
        print("  Nothing to index.")
        return

    # Step 2: extract definitions (functions, methods, classes)
    print("Step 2/5: Extracting definitions...")
    nodes = parse_files(files, repo_path)
    print(f"  ✓ Extracted {len(nodes)} definitions\n")

    # Step 3: extract call edges
    print("Step 3/5: Extracting call edges...")
    edges = extract_all_edges(files, repo_path, nodes)
    print(f"  ✓ Extracted {len(edges)} edges\n")

    #Step 4: Ingest nodes into ChromaDB for semantic search
    print("Step 4/5: Ingesting nodes into ChromaDB for semantic search...")
    chunked_nodes = chunk_ast_nodes(nodes, max_tokens=512)
    ingest_nodes_to_chroma(chunked_nodes)
 

    # Step 5: write to Neo4j
    print("Step 5/5: Writing to Neo4j...")
    build_graph(nodes, edges)
    print("  ✓ Written to Neo4j\n")

    print(f"{'═' * 70}")
    print("  ✓ Indexing complete")
    print(f"{'═' * 70}\n")
    print("Open http://localhost:7474 to explore the graph.")
    print("Try this Cypher query to see everything:")
    print("    MATCH (n) RETURN n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m src.index_repo <path_to_repo>")
        sys.exit(1)
    index_repository(sys.argv[1])