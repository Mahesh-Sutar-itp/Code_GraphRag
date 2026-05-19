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

    return all_nodes


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