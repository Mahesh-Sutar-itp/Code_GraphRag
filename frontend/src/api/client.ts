import type {
  Repo,
  FileNode,
  FileContent,
  QueryRequest,
  QueryResponse,
  IndexJob,
} from "./types";

// Real indexer API (your FastAPI). Inference stays mocked until friend 3 is ready.
const INDEXER_BASE = import.meta.env.VITE_INDEXER_API ?? "http://localhost:8000";
const INFERENCE_BASE = import.meta.env.VITE_INFERENCE_API ?? "/api";

const SESSION_ID = crypto.randomUUID();

async function request<T>(
  base: string,
  path: string,
  init?: RequestInit
): Promise<T> {
  const res = await fetch(`${base}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    throw new Error(`API ${path} failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

function slugFromUrl(url: string): string {
  return url
    .replace(/^https?:\/\/github\.com\//, "")
    .replace(/\.git$/, "")
    .replace(/\/$/, "")
    .replace(/\//g, "-");
}

export const api = {
  listRepos: () => request<Repo[]>(INDEXER_BASE, "/repos"),

  getTree: (repoId: string) =>
    request<FileNode[]>(INDEXER_BASE, `/repos/${repoId}/tree`),

  getFile: (repoId: string, path: string) =>
    request<FileContent>(
      INDEXER_BASE,
      `/repos/${repoId}/files?path=${encodeURIComponent(path)}`
    ),

  query: async (body: QueryRequest): Promise<QueryResponse> => {
    const raw = await request<{
      status: string;
      code: number;
      msg: string;
      node_ids?: string[];
    }>(INFERENCE_BASE, "/resolve-query", {
      method: "POST",
      body: JSON.stringify({
        user_id: "local-user",
        session_id: SESSION_ID,
        user_query: body.question,
      }),
    });

    if (raw.status.toLowerCase() !== "success") {
      throw new Error(raw.msg || "Query failed");
    }

    // Edges live in the graph, not the LLM — fetch the subgraph by node_ids
    let context: QueryResponse["context"] = { nodes: [], edges: [] };
    if (raw.node_ids && raw.node_ids.length > 0) {
      context = await request<QueryResponse["context"]>(
        INDEXER_BASE,
        "/subgraph",
        {
          method: "POST",
          body: JSON.stringify({ node_ids: raw.node_ids }),
        }
      );
    }

    return { answer: raw.msg, context };
  },

  startIndex: async (url: string) => {
    const raw = await request<{ job_id: string; status: string }>(
      INDEXER_BASE,
      "/index-repository",
      {
        method: "POST",
        body: JSON.stringify({ url }),
      }
    );
    // Real API returns job_id + status; derive repo_id client-side for the UI
    return { ...raw, repo_id: slugFromUrl(url) };
  },

  getIndexStatus: (jobId: string) =>
    request<IndexJob>(INDEXER_BASE, `/index-repository/${jobId}/status`),
};