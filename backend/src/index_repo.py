"""
End-to-end indexer — scans a repo, parses it, embeds it, writes the graph to Neo4j.

Usage:
    python -m src.index_repo <path_or_url>

Examples:
    python -m src.index_repo test_repos/my-project
    python -m src.index_repo https://github.com/pallets/click
"""

import os
import sys
import logging
from pathlib import Path

from src.parser.file_discovery import find_python_files, compute_repo_stats, collect_files
from src.parser.ast_parser import parse_files, build_canonical_map, redirect_edges
from src.parser.call_extractor import extract_all_edges
from src.indexer.neo4j_writer import (
    build_graph,
    verify_connection,
    read_index_metadata,
    write_index_metadata,
)
from src.parser.repo_fetcher import (
    resolve_repo_source,
    _safe_rmtree,
    is_url,
    get_remote_sha,
)
from src.chromadb.node_chunker import chunk_ast_nodes
from src.chromadb.ingestion import ingest_nodes_to_chroma
from src.exceptions import (
    StorageUnavailableError,
    RepoCloneError,
    IndexingError,
)

logger = logging.getLogger(__name__)

def index_repository(source: str, on_progress=None) -> None:
    """
    Run the full pipeline: (cache check) → resolve → discover → parse →
    extract → embed (ChromaDB) → write (Neo4j) → record metadata.

    `source` can be a local path or a remote repo URL. For URLs, the latest
    commit SHA is checked first; if it matches the last-indexed SHA, the whole
    pipeline is skipped — no clone, no re-index.

    `on_progress(stage, progress)` is an optional callback used by the API to
    stream progress; stage is one of cloning/parsing/edges/writing/done.
    
    Raises:
        StorageUnavailableError: If Neo4j connection fails
        RepoCloneError: If repository resolution fails
        IndexingError: If any indexing step fails
    """
    def _report(stage: str, progress: int) -> None:
        if on_progress:
            on_progress(stage, progress)
    
    def _log_stage(stage_name: str, message: str = ""):
        logger.info(
            f"Indexing stage: {stage_name}",
            extra={"extra_fields": {"stage": stage_name, "message": message, "repo": source}}
        )

    # Step 0: verify Neo4j is alive before doing any work
    _log_stage("neo4j_verify", "Verifying Neo4j connection")
    if not verify_connection():
        logger.error(
            "Neo4j connection failed",
            extra={"extra_fields": {"stage": "neo4j_verify", "repo": source}}
        )
        raise StorageUnavailableError("Cannot reach Neo4j. Is it running?")

    # Step 1: SHA cache check (URLs only) — skip if repo is unchanged
    _log_stage("cache_check", "Checking for changes")
    remote_sha = None
    if is_url(source):
        remote_sha = get_remote_sha(source)
        if remote_sha:
            last = read_index_metadata()
            if last is not None:
                last_url, last_sha = last
                if last_url == source and last_sha == remote_sha:
                    logger.info(
                        "Repo unchanged, skipping index",
                        extra={"extra_fields": {"stage": "cache_check", "repo": source, "sha": remote_sha[:8]}}
                    )
                    _report("done", 100)
                    return
            logger.info(
                "New or changed repo, proceeding with index",
                extra={"extra_fields": {"stage": "cache_check", "repo": source, "sha": remote_sha[:8]}}
            )
        else:
            logger.warning(
                "Could not fetch remote SHA, proceeding without cache",
                extra={"extra_fields": {"stage": "cache_check", "repo": source}}
            )
    else:
        logger.debug("Local path — skipping cache check", extra={"extra_fields": {"repo": source}})

    # Step 2: resolve the source (clone if URL, passthrough if local)
    _log_stage("cloning", "Resolving source")
    _report("cloning", 20)
    try:
        repo_path, is_temp = resolve_repo_source(source)
    except (FileNotFoundError, RuntimeError, TimeoutError) as e:
        logger.error(
            "Repo resolution failed",
            extra={"extra_fields": {
                "stage": "cloning",
                "error": str(e),
                "error_type": type(e).__name__,
                "repo": source
            }}
        )
        raise RepoCloneError(f"Failed to clone or resolve repository: {e}") from e

    try:
        # Step 3: discover .py files
        _log_stage("discovering", "Discovering Python files")
        files = find_python_files(repo_path)
        logger.info(
            "Python files discovered",
            extra={"extra_fields": {
                "stage": "discovering",
                "file_count": len(files),
                "repo": source
            }}
        )
        if not files:
            logger.info(
                "No Python files found in repository",
                extra={"extra_fields": {"stage": "discovering", "repo": source}}
            )
            _report("done", 100)
            return

        # Repo size metrics
        stats = compute_repo_stats(files)
        logger.info(
            "Repo stats computed",
            extra={"extra_fields": {
                "stage": "discovering",
                "total_lines": stats['total_lines'],
                "code_lines": stats['code_lines'],
                "repo": source
            }}
        )

        # Step 4: extract definitions
        _log_stage("parsing", "Extracting definitions")
        _report("parsing", 45)
        nodes = parse_files(files, repo_path)
        logger.info(
            "Definitions extracted",
            extra={"extra_fields": {
                "stage": "parsing",
                "node_count": len(nodes),
                "repo": source
            }}
        )

        # Step 5: extract call edges + C1 redirect
        _log_stage("edges", "Extracting call edges")
        _report("edges", 65)
        edges = extract_all_edges(files, repo_path, nodes)
        canonical = build_canonical_map(nodes)
        if canonical:
            edges = redirect_edges(edges, canonical)
            logger.info(
                "Edges redirected for disambiguated functions",
                extra={"extra_fields": {
                    "stage": "edges",
                    "canonical_count": len(canonical),
                    "repo": source
                }}
            )
        logger.info(
            "Call edges extracted",
            extra={"extra_fields": {
                "stage": "edges",
                "edge_count": len(edges),
                "repo": source
            }}
        )

        # Step 6: ingest nodes into ChromaDB for semantic search
        _log_stage("chromadb", "Ingesting nodes into ChromaDB")
        chunked_nodes = chunk_ast_nodes(nodes, max_tokens=512)
        ingest_nodes_to_chroma(chunked_nodes)
        logger.info(
            "Nodes ingested into ChromaDB",
            extra={"extra_fields": {
                "stage": "chromadb",
                "chunk_count": len(chunked_nodes),
                "repo": source
            }}
        )

        # Step 7: write to Neo4j
        _log_stage("writing", "Writing to Neo4j")
        _report("writing", 85)
        file_contents = collect_files(files, repo_path)
        build_graph(nodes, edges, files=file_contents)
        logger.info(
            "Graph written to Neo4j",
            extra={"extra_fields": {
                "stage": "writing",
                "node_count": len(nodes),
                "edge_count": len(edges),
                "file_count": len(files),
                "repo": source
            }}
        )

        # Record metadata so future runs can skip if unchanged (URLs only)
        if is_url(source) and remote_sha:
            repo_name = source.replace("https://github.com/", "").replace(".git", "").rstrip("/")
            write_index_metadata(
                source,
                remote_sha,
                name=repo_name,
                total_files=stats["total_files"],
                total_lines=stats["total_lines"],
            )
            logger.info(
                "Index metadata recorded",
                extra={"extra_fields": {
                    "stage": "metadata",
                    "repo": source,
                    "sha": remote_sha[:8]
                }}
            )

        logger.info(
            "Indexing complete",
            extra={"extra_fields": {
                "stage": "done",
                "repo": source,
                "total_files": stats.get("total_files", 0),
                "total_lines": stats.get("total_lines", 0)
            }}
        )
        _report("done", 100)

    finally:
        # Always clean up the temp clone, even if indexing failed
        if is_temp:
            try:
                _safe_rmtree(repo_path)
                logger.debug(
                    "Temp directory cleaned up",
                    extra={"extra_fields": {"stage": "cleanup", "repo": source}}
                )
            except Exception as cleanup_err:
                logger.warning(
                    "Temp directory cleanup failed",
                    extra={"extra_fields": {
                        "stage": "cleanup",
                        "error": str(cleanup_err),
                        "repo": source
                    }}
                )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m src.index_repo <path_or_url>")
        sys.exit(1)
    index_repository(sys.argv[1])