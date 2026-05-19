# UV Project Setup Guide

## Clone the Repository

```bash
git clone <repo-url>
cd <repo-name>
```

---

## Sync Dependencies

After cloning the repository or pulling the latest changes from GitHub, run:

```bash
uv sync
```

This will:
- Create/update the virtual environment
- Install all required dependencies from `uv.lock`

---

## Installing New Packages

Whenever you want to install a new package, use:

```bash
uv add <package-name>
```

Example:

```bash
uv add chromadb
```

This automatically updates:
- `pyproject.toml`
- `uv.lock`

Commit both files after adding dependencies.