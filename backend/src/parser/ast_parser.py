"""
AST parsing — converts Python source files into structured node metadata.

Uses Tree-sitter to parse each .py file into a typed AST, then walks the tree
to extract function and class definitions along with their location and source.

Output: list of dicts representing graph nodes — feed these directly to Neo4j.
"""

from pathlib import Path
from typing import Optional

import tree_sitter_python as tspython
from tree_sitter import Language, Parser, Node
from collections import Counter

# Build the language object once — reused across all parse calls.
# Loading the grammar has nontrivial cost; doing it module-level
# means it happens once per Python process.
PY_LANGUAGE = Language(tspython.language())


def _make_parser() -> Parser:
    """Create a fresh Tree-sitter parser bound to the Python grammar."""
    parser = Parser(PY_LANGUAGE)
    return parser

def _make_node_id(file_path: str, qualified_name: str) -> str:
    """
    Build the canonical node identifier used everywhere downstream.

    Format: 'relative/path/to/file.py::function_name' or
            'relative/path/to/file.py::ClassName.method_name'

    This is the primary key in Neo4j and the document ID in ChromaDB —
    the linking mechanism of the dual-index pattern.
    """
    # Normalize path separators — Neo4j queries from Linux/Mac must match
    normalized = file_path.replace("\\", "/")
    return f"{normalized}::{qualified_name}"

def _unwrap_decorated(node: Node) -> Node:
    """
    A decorated function/class shows up as:
        decorated_definition
          ├── decorator
          └── function_definition  (or class_definition)

    Return the underlying definition node so we can treat it uniformly.
    """
    if node.type == "decorated_definition":
        for child in node.children:
            if child.type in ("function_definition", "class_definition"):
                return child
    return node

def _is_overload(node: Node) -> bool:
    """
    Check whether a node is an @overload-decorated function stub.

    Overload stubs are typing hints, not real implementations — their body
    is just `...`. We skip them during parsing so the graph indexes only the
    real implementation.

    Matches: @overload, @t.overload, @typing.overload

    Args:
        node: An AST node (we only care if it's a decorated_definition).

    Returns:
        True if the node is decorated with some form of @overload.
    """
    if node.type != "decorated_definition":
        return False

    for child in node.children:
        if child.type == "decorator":
            # decorator text looks like "@overload" or "@t.overload"
            text = child.text.decode("utf-8").lstrip("@").strip()
            # take the part after any dots: "t.overload" -> "overload"
            last_part = text.split(".")[-1]
            # handle decorators with args defensively: "overload()" -> "overload"
            last_part = last_part.split("(")[0].strip()
            if last_part == "overload":
                return True

    return False

def _get_name(node: Node) -> Optional[str]:
    """Extract the 'name' identifier from a function or class definition node."""
    name_node = node.child_by_field_name("name")
    if name_node is None:
        return None
    return name_node.text.decode("utf-8")

def _find_definitions(
    node: Node,
    source_bytes: bytes,
    file_path: str,
    class_context: Optional[str] = None,
) -> list[dict]:
    """
    Recursively walk the AST and extract all function + class definitions.

    Args:
        node: Current AST node being visited.
        source_bytes: Raw bytes of the source file (for slicing source code).
        file_path: Relative path to the file (used in node_id).
        class_context: Name of the enclosing class, if any. When we recurse
                       into a class body, we pass the class name so methods
                       get prefixed as ClassName.method_name.

    Returns:
        List of dicts, one per discovered function or class.
    """
    results: list[dict] = []

    # Skip @overload stubs — they're type hints, not real code.
    # The real implementation (undecorated, or last) is indexed normally.
    if _is_overload(node):
        return results

    # Tree-sitter wraps decorated definitions — unwrap to handle uniformly
    target = _unwrap_decorated(node)

    if target.type == "function_definition":
        name = _get_name(target)
        if name is None:
            return results

        qualified = f"{class_context}.{name}" if class_context else name
        source_code = source_bytes[target.start_byte : target.end_byte].decode(
            "utf-8", errors="replace"
        )
        docstring = _extract_docstring(target)

        results.append({
            "node_id": _make_node_id(file_path, qualified),
            "name": qualified,
            "kind": "method" if class_context else "function",
            "file_path": file_path.replace("\\", "/"),
            "start_line": target.start_point[0] + 1,
            "end_line": target.end_point[0] + 1,
            "source_code": source_code,
            "docstring": docstring or "",
        })
        return results  

    elif target.type == "class_definition":
        name = _get_name(target)
        if name is None:
            return results

        # Class itself is a node in the graph
        source_code = source_bytes[target.start_byte : target.end_byte].decode(
            "utf-8", errors="replace"
        )
        docstring = _extract_docstring(target)

        results.append({
            "node_id": _make_node_id(file_path, name),
            "name": name,
            "kind": "class",
            "file_path": file_path.replace("\\", "/"),
            "start_line": target.start_point[0] + 1,
            "end_line": target.end_point[0] + 1,
            "source_code": source_code,
            "docstring": docstring or "",
        })

        # Recurse INTO the class body to find methods.
        # Pass class name as context so methods become ClassName.method_name.
        body = target.child_by_field_name("body")
        if body is not None:
            for child in body.children:
                results.extend(
                    _find_definitions(child, source_bytes, file_path, class_context=name)
                )
        return results  # methods handled, don't double-walk children below

    # Walk children for any non-definition node (module root, etc.)
    for child in node.children:
        results.extend(
            _find_definitions(child, source_bytes, file_path, class_context=class_context)
        )

    return results

def _extract_docstring(definition_node: Node) -> Optional[str]:
    """
    Extract docstring from a function or class definition.

    A docstring is the first statement in the body, and it must be a
    string literal. Anything else (assignment, code, etc.) means no docstring.
    """
    body = definition_node.child_by_field_name("body")
    if body is None or not body.children:
        return None

    # First child of body that is a statement
    for child in body.children:
        if child.type == "expression_statement":
            # Inside expression_statement, look for a string node
            for sub in child.children:
                if sub.type == "string":
                    raw = sub.text.decode("utf-8", errors="replace")
                    # Strip surrounding quotes (could be """, ''', ", ')
                    return raw.strip("\"'").strip()
            return None  # first statement wasn't a string → no docstring
        elif child.type in ("comment",):
            continue  # comments before docstring are fine
        else:
            return None  # first real statement isn't a string

    return None

def parse_file(file_path: str | Path, repo_root: str | Path) -> list[dict]:
    """
    Parse a single Python file and return its function + class definitions.

    Args:
        file_path: Absolute path to the .py file to parse.
        repo_root: Absolute path to the repo root. Used to compute relative
                   paths so node_ids are portable across machines.

    Returns:
        List of node dicts (functions and classes). Empty list if file is
        unparseable or has no definitions.
    """
    file_path = Path(file_path).resolve()
    repo_root = Path(repo_root).resolve()

    # Compute relative path for stable node_ids
    try:
        relative = str(file_path.relative_to(repo_root))
    except ValueError:
        # File is outside repo root — use absolute path as fallback
        relative = str(file_path)

    # Tree-sitter operates on bytes — open in binary mode
    try:
        source_bytes = file_path.read_bytes()
    except (OSError, IOError) as e:
        print(f"  ! Could not read {relative}: {e}")
        return []

    parser = _make_parser()
    tree = parser.parse(source_bytes)

    # Walk the tree starting at the root
    return _find_definitions(tree.root_node, source_bytes, relative)

def parse_files(file_paths: list[Path], repo_root: str | Path) -> list[dict]:
    """
    Parse a batch of files. Errors in one file don't halt the others.

    Returns aggregated list of all nodes from all files.
    """
    all_nodes: list[dict] = []
    errors: list[tuple[Path, str]] = []

    for fp in file_paths:
        try:
            nodes = parse_file(fp, repo_root)
            all_nodes.extend(nodes)
        except Exception as e:
            errors.append((fp, str(e)))

    if errors:
        print(f"\n  ! {len(errors)} files failed to parse:")
        for fp, err in errors:
            print(f"    {fp}: {err}")

    # Disambiguate any colliding node_ids (rare: conditional definitions)
    all_nodes = _disambiguate_nodes(all_nodes)

    return all_nodes

def _find_collisions(nodes: list[dict]) -> set[str]:
    """
    Find node_ids that appear more than once in the parsed nodes.

    Collisions happen when the same name is defined multiple times in one
    file — most commonly conditional definitions:

        if WIN:
            def _get_argv_encoding(): ...   # same node_id
        else:
            def _get_argv_encoding(): ...   # same node_id  → collision

    Args:
        nodes: The full list of parsed node dicts.

    Returns:
        A set of node_ids that occur 2+ times. Empty set if all unique.
    """
    counts = Counter(n["node_id"] for n in nodes)
    return {node_id for node_id, count in counts.items() if count > 1}

def _disambiguate_nodes(nodes: list[dict]) -> list[dict]:
    """
    Make colliding node_ids unique by appending '#<start_line>'.

    Only node_ids that actually collide are modified — clean (unique) node_ids
    are left exactly as-is. This keeps the common case pristine while resolving
    genuine duplicates (e.g. platform-conditional definitions:
    `if WIN: def f() else: def f()`).

    Mutates and returns the same list.

    Example:
        _compat.py::_get_argv_encoding (line 45) -> _compat.py::_get_argv_encoding#45
        _compat.py::_get_argv_encoding (line 52) -> _compat.py::_get_argv_encoding#52
        main.py::login                            -> main.py::login  (unchanged)
    """
    collisions = _find_collisions(nodes)
    if not collisions:
        return nodes  # nothing to disambiguate — common case, fast exit

    for n in nodes:
        if n["node_id"] in collisions:
            original = n["node_id"]
            n["node_id"] = f"{original}#{n['start_line']}"
            # Observability: make the rare case loud, not silent
            print(
                f"  ⚠ Duplicate '{n['name']}' in {n['file_path']} "
                f"— disambiguated as ...#{n['start_line']}"
            )

    return nodes

def build_canonical_map(nodes: list[dict]) -> dict[str, str]:
    """
    Map each collided BASE node_id to its FIRST variant by line (C1 policy).

    After _disambiguate_nodes, collided nodes carry a '#<line>' suffix
    (e.g. 'f.py::foo#45'). But edges from the call extractor use the BASE id
    ('f.py::foo') — a call site knows the name, not the definition's line.
    This map lets us redirect those edges to one real target: the first
    variant by line order.

    '#' never appears in valid paths or identifiers, so it reliably marks a
    disambiguated node_id.

    Returns:
        { base_id: first_variant_id }, empty if there were no collisions.
    """
    from collections import defaultdict

    groups: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for n in nodes:
        nid = n["node_id"]
        if "#" in nid:
            base = nid.rsplit("#", 1)[0]
            groups[base].append((n["start_line"], nid))

    canonical: dict[str, str] = {}
    for base, variants in groups.items():
        variants.sort(key=lambda pair: pair[0])  # ascending by line
        canonical[base] = variants[0][1]          # first variant's full id

    return canonical

def redirect_edges(
    edges: list[tuple[str, str]], canonical: dict[str, str]
) -> list[tuple[str, str]]:
    """
    Redirect edge endpoints pointing to a collided base id → its first variant.

    Endpoints not in the canonical map are left unchanged (the common case).
    Self-loops accidentally created by redirection are dropped.

    Returns:
        A deduplicated list of (caller, callee) edges.
    """
    if not canonical:
        return edges  # no collisions — nothing to redirect

    redirected: list[tuple[str, str]] = []
    for caller, callee in edges:
        caller = canonical.get(caller, caller)
        callee = canonical.get(callee, callee)
        if caller != callee:  # avoid self-loops from redirect
            redirected.append((caller, callee))

    return list(set(redirected))  # dedupe

if __name__ == "__main__":
    # Smoke test: parse our test repo and show a summary
    import sys
    from src.parser.file_discovery import find_python_files

    repo = sys.argv[1] if len(sys.argv) > 1 else "test_repos/ai-engineering-journey/projects/vector-db-comparison"

    print(f"Repo: {repo}\n")
    files = find_python_files(repo)
    print(f"Found {len(files)} .py files. Parsing...\n")

    nodes = parse_files(files, repo)

    # Summary
    functions = [n for n in nodes if n["kind"] == "function"]
    methods = [n for n in nodes if n["kind"] == "method"]
    classes = [n for n in nodes if n["kind"] == "class"]

    print(f"\nExtracted {len(nodes)} definitions total:")
    print(f"  Functions: {len(functions)}")
    print(f"  Methods:   {len(methods)}")
    print(f"  Classes:   {len(classes)}\n")

    # Show first 5 of each
    print("Sample functions:")
    for n in functions[:5]:
        print(f"  {n['node_id']}  (lines {n['start_line']}-{n['end_line']})")

    print("\nSample methods:")
    for n in methods[:5]:
        print(f"  {n['node_id']}  (lines {n['start_line']}-{n['end_line']})")

    print("\nSample classes:")
    for n in classes[:5]:
        print(f"  {n['node_id']}  (lines {n['start_line']}-{n['end_line']})")