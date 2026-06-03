"""
File discovery — walks a directory tree and returns all Python source files.

Skips folders that contain derived/external content (venv, caches, git, etc.)
using in-place pruning of os.walk's subdirs list — much faster than filtering
paths after the fact because pruned folders are never visited at all.
"""

import os
from pathlib import Path


# Folders we never descend into.
# Adding here = invisible to the rest of the pipeline.
SKIP_DIRS = {
    "venv", ".venv", "env", "ENV",
    "__pycache__",
    ".git",
    "node_modules",
    ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "build", "dist",
    ".tox",
    ".idea", ".vscode",
    "site-packages",
}


def find_python_files(root_path: str | Path) -> list[Path]:
    """
    Recursively find all .py files under root_path, skipping known noise folders.

    Uses in-place mutation of subdirs (subdirs[:] = ...) so os.walk
    never descends into pruned folders.

    Args:
        root_path: Absolute or relative path to the directory to scan.

    Returns:
        A sorted list of absolute Path objects pointing to .py files.
    """
    root = Path(root_path).resolve()

    if not root.exists():
        raise FileNotFoundError(f"Path does not exist: {root}")

    if not root.is_dir():
        raise NotADirectoryError(f"Not a directory: {root}")

    collected: list[Path] = []

    for current_dir, subdirs, files in os.walk(root):
        # CRITICAL: in-place mutation — os.walk reads this list to decide
        # which subdirs to descend into next. Reassignment (subdirs = [...])
        # creates a new list os.walk never sees.
        subdirs[:] = [d for d in subdirs if d not in SKIP_DIRS]

        # Collect .py files in the current directory
        for filename in files:
            if filename.endswith(".py"):
                full_path = Path(current_dir) / filename
                collected.append(full_path.resolve())

    # Sort for deterministic ordering — same input always yields same order.
    # Makes debugging and reproducibility much easier.
    return sorted(collected)

def compute_repo_stats(file_paths: list[Path]) -> dict:
    """
    Compute simple size metrics for a set of files.

    Returns:
        {
          "total_files": number of files,
          "total_lines": total physical lines (blanks + comments + code),
          "code_lines":  non-blank lines (a rough "lines of code" measure),
        }
    """
    total_files = len(file_paths)
    total_lines = 0
    code_lines = 0

    for fp in file_paths:
        try:
            content = Path(fp).read_text(encoding="utf-8", errors="replace")
        except (OSError, IOError):
            continue  # skip unreadable files, don't crash the whole count

        lines = content.splitlines()
        total_lines += len(lines)
        code_lines += sum(1 for line in lines if line.strip())

    return {
        "total_files": total_files,
        "total_lines": total_lines,
        "code_lines": code_lines,
    }

def collect_files(file_paths: list[Path], repo_root: Path) -> list[dict]:
    """
    Read each file and return its repo-relative path, name, and full content.
    Used to persist file contents as :File nodes, so the UI can show a file
    tree and view raw file contents without keeping the cloned repo on disk.
    """
    root = Path(repo_root).resolve()
    files = []
    for fp in file_paths:
        try:
            content = Path(fp).read_text(encoding="utf-8", errors="replace")
        except (OSError, IOError):
            continue
        rel = Path(fp).resolve().relative_to(root).as_posix()
        files.append({
            "path": rel,
            "name": Path(fp).name,
            "content": content,
        })
    return files

if __name__ == "__main__":
    # Quick smoke test — run this file directly to test on the cloned repo
    import sys

    test_path = sys.argv[1] if len(sys.argv) > 1 else "test_repos"
    print(f"Scanning: {test_path}\n")

    files = find_python_files(test_path)

    print(f"Found {len(files)} Python files:\n")
    for f in files:
        # Show paths relative to the project root for readability
        try:
            rel = f.relative_to(Path.cwd())
            print(f"  {rel}")
        except ValueError:
            print(f"  {f}")