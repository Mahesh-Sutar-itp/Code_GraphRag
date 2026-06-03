# Future Work & Deferred Features

This file tracks features that were analyzed and **consciously deferred** —
along with *why*. Deferring with documented reasoning is a deliberate
engineering decision, not an oversight.

---

## 🔮 Deferred: Incremental Indexing (was "Version 4")

**Status:** Deferred — revisit at scale.

### What it is

Currently (V3), when a repo changes (commit SHA differs), we **wipe the entire
graph and re-parse every file**. Incremental indexing would instead:

1. Detect *which files* changed since the last index.
2. Re-parse only those files.
3. Update only the affected nodes/edges in the graph (leave the rest untouched).

### Why deferred — cost/benefit at current scale

For our typical repos (tens to low-hundreds of files), the cost is dominated
by the **clone**, not the parse:

| Stage              | Time      | Notes                          |
|--------------------|-----------|--------------------------------|
| Shallow clone      | ~30–60s   | **Dominates** — files must be fetched |
| Parse all files    | ~1–2s     | Small                          |
| Edge extraction    | <1s       | Tiny                           |
| Neo4j write        | <1s       | Tiny                           |

Incremental indexing saves the **parse time (~2s)**, but the clone still
happens regardless. **Net saving at our scale: marginal (~2s of ~60s).**

The real payoff appears at **huge-monorepo scale (50k+ files)**, where parsing
takes *minutes*. At that point, incremental becomes essential.

### Technical challenges to solve when revisiting

1. **Shallow clone has no history.** We use `git clone --depth 1`, so
   `git diff oldSHA newSHA` won't work (oldSHA isn't present).
   → **Solution:** content-hash each file; compare hashes across indexes.
   No git history needed.

2. **Cross-file edges.** Edges cross file boundaries. If file B changes and a
   call in *unchanged* file A points into B, A's edge can become stale even
   though A wasn't reprocessed.
   → This is the core difficulty: true incremental must track which files
   each edge depends on, and re-resolve edges touching any changed file.

### Approach when we build it

Three scoping options were analyzed:

- **Pragmatic** (recommended for first cut): content-hash files, re-parse only
  changed files, re-resolve edges for changed files + edges targeting them.
  ~80% of the value at ~40% of the complexity. Some rename edge-cases
  simplified.
- **Full**: precise edge-dependency tracking across all files; handles
  renames/moves/deletes correctly. Production-grade, ~2× the complexity.
  Worth it mainly at large scale.
- **Defer** (current choice): keep V3's wipe-and-rebuild; revisit when scale
  demands it.

### Trigger to build this

Revisit incremental indexing when **any** of these become true:

- Indexing a single repo takes more than ~30s in parse time alone.
- Codebases regularly exceed ~5,000 files.
- Users re-index the same large repo frequently and the wait becomes painful.

---

## 📌 Other known future work (Phase 2 — semantic layer)

Not yet built; tracked here for context:

- **Embeddings (ChromaDB)** — vector index for semantic search
  ("where is the auth logic?"), complementing the current structural graph.
- **Hybrid retrieval** — vectors locate entry points; graph traversal expands
  context around them.
- **LLM Q&A (Ollama)** — natural-language questions answered using
  graph + vector context.
- **UI (Streamlit)** — chat interface over the indexed repo.

- **Node ID disambiguation refinement** — current edges to duplicated
  functions resolve to the first variant by line (C1). A future refinement
  could use control-flow / type info to pick the runtime-active variant.

- **Private repo auth** — token injection into clone URL for private GitHub
  repos (the `token` param already exists in `repo_fetcher`, reserved for this).