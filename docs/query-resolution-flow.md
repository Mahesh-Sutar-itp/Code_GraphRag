# Query Resolution Flow

The query flow answers a user's natural-language question about the indexed codebase.

Main API route:

```text
POST /resolve-query
```

Main workflow files:

```text
backend/src/agent/query_resolution_workflow.py
backend/src/agent/nodes.py
backend/src/retrievers/retrieval_pipeline.py
```

## Input

The backend expects:

```json
{
  "user_id": "local-user",
  "session_id": "session-id",
  "user_query": "How does indexing work?"
}
```

## Step 1: Validate Request

The backend checks:

- `user_id`
- `session_id`
- `user_query`

If any required field is missing, the backend returns a bad request response.

## Step 2: Retrieve Candidate Context

File:

```text
backend/src/retrievers/retrieval_pipeline.py
```

The retrieval pipeline starts with the user's question and finds likely relevant code nodes.

It uses:

- ChromaDB semantic search
- BM25 keyword search
- Reciprocal rank fusion
- Code reranking

The result is a list of seed node IDs.

## Step 3: Expand Graph Context

File:

```text
backend/src/retrievers/implementations/graphdb_retriever.py
```

The retriever asks Neo4j for nodes related to the seed nodes.

It can traverse up to 2 hops through relationships such as:

- `CALLS`
- `INHERITS`
- `INSTANTIATES`
- `IMPORTS`

The current indexer mainly writes `CALLS` edges.

## Step 4: Planner Agent

File:

```text
backend/src/agent/agents.py
```

The planner receives:

- The user question
- Candidate graph nodes
- Candidate graph edges

It ranks which nodes are most useful for answering the question.

The planner does not need full source code for every node. It mainly works from metadata and graph structure.

## Step 5: Fetch Source Code

The workflow fetches full source code for the selected nodes.

This keeps the prompt smaller because source code is loaded only after ranking.

## Step 6: Resolver Agent

The resolver receives:

- User question
- Selected code nodes
- Full source code for those nodes

It writes the final answer.

## Step 7: Return Answer and Node IDs

The API response contains:

```json
{
  "status": "Success",
  "code": "200",
  "msg": "answer text",
  "node_ids": ["path/file.py::function_name"]
}
```

The frontend then calls:

```text
POST /subgraph
```

with the returned `node_ids`. This gives the frontend graph nodes and edges to display beside the answer.

## Why This Flow Helps

The system avoids sending the whole repository to the LLM.

Instead, it:

1. Searches for likely nodes.
2. Uses graph structure to add nearby context.
3. Lets a planner rank what matters.
4. Sends only selected source code to the resolver.

This makes answers more grounded and keeps prompts smaller.

