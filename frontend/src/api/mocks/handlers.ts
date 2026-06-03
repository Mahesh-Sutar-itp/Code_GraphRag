// All endpoints now hit real services:
//   - indexer (repos, tree, files, subgraph, index) → your FastAPI (localhost:8000)
//   - inference (resolve-query) → friend 3's service (VITE_INFERENCE_API)
// Nothing left to mock.
export const handlers = [];