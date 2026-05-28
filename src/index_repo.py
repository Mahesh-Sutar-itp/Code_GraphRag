"""
End-to-end indexer — scans a repo, parses it, writes the graph to Neo4j.

Usage:
    python -m src.index_repo <path_or_url>

Examples:
    python -m src.index_repo test_repos/my-project
    python -m src.index_repo https://github.com/pallets/click
"""

import sys
from pathlib import Path

from src.parser.file_discovery import find_python_files, compute_repo_stats
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


def index_repository(source: str) -> None:
    """
    Run the full pipeline: (cache check) → resolve → discover → parse →
    extract → write → record metadata.

    `source` can be a local path or a remote repo URL. For URLs, the latest
    commit SHA is checked first; if it matches the last-indexed SHA, the whole
    pipeline is skipped — no clone, no re-index.
    """
    print(f"\n{'═' * 70}")
    print(f"  Indexing: {source}")
    print(f"{'═' * 70}\n")

    # Step 0: verify Neo4j is alive before doing any work
    print("Step 0/6: Verifying Neo4j connection...")
    if not verify_connection():
        print("  ✗ Cannot reach Neo4j. Is it running?")
        sys.exit(1)
    print("  ✓ Connected\n")

    # Step 1: SHA cache check (URLs only) — skip if repo is unchanged
    print("Step 1/6: Checking for changes...")
    remote_sha = None
    if is_url(source):
        remote_sha = get_remote_sha(source)
        if remote_sha:
            last = read_index_metadata()
            if last is not None:
                last_url, last_sha = last
                if last_url == source and last_sha == remote_sha:
                    print(f"  ✓ Repo unchanged (SHA {remote_sha[:8]}) — skipping.\n")
                    print("Already indexed. Open http://localhost:7474 to explore.")
                    return
            print(f"  ✓ New/changed repo (SHA {remote_sha[:8]}) — will index.\n")
        else:
            print("  ! Could not fetch remote SHA — proceeding without cache.\n")
    else:
        print("  ✓ Local path — skipping cache check.\n")

    # Step 2: resolve the source (clone if URL, passthrough if local)
    print("Step 2/6: Resolving source...")
    try:
        repo_path, is_temp = resolve_repo_source(source)
    except (FileNotFoundError, RuntimeError) as e:
        print(f"  ✗ {e}")
        sys.exit(1)
    print(f"  ✓ Source ready at {repo_path}\n")

    try:
        # Step 3: discover .py files
        print("Step 3/6: Discovering Python files...")
        files = find_python_files(repo_path)
        print(f"  ✓ Found {len(files)} files")
        if not files:
            print("  Nothing to index.")
            return

        # Repo size metrics
        stats = compute_repo_stats(files)
        print(
            f"  ✓ {stats['total_lines']:,} total lines "
            f"({stats['code_lines']:,} code lines)\n"
        )

        # Step 4: extract definitions
        print("Step 4/6: Extracting definitions...")
        nodes = parse_files(files, repo_path)
        print(f"  ✓ Extracted {len(nodes)} definitions\n")

        # Step 5: extract call edges + C1 redirect
        print("Step 5/6: Extracting call edges...")
        edges = extract_all_edges(files, repo_path, nodes)
        canonical = build_canonical_map(nodes)
        if canonical:
            edges = redirect_edges(edges, canonical)
            print(f"  ✓ Redirected edges for {len(canonical)} disambiguated function(s)")
        print(f"  ✓ Extracted {len(edges)} edges\n")

        # Step 6: write to Neo4j
        print("Step 6/6: Writing to Neo4j...")
        build_graph(nodes, edges)

        # Record metadata so future runs can skip if unchanged (URLs only)
        if is_url(source) and remote_sha:
            write_index_metadata(source, remote_sha)
            print(f"  ✓ Recorded index metadata (SHA {remote_sha[:8]})")
        print()

        print(f"{'═' * 70}")
        print("  ✓ Indexing complete")
        print(f"{'═' * 70}\n")
        print("Open http://localhost:7474 to explore the graph.")
        print("Try this Cypher query to see everything:")
        print("    MATCH (n) RETURN n")

    finally:
        # Always clean up the temp clone, even if indexing failed
        if is_temp:
            print(f"\n  Cleaning up temporary clone...")
            _safe_rmtree(repo_path)
            print(f"  ✓ Temp directory removed")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m src.index_repo <path_or_url>")
        sys.exit(1)
    index_repository(sys.argv[1])