# CodeGraph-RAG Frontend

This folder contains the React + TypeScript frontend for CodeGraph-RAG.

It provides:

- Repository indexing UI
- Chat interface for asking codebase questions
- File tree browser
- Graph view for relevant code context
- Source code viewer
- Light/dark theme state

Run locally:

```bash
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

For real backend query calls, set:

```env
VITE_INDEXER_API=http://localhost:8000
VITE_INFERENCE_API=http://localhost:8000
```

Read the main project documentation from the repository root:

- [Project README](../README.md)
- [Frontend Guide](../docs/frontend.md)
- [Setup Guide](../docs/setup.md)
- [API Reference](../docs/api-reference.md)
