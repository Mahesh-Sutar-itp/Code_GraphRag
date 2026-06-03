"""
Call extraction — finds function calls inside each function and resolves
them to their source functions using a per-file imports table.

Each resolved call produces a graph edge: (caller_node_id, callee_node_id).
Unresolved calls (built-ins like print, external libs like requests) are
skipped in v1 — we track only in-project edges.

This is Phase B of the parsing pipeline; Phase A (extracting definitions)
lives in ast_parser.py.
"""

from pathlib import Path
from typing import Optional

import tree_sitter_python as tspython
from tree_sitter import Language, Parser, Node

from src.parser.ast_parser import _make_node_id


PY_LANGUAGE = Language(tspython.language())


def _make_parser() -> Parser:
    return Parser(PY_LANGUAGE)


# ──────────────────────────────────────────────────────────────────────
# Phase A — Build imports table for a file
# ──────────────────────────────────────────────────────────────────────

def _module_to_path(module_dotted: str) -> str:
    """
    Convert 'stores.base_store' → 'stores/base_store.py'

    This is a heuristic — real Python imports may resolve via __init__.py,
    namespace packages, or installed site-packages. For our v1 we assume
    flat module-to-file mapping inside the repo.
    """
    return module_dotted.replace(".", "/") + ".py"


def _resolve_relative_import(
    current_file_relative: str, dots: int, module_part: str
) -> Optional[str]:
    """
    Resolve a relative import like `from .base_store import X` or
    `from ..utils import Y` given the importing file's path.

    Args:
        current_file_relative: 'stores/chroma_store.py'
        dots: number of leading dots in `from .` (1 = current dir, 2 = parent)
        module_part: the rest after dots, e.g. 'base_store' or '' (just dots)

    Returns:
        Resolved file path like 'stores/base_store.py', or None if can't resolve.
    """
    current = Path(current_file_relative)
    # Number of directory levels to go up:
    #   1 dot  = stay in current dir (use parent)
    #   2 dots = go up one level (use grandparent)
    #   etc.
    target_dir = current.parent
    for _ in range(dots - 1):
        if target_dir.parent == target_dir:  # at filesystem root, can't go further
            return None
        target_dir = target_dir.parent

    if module_part:
        # `from .b.c import x` → target_dir / b / c .py
        target_file = target_dir / module_part.replace(".", "/")
    else:
        # `from . import x` — package-level, ambiguous in v1
        return None

    return str(target_file.with_suffix(".py")).replace("\\", "/")


def _extract_imports_table(
    tree_root: Node, current_file_relative: str
) -> dict[str, str]:
    """
    Walk the AST and build a dict: local_name → fully_qualified_node_id_prefix.

    Examples:
        from stores.base_store import BaseVectorStore
            → {"BaseVectorStore": "stores/base_store.py::BaseVectorStore"}

        from .helpers import normalize as norm
            → {"norm": "<resolved>/helpers.py::normalize"}

        import os
            → {} (no entry — external library, skipped)
    """
    imports: dict[str, str] = {}

    def walk(node: Node):
        if node.type == "import_from_statement":
            _handle_import_from(node, imports, current_file_relative)
        # `import x` and `import x as y` — these point to whole modules,
        # not specific names. We skip them in v1 because mapping
        # `os.path.join` to a file is brittle and rarely useful for
        # in-project call tracking.

        for child in node.children:
            walk(child)

    walk(tree_root)
    return imports


def _handle_import_from(
    node: Node, imports: dict[str, str], current_file_relative: str
):
    """
    Parse one `from X import Y, Z as W` statement and add to imports dict.
    """
    # Tree-sitter exposes the module via the 'module_name' field
    module_node = node.child_by_field_name("module_name")
    if module_node is None:
        return

    module_text = module_node.text.decode("utf-8")

    # Detect leading dots for relative imports
    dots = 0
    for ch in module_text:
        if ch == ".":
            dots += 1
        else:
            break
    module_part = module_text[dots:]  # rest after dots

    # Resolve module to a file path
    if dots == 0:
        # Absolute: from stores.base_store import X
        target_file = _module_to_path(module_text)
    else:
        # Relative: from .base import X or from ..utils import X
        resolved = _resolve_relative_import(current_file_relative, dots, module_part)
        if resolved is None:
            return  # couldn't resolve, skip
        target_file = resolved

    # Walk children to find the imported names (and any aliases)
    # Structure: from <module> import <name1> [as <alias>], <name2> ...
    for child in node.children:
        if child.type == "dotted_name" and child == module_node:
            continue  # this is the module itself, not an imported name

        if child.type == "dotted_name":
            # Plain import: from X import Y
            imported_name = child.text.decode("utf-8")
            imports[imported_name] = f"{target_file}::{imported_name}"

        elif child.type == "aliased_import":
            # Aliased: from X import Y as Z
            name_node = child.child_by_field_name("name")
            alias_node = child.child_by_field_name("alias")
            if name_node is None or alias_node is None:
                continue
            original = name_node.text.decode("utf-8")
            alias = alias_node.text.decode("utf-8")
            # Local name is the alias; target is the original
            imports[alias] = f"{target_file}::{original}"


# ──────────────────────────────────────────────────────────────────────
# Phase B — Find calls inside each function & resolve them
# ──────────────────────────────────────────────────────────────────────

def _find_calls_in_function(
    function_node: Node,
) -> list[str]:
    """
    Find all function calls inside a given function/method body.

    Returns:
        List of called names. For `func()` returns 'func'. For `obj.method()`
        returns 'method' (best-effort — we lose obj identity since we don't
        do type inference in v1).
    """
    called_names: list[str] = []

    def walk(node: Node):
        if node.type == "call":
            func_node = node.child_by_field_name("function")
            if func_node is None:
                return
            name = _extract_call_name(func_node)
            if name:
                called_names.append(name)

        for child in node.children:
            walk(child)

    body = function_node.child_by_field_name("body")
    if body is not None:
        walk(body)

    return called_names


def _extract_call_name(func_node: Node) -> Optional[str]:
    """
    Given the 'function' child of a `call` node, extract the callable's name.

    - func()           → func_node.type == 'identifier' → 'func'
    - obj.method()     → func_node.type == 'attribute', use the attribute name
    - obj.x.method()   → chained attribute, use the rightmost name
    """
    if func_node.type == "identifier":
        return func_node.text.decode("utf-8")

    if func_node.type == "attribute":
        # Rightmost attribute is the actual call target
        # tree-sitter: 'attribute' has child 'attribute' (str field for the .name part)
        attr_node = func_node.child_by_field_name("attribute")
        if attr_node is not None:
            return attr_node.text.decode("utf-8")

    return None


# ──────────────────────────────────────────────────────────────────────
# Public API — extract edges from a file
# ──────────────────────────────────────────────────────────────────────

def extract_edges(
    file_path: str | Path,
    repo_root: str | Path,
    module_level_names: set[str],
    methods_by_class: dict[str, set[str]],
    all_project_files: set[str],
) -> list[tuple[str, str]]:
    """
    Parse a single file and return all resolved (caller, callee) edges.

    Args:
        file_path: Absolute path to .py file.
        repo_root: Project root for computing relative paths.
        module_level_names: Top-level function names defined in THIS file.
        methods_by_class: {ClassName: {method_name, ...}} for classes in THIS file.
        all_project_files: All .py files in project (for import validation).
    """
    file_path = Path(file_path).resolve()
    repo_root = Path(repo_root).resolve()

    try:
        relative = str(file_path.relative_to(repo_root)).replace("\\", "/")
    except ValueError:
        relative = str(file_path).replace("\\", "/")

    source_bytes = file_path.read_bytes()
    parser = _make_parser()
    tree = parser.parse(source_bytes)

    imports = _extract_imports_table(tree.root_node, relative)

    # Filter imports: only keep targets in project
    imports = {
        local: target
        for local, target in imports.items()
        if target.split("::")[0] in all_project_files
    }

    edges: list[tuple[str, str]] = []

    def walk_definitions(node: Node, class_context: Optional[str] = None):
        if node.type == "decorated_definition":
            for child in node.children:
                if child.type in ("function_definition", "class_definition"):
                    walk_definitions(child, class_context)
            return

        if node.type == "function_definition":
            name_node = node.child_by_field_name("name")
            if name_node is None:
                return
            name = name_node.text.decode("utf-8")
            qualified = f"{class_context}.{name}" if class_context else name
            caller_id = _make_node_id(relative, qualified)

            calls = _find_calls_in_function(node)

            for called_name in calls:
                callee_id = _resolve_call(
                    called_name,
                    imports,
                    module_level_names,
                    methods_by_class,
                    class_context,
                    relative,
                )
                if callee_id is None:
                    continue
                if callee_id == caller_id:
                    continue  # skip self-loops
                edges.append((caller_id, callee_id))
            return

        if node.type == "class_definition":
            cls_name_node = node.child_by_field_name("name")
            cls_name = (
                cls_name_node.text.decode("utf-8") if cls_name_node else class_context
            )
            body = node.child_by_field_name("body")
            if body is not None:
                for child in body.children:
                    walk_definitions(child, class_context=cls_name)
            return

        for child in node.children:
            walk_definitions(child, class_context)

    walk_definitions(tree.root_node)
    return edges


def _resolve_call(
    called_name: str,
    imports: dict[str, str],
    module_level_names: set[str],
    methods_by_class: dict[str, set[str]],
    current_class: Optional[str],
    current_file_relative: str,
) -> Optional[str]:
    """
    Resolve a called name to a full node_id. Returns None if external/unknown.

    Resolution priority:
        1. If called from inside a class, check if it's a method on the SAME class
           (handles self.method() style calls — most common method call pattern).
        2. Check imports table (cross-file calls).
        3. Check module-level functions defined in same file.
        4. Otherwise, external/builtin/unresolvable — skip.
    """
    # Priority 1: same-class method call (the self.method() pattern)
    if current_class is not None:
        cls_methods = methods_by_class.get(current_class, set())
        if called_name in cls_methods:
            return _make_node_id(
                current_file_relative, f"{current_class}.{called_name}"
            )

    # Priority 2: imports table
    if called_name in imports:
        return imports[called_name]

    # Priority 3: module-level function in same file
    if called_name in module_level_names:
        return _make_node_id(current_file_relative, called_name)

    return None  # external — skip


# ──────────────────────────────────────────────────────────────────────
# Batch processing
# ──────────────────────────────────────────────────────────────────────

def extract_all_edges(
    file_paths: list[Path],
    repo_root: str | Path,
    nodes: list[dict],
) -> list[tuple[str, str]]:
    """
    Extract edges across all files in the repo.
    """
    repo_root = Path(repo_root).resolve()

    project_files: set[str] = set()
    for fp in file_paths:
        try:
            rel = str(Path(fp).resolve().relative_to(repo_root)).replace("\\", "/")
            project_files.add(rel)
        except ValueError:
            continue

    # Per-file maps:
    # 1. module_level_names[file] = {function_name, ...}  — top-level functions
    # 2. methods_by_class[file] = {ClassName: {method_name, ...}}  — class methods
    module_level_names: dict[str, set[str]] = {}
    methods_by_class: dict[str, dict[str, set[str]]] = {}

    for n in nodes:
        fp_key = n["file_path"]
        if n["kind"] == "function":
            module_level_names.setdefault(fp_key, set()).add(n["name"])
        elif n["kind"] == "method":
            # n["name"] is "ClassName.method_name"
            parts = n["name"].split(".", 1)
            if len(parts) == 2:
                cls_name, method_name = parts
                methods_by_class.setdefault(fp_key, {}).setdefault(cls_name, set()).add(
                    method_name
                )

    all_edges: list[tuple[str, str]] = []
    for fp in file_paths:
        try:
            rel = str(Path(fp).resolve().relative_to(repo_root)).replace("\\", "/")
        except ValueError:
            continue

        try:
            edges = extract_edges(
                fp,
                repo_root,
                module_level_names.get(rel, set()),
                methods_by_class.get(rel, {}),
                project_files,
            )
            all_edges.extend(edges)
        except Exception as e:
            print(f"  ! Edge extraction failed for {fp}: {e}")

    return list(set(all_edges))


if __name__ == "__main__":
    # Smoke test: extract edges from the test repo
    import sys
    from src.parser.file_discovery import find_python_files
    from src.parser.ast_parser import parse_files

    repo = sys.argv[1] if len(sys.argv) > 1 else "test_repos/ai-engineering-journey/projects/vector-db-comparison"

    print(f"Repo: {repo}\n")
    files = find_python_files(repo)
    print(f"Found {len(files)} .py files\n")

    print("Phase 1: extracting definitions...")
    nodes = parse_files(files, repo)
    print(f"  → {len(nodes)} nodes\n")

    print("Phase 2: extracting call edges...")
    edges = extract_all_edges(files, repo, nodes)
    print(f"  → {len(edges)} edges (deduplicated)\n")

    # Show sample edges
    print("Sample edges (first 20):")
    for caller, callee in edges[:20]:
        print(f"  {caller}")
        print(f"    → {callee}")
        print()