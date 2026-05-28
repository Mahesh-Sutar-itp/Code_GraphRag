"""
Neo4j writer — persists the parsed code graph into Neo4j.

Writes nodes (functions, methods, classes) and CALLS edges. Uses parameterized
Cypher and UNWIND-based batching for speed and safety.

Idempotent: wipes existing data before writing, so re-running always produces
a consistent state.
"""

import os
from dotenv import load_dotenv
from neo4j import GraphDatabase, Driver

# Fixed id for the singleton metadata node — the graph holds one repo at a time
METADATA_ID = "singleton"

# Load .env config at module import time
load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

if NEO4J_PASSWORD is None:
    raise RuntimeError(
        "NEO4J_PASSWORD not set. Make sure .env exists at project root."
    )


# ──────────────────────────────────────────────────────────────────────
# Connection management
# ──────────────────────────────────────────────────────────────────────

def get_driver() -> Driver:
    """Create a Neo4j driver. Caller is responsible for closing it."""
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

def verify_connection() -> bool:
    """Quick health check — returns True if Neo4j is reachable and accepting auth."""
    driver = get_driver()
    try:
        driver.verify_connectivity()
        return True
    except Exception as e:
        print(f"  ! Neo4j connection failed: {e}")
        return False
    finally:
        driver.close()


def read_index_metadata() -> tuple[str, str] | None:
    """
    Read the (repo_url, commit_sha) of the repo currently in the graph.

    Returns None if nothing has been indexed yet (fresh/empty graph). This is
    the signal the orchestrator uses to decide whether a repo can be skipped.

    Stored in Neo4j (not a file) so it stays consistent with the graph — if
    the graph is wiped, this metadata vanishes too, preventing false skips.
    """
    driver = get_driver()
    try:
        with driver.session() as session:
            result = session.run(
                """
                MATCH (m:IndexMetadata {id: $id})
                RETURN m.repo_url AS url, m.commit_sha AS sha
                """,
                id=METADATA_ID,
            )
            record = result.single()
            if record is None:
                return None
            return record["url"], record["sha"]
    finally:
        driver.close()

def write_index_metadata(repo_url: str, commit_sha: str) -> None:
    """
    Store the (repo_url, commit_sha) of the repo just indexed.

    Uses MERGE on a fixed singleton id, so there's always exactly one metadata
    node — create it the first time, update it on every subsequent index.

    Call this AFTER build_graph, so wipe_graph doesn't delete it.
    """
    driver = get_driver()
    try:
        with driver.session() as session:
            session.run(
                """
                MERGE (m:IndexMetadata {id: $id})
                SET m.repo_url = $url,
                    m.commit_sha = $sha,
                    m.indexed_at = datetime()
                """,
                id=METADATA_ID,
                url=repo_url,
                sha=commit_sha,
            )
    finally:
        driver.close()

# ──────────────────────────────────────────────────────────────────────
# Schema setup
# ──────────────────────────────────────────────────────────────────────

def wipe_graph(driver: Driver) -> None:
    """
    Delete every node and relationship. Used before a full re-index
    to guarantee a clean slate.

    DETACH DELETE removes the node and all its relationships in one op —
    avoids 'Cannot delete node, still has relationships' errors.
    """
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
    print("  ✓ Existing graph wiped")


def ensure_constraints(driver: Driver) -> None:
    """
    Create the uniqueness constraint on node_id.

    Doing this serves two purposes simultaneously:
      1. Prevents duplicate inserts — fail fast on bugs
      2. Creates an automatic index for fast node_id lookups (used by Chroma → Neo4j hops)
    """
    with driver.session() as session:
        session.run("""
            CREATE CONSTRAINT function_node_id IF NOT EXISTS
            FOR (f:Function) REQUIRE f.node_id IS UNIQUE
        """)
        session.run("""
            CREATE CONSTRAINT class_node_id IF NOT EXISTS
            FOR (c:Class) REQUIRE c.node_id IS UNIQUE
        """)
    print("  ✓ Uniqueness constraints in place")


# ──────────────────────────────────────────────────────────────────────
# Writes
# ──────────────────────────────────────────────────────────────────────

def write_nodes(driver: Driver, nodes: list[dict]) -> None:
    """
    Insert all nodes as :Function or :Class depending on kind.

    Functions and methods both get the :Function label — easier traversal.
    Classes get :Class. A function can be additionally tagged based on `kind`
    via a property.
    """
    # Split by intended label
    function_nodes = [n for n in nodes if n["kind"] in ("function", "method")]
    class_nodes = [n for n in nodes if n["kind"] == "class"]

    with driver.session() as session:
        if function_nodes:
            session.run(
                """
                UNWIND $nodes AS node
                CREATE (f:Function)
                SET f = node
                """,
                nodes=function_nodes,
            )
        if class_nodes:
            session.run(
                """
                UNWIND $nodes AS node
                CREATE (c:Class)
                SET c = node
                """,
                nodes=class_nodes,
            )

    print(
        f"  ✓ Inserted {len(function_nodes)} function/method nodes "
        f"+ {len(class_nodes)} class nodes"
    )


def write_edges(driver: Driver, edges: list[tuple[str, str]]) -> int:
    """
    Insert (caller, callee) tuples as :CALLS relationships.

    Uses UNWIND for batching. Only creates the relationship if BOTH endpoints
    already exist — orphan edges (where one end doesn't match any node) are
    silently dropped. This matters because our edge extractor can produce edges
    pointing to nodes we never registered (e.g. methods on imported classes
    we don't fully resolve).

    Returns the actual number of edges created.
    """
    if not edges:
        print("  ✓ No edges to insert")
        return 0

    edge_dicts = [{"caller": c, "callee": e} for c, e in edges]

    with driver.session() as session:
        result = session.run(
            """
            UNWIND $edges AS edge
            MATCH (caller {node_id: edge.caller})
            MATCH (callee {node_id: edge.callee})
            CREATE (caller)-[:CALLS]->(callee)
            RETURN count(*) AS created
            """,
            edges=edge_dicts,
        )
        created = result.single()["created"]

    dropped = len(edges) - created
    print(f"  ✓ Inserted {created} :CALLS edges ({dropped} orphan edges dropped)")
    return created


# ──────────────────────────────────────────────────────────────────────
# Sanity & inspection
# ──────────────────────────────────────────────────────────────────────

def print_summary(driver: Driver) -> None:
    """Print a quick summary of what's in the graph."""
    with driver.session() as session:
        funcs = session.run("MATCH (f:Function) RETURN count(f) AS n").single()["n"]
        classes = session.run("MATCH (c:Class) RETURN count(c) AS n").single()["n"]
        calls = session.run("MATCH ()-[r:CALLS]->() RETURN count(r) AS n").single()["n"]

    print("\n  Graph contents:")
    print(f"    :Function nodes : {funcs}")
    print(f"    :Class nodes    : {classes}")
    print(f"    :CALLS edges    : {calls}")


# ──────────────────────────────────────────────────────────────────────
# Top-level orchestration
# ──────────────────────────────────────────────────────────────────────

def build_graph(nodes: list[dict], edges: list[tuple[str, str]]) -> None:
    """
    End-to-end: wipe → constraints → nodes → edges → summary.

    This is the one function the indexer pipeline calls.
    """
    driver = get_driver()
    try:
        wipe_graph(driver)
        ensure_constraints(driver)
        write_nodes(driver, nodes)
        write_edges(driver, edges)
        print_summary(driver)
    finally:
        driver.close()


if __name__ == "__main__":
    # Quick connectivity check
    print(f"Connecting to {NEO4J_URI} as {NEO4J_USER}...")
    if verify_connection():
        print("✓ Neo4j reachable\n")
        driver = get_driver()
        try:
            print_summary(driver)
        finally:
            driver.close()
    else:
        print("✗ Could not connect. Is the Docker container running?")
        print("  Try: docker ps")