# API Reference

Base URL:

```text
http://localhost:8000
```

## Health

```http
GET /health
```

Response:

```json
{
  "status": "ok"
}
```

## List Indexed Repositories

```http
GET /repos
```

Response when no repo is indexed:

```json
[]
```

Response when a repo is indexed:

```json
[
  {
    "id": "owner-repo",
    "name": "owner/repo",
    "url": "https://github.com/owner/repo",
    "indexed_at": "2026-06-04T10:00:00Z",
    "total_files": 42,
    "total_lines": 12000
  }
]
```

## Get File Tree

```http
GET /repos/{repo_id}/tree
```

Response:

```json
[
  {
    "path": "src",
    "name": "src",
    "kind": "dir",
    "children": [
      {
        "path": "src/main.py",
        "name": "main.py",
        "kind": "file"
      }
    ]
  }
]
```

## Get File Content

```http
GET /repos/{repo_id}/files?path=src/main.py
```

Response:

```json
{
  "path": "src/main.py",
  "content": "print('hello')",
  "language": "python"
}
```

## Start Indexing

```http
POST /index-repository
```

Request:

```json
{
  "url": "https://github.com/pallets/click"
}
```

Response:

```json
{
  "job_id": "uuid-value",
  "status": "queued"
}
```

## Get Index Job Status

```http
GET /index-repository/{job_id}/status
```

Response:

```json
{
  "job_id": "uuid-value",
  "status": "running",
  "stage": "parsing",
  "progress": 45,
  "error": null
}
```

Possible `status` values:

- `queued`
- `running`
- `completed`
- `failed`

Possible `stage` values:

- `cloning`
- `parsing`
- `edges`
- `writing`
- `done`

## Resolve Query

```http
POST /resolve-query
```

Request:

```json
{
  "user_id": "local-user",
  "session_id": "session-id",
  "user_query": "How does repository indexing work?"
}
```

Response:

```json
{
  "status": "Success",
  "code": "200",
  "msg": "The answer text.",
  "node_ids": ["backend/src/index_repo.py::index_repository"]
}
```

## Get Subgraph

```http
POST /subgraph
```

Request:

```json
{
  "node_ids": ["backend/src/index_repo.py::index_repository"]
}
```

Response:

```json
{
  "nodes": [
    {
      "node_id": "backend/src/index_repo.py::index_repository",
      "name": "index_repository",
      "kind": "function",
      "file_path": "backend/src/index_repo.py",
      "start_line": 23,
      "end_line": 130,
      "source_code": "def index_repository(...): ..."
    }
  ],
  "edges": [
    {
      "source": "caller-node-id",
      "target": "callee-node-id"
    }
  ]
}
```

