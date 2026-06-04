# Frontend Guide

The frontend is a React + TypeScript + Vite app.

## Run Frontend

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

## Main Files

```text
frontend/src/App.tsx
frontend/src/api/client.ts
frontend/src/api/types.ts
frontend/src/components/
frontend/src/features/
frontend/src/stores/
```

## Main User Experience

When no repo is indexed, the app shows an empty state. The user can paste a GitHub URL and start indexing.

After a repo is indexed, the main screen has:

- A top bar.
- A left pane for files.
- A center chat panel.
- A right drawer for graph/code context.
- A modal for indexing another repo.

## API Client

File:

```text
frontend/src/api/client.ts
```

The frontend calls:

- `GET /repos`
- `GET /repos/{repo_id}/tree`
- `GET /repos/{repo_id}/files`
- `POST /index-repository`
- `GET /index-repository/{job_id}/status`
- `POST /resolve-query`
- `POST /subgraph`

Environment variables:

```env
VITE_INDEXER_API=http://localhost:8000
VITE_INFERENCE_API=http://localhost:8000
```

## State Management

The frontend uses Zustand.

Repo/UI state:

```text
frontend/src/stores/repo-store.ts
```

Stores:

- Selected repo ID
- Left pane open/closed
- Right drawer open/closed
- Theme

Chat state:

```text
frontend/src/stores/chat-store.ts
```

Stores:

- Messages per repo
- Active graph context
- Active code view

## Server State

The frontend uses TanStack Query for API data such as repositories and index status.

The indexing modal starts a job and then polls:

```text
GET /index-repository/{job_id}/status
```

Polling interval:

```text
700ms
```

## Graph View

File:

```text
frontend/src/features/graph/GraphView.tsx
```

The graph uses React Flow and Dagre.

It displays:

- Function nodes
- Method nodes
- Class nodes
- Directed edges returned by the backend

Clicking a graph node can open the related source code in the code viewer.

## Code Viewer

File:

```text
frontend/src/features/code-viewer/CodeViewer.tsx
```

The code viewer uses syntax highlighting and shows line numbers. It also has a copy button.

