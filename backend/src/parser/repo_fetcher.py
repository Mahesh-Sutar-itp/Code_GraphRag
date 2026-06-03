"""
Repo fetcher — resolves a user-provided source (URL or local path) into a
local directory the rest of the pipeline can index.

For URLs, this clones the repo (shallow) into a temp directory.
For local paths, it's a passthrough.
"""

import subprocess
import tempfile
from pathlib import Path

# URL schemes we recognize. If a source string starts with any of these,
# we treat it as a remote repo to clone rather than a local path.
URL_PREFIXES = ("http://","https://","git@","git://","ssh://",)

def is_url(source: str) -> bool:
    """
    Detect whether a source string is a remote URL (vs a local filesystem path).

    Args:
        source: The user-provided string — either a URL or a local path.

    Returns:
        True if it looks like a remote repo URL, False if it's a local path.

    Examples:
        is_url("https://github.com/user/repo")  -> True
        is_url("git@github.com:user/repo.git")  -> True
        is_url("test_repos/my-project")         -> False
        is_url("C:\\dev\\codegraph-rag")        -> False
    """
    return source.startswith(URL_PREFIXES)

def _check_git_available() -> bool:
    """
    Verify that the `git` command is available on the system.

    Returns:
        True if git is installed and runnable, False otherwise.
    """
    try:
        subprocess.run(["git", "--version"],capture_output=True,check=True,)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def shallow_clone(url: str, token: str | None = None) -> Path:
    """
    Shallow-clone a remote repo into a fresh temporary directory.

    Uses --depth 1 (latest commit only) and --single-branch (default branch
    only) for the smallest, fastest possible download.

    Args:
        url: The remote repo URL (https/ssh/git).
        token: Optional auth token for private repos (used in v1.2 only for
               public repos; private-repo auth comes in a later version).

    Returns:
        Path to the temp directory containing the cloned repo.

    Raises:
        RuntimeError: If git is not installed, or the clone fails.
    """
    # Pre-flight: ensure git is available before doing anything
    if not _check_git_available():
        raise RuntimeError(
            "git is not installed or not in PATH. "
            "Install git from https://git-scm.com/downloads"
        )

    # Create a fresh temp directory — OS manages the location
    temp_dir = Path(tempfile.mkdtemp(prefix="codegraph_"))

    # Build the clone command
    clone_cmd = [
        "git", "clone",
        "--depth", "1",          # shallow — latest commit only
        "--single-branch",       # default branch only
        url,
        str(temp_dir),
    ]

    print(f"  Cloning {url} ...")

    try:
        result = subprocess.run(clone_cmd,capture_output=True,text=True,check=True,)
    except subprocess.CalledProcessError as e:
        # Clone failed — clean up the temp dir we created, then report
        _safe_rmtree(temp_dir)
        raise RuntimeError(
            f"git clone failed for {url}\n"
            f"  Exit code: {e.returncode}\n"
            f"  Error: {e.stderr.strip()}"
        ) from e

    print(f"  ✓ Cloned into temp directory")
    return temp_dir

def get_remote_sha(url: str, token: str | None = None) -> str | None:
    """
    Get the latest commit SHA of a remote repo's HEAD — without cloning.

    Uses `git ls-remote`, which queries the remote's refs in a single
    lightweight network round-trip (no file content downloaded). This lets us
    cheaply check whether a repo has changed since the last index.

    Args:
        url: The remote repo URL.
        token: Optional auth token (reserved for private repos).

    Returns:
        The 40-char HEAD commit SHA as a string, or None if the lookup fails
        (caller should fall back to a normal clone+index).
    """
    if not _check_git_available():
        return None

    try:
        result = subprocess.run(
            ["git", "ls-remote", url, "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,  # don't hang forever on a dead network
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None

    output = result.stdout.strip()
    if not output:
        return None

    # Output looks like: "5d4e3c2b...<tab>HEAD" — SHA is the first token
    sha = output.split()[0]
    return sha

def resolve_repo_source(source: str, token: str | None = None) -> tuple[Path, bool]:
    """
    Resolve a user-provided source into a local directory path.

    Handles both remote URLs (clones them) and local paths (passthrough).

    Args:
        source: A repo URL or a local filesystem path.
        token: Optional auth token (reserved for private-repo support later).

    Returns:
        A tuple (local_path, is_temporary):
          - local_path: Path to the directory containing the code.
          - is_temporary: True if we cloned to a temp dir (caller must clean up),
                          False if it's a user's local path (leave it alone).

    Raises:
        FileNotFoundError: If a local path doesn't exist.
        RuntimeError: If a URL clone fails.
    """
    if is_url(source):
        # Remote URL → clone into temp, caller cleans up
        temp_path = shallow_clone(source, token=token)
        return temp_path, True

    # Local path → validate and passthrough, no cleanup needed
    local_path = Path(source).resolve()
    if not local_path.exists():
        raise FileNotFoundError(f"Local path does not exist: {local_path}")
    return local_path, False

def _safe_rmtree(path: Path) -> None:
    """
    Delete a directory tree, ignoring errors (best-effort cleanup).

    Used both for cleaning up after successful indexing and for cleaning up
    a partial clone if cloning failed midway.
    """
    import shutil
    try:
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass  # best-effort — don't crash on cleanup failure

if __name__ == "__main__":
    import sys

    # If a URL is passed, test cloning it
    if len(sys.argv) > 1 and is_url(sys.argv[1]):
        url = sys.argv[1]
        print(f"Testing shallow_clone with: {url}\n")

        try:
            cloned_path = shallow_clone(url)
            print(f"\n  ✓ Clone succeeded")
            print(f"  Location: {cloned_path}")

            # List what got cloned
            py_files = list(cloned_path.rglob("*.py"))
            print(f"  Python files found: {len(py_files)}")
            for f in py_files[:5]:
                print(f"    {f.relative_to(cloned_path)}")
            if len(py_files) > 5:
                print(f"    ... and {len(py_files) - 5} more")

            # Clean up
            _safe_rmtree(cloned_path)
            print(f"\n  ✓ Temp directory cleaned up")

        except RuntimeError as e:
            print(f"\n  ✗ {e}")

    else:
        # Original is_url smoke test
        test_cases = [
            ("https://github.com/user/repo", True),
            ("git@github.com:user/repo.git", True),
            ("test_repos/my-project", False),
            ("C:\\dev\\codegraph-rag", False),
        ]
        print("Testing is_url():\n")
        for source, expected in test_cases:
            result = is_url(source)
            status = "✓" if result == expected else "✗ FAIL"
            print(f"  {status}  is_url({source!r}) = {result}")












