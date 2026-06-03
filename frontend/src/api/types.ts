export type Repo = {
  id: string;
  name: string;
  url: string;
  indexed_at: string;
  total_files: number;
  total_lines: number;
};

export type FileNode = {
  path: string;
  name: string;
  kind: "file" | "dir";
  children?: FileNode[];
};

export type GraphNode = {
  node_id: string;
  name: string;
  kind: "function" | "method" | "class";
  file_path: string;
  start_line: number;
  end_line: number;
  source_code: string;
};

export type GraphEdge = {
  source: string;
  target: string;
};

export type QueryRequest = {
  repo_id: string;
  question: string;
};

export type QueryResponse = {
  answer: string;
  context: {
    nodes: GraphNode[];
    edges: GraphEdge[];
  };
};

export type IndexJob = {
  job_id: string;
  status: "queued" | "running" | "completed" | "failed";
  stage: "cloning" | "parsing" | "edges" | "writing" | "done";
  progress: number;
  message?: string;
  error?: string;
};

export type FileContent = {
  path: string;
  content: string;
  language: string;
};