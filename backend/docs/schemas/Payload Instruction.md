# CodeGraph Payload Structure & Schema Reference

This document serves as the definitive reference for the ingestion payloads and schema structures across ChromaDB and Neo4j for the CodeGraph project. All team members must adhere to these exact structures to prevent context bloat and ensure graph integrity.

## 1. ChromaDB Payload (The Semantic Router)

ChromaDB has transitioned from a document store to a purely lightweight vector index. **Do not store raw code or rich metadata in Chroma.**

### Field Rules:
* **`ids`**: The exact, deterministic Unique ID generated upstream by the AST parser (e.g., `src.services.billingService.BillingController.calculateTotal`).
* **`embeddings`**: The core mathematical representation of the code chunk.
* **`metadatas.neo4j_node_id`**: Must perfectly mirror the `ids` field. This acts as the absolute primary key for the subsequent Neo4j lookup once nodes are reranked.
* **`documents`**: **MUST BE EMPTY** (e.g., `[""]`). The raw source code is strictly stored in Neo4j to prevent data duplication.
* **Excluded Metadata**: Do NOT include `file_path`, `type`, or `parent_class` here. Neo4j absorbs all rich metadata.

### Example Payload:
```json
{
  "ids": ["module.auth.loginUser"],
  "embeddings": [[0.142, -0.045, 0.891, 0.334]],
  "metadatas": [{"neo4j_node_id": "module.auth.loginUser"}],
  "documents": [""] 
}
```

---

## 2. Neo4j Schema & Payloads (The "Linked" Approach)

To prevent "Property Bloat" and maintain lightning-fast multi-hop traversals, Neo4j uses a decoupled schema. We split the data into **Structural Nodes** (lightweight architecture pointers) and **Document Nodes** (heavy multi-line string storage), connected by specific, typed edges.

### 2A. The Structural Node (The Lightweight Pointer)
Represents the actual AST architecture (e.g., a `Function`, `Class`, or `Module`).

**Example Payload:**
```json
{
  "id": "module.auth.loginUser",
  "name": "loginUser",
  "type": "Function",
  "file_path": "/src/controllers/auth.js",
  "parent_class": "AuthController"
}
```
*Note: `id` must exactly match the ChromaDB `ids` field for $O(1)$ lookups.*

### 2B. The Document Node (The Heavy Payload)
Designated strictly for text storage to keep the graph traversals lightweight.

**Example Payload:**
```json
{
  "id": "doc.module.auth.loginUser",
  "source_code": "public loginUser(req, res) {\n  // ... authentication logic ...\n}"
}
```
*Note: Prefix the structural ID with `doc.` to avoid primary key collisions.*

### 2C. Edge Payloads & Relationship Types
To accurately map the structural flow and link the heavy text data, Neo4j uses distinct edge types. Edges are represented as directional triplets.

**Type 1: Structural Edges (The Architecture)**
These edges are used exclusively to map how code components interact. These are the **ONLY** edges traversed during N-hop blast radius queries.
* **Valid Types:** `[:CALLS]`, `[:IMPORTS]`, `[:INHERITS]`, `[:IMPLEMENTS]`, `[:INSTANTIATES]`
* **Edge Payload (Properties):** Structural edges can carry lightweight metadata regarding the exact nature of the relationship.
  ```json
  {
    "type": "CALLS",
    "line_number": 42,
    "is_async": true
  }
  ```
* **Cypher Structure:** 
  ```cypher
  (Caller:Function)-[:CALLS {line_number: 42, is_async: true}]->(Callee:Function)
  

**Type 2: Document Edges (The Sealed Door)**
This edge links the structural architecture to the raw code. It is **NEVER** traversed during N-hop structural queries.
* **Valid Type:** `[:HAS_SOURCE_CODE]`
* **Edge Payload:** *None. This edge acts purely as a stateless pointer.*
* **Cypher Structure:** 
  ```cypher
  (StructuralNode)-[:HAS_SOURCE_CODE]->(DocumentNode)

---

## 3. Engineering Guidelines

* **Deterministic ID Creation:**
  IDs **MUST** be generated upstream by the AST parser (Layer 1) before any database interaction. Databases must never auto-generate these IDs. 
  * **The Formula:** `[namespace_or_file_path].[parent_entity].[target_entity]`
  * **Example 1 (Class Method):** A file `src/services/billing.ts` with class `BillingController` and method `calculateTotal` generates the ID: 
    * `src.services.billing.BillingController.calculateTotal`
  * **Example 2 (Standalone Function):** A file `utils/math.py` with a standalone function `add_numbers` generates the ID: 
    * `utils.math.add_numbers`
  * **Example 3 (Class Definition):** The definition of the `AuthService` class inside `core/auth.ts` generates the ID:
    * `core.auth.AuthService`

* **The Sequential Saga Pattern:** To avoid orphaned edges during ingestion, you must follow this strict execution order:
    1. Parse the AST and hold text chunks/relationships in memory.
    2. Attempt asynchronous embedding to ChromaDB first.
    3. **ONLY** if ChromaDB returns a strict success flag (200 OK), instantly commit the memory arrays to Neo4j. Never write to Neo4j first.