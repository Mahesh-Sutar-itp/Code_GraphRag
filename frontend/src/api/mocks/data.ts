import type { Repo, FileNode, QueryResponse, GraphNode } from "../types";

export const mockRepos: Repo[] = [
  {
    id: "pallets-click",
    name: "pallets/click",
    url: "https://github.com/pallets/click",
    indexed_at: "2025-01-15T10:30:00Z",
    total_files: 63,
    total_lines: 18432,
  },
  {
    id: "psf-requests",
    name: "psf/requests",
    url: "https://github.com/psf/requests",
    indexed_at: "2025-01-14T09:15:00Z",
    total_files: 112,
    total_lines: 24891,
  },
];

export const mockTree: FileNode[] = [
  {
    path: "src",
    name: "src",
    kind: "dir",
    children: [
      {
        path: "src/click",
        name: "click",
        kind: "dir",
        children: [
          { path: "src/click/core.py", name: "core.py", kind: "file" },
          { path: "src/click/types.py", name: "types.py", kind: "file" },
          { path: "src/click/_compat.py", name: "_compat.py", kind: "file" },
          { path: "src/click/decorators.py", name: "decorators.py", kind: "file" },
        ],
      },
    ],
  },
  { path: "README.md", name: "README.md", kind: "file" },
];

const sampleNodes: GraphNode[] = [
  {
    node_id: "src/click/types.py::StringParamType.convert",
    name: "StringParamType.convert",
    kind: "method",
    file_path: "src/click/types.py",
    start_line: 152,
    end_line: 168,
    source_code:
      "def convert(self, value, param, ctx):\n    if isinstance(value, bytes):\n        enc = _get_argv_encoding()\n        try:\n            value = value.decode(enc)\n        except UnicodeError:\n            value = value.decode('utf-8', 'replace')\n    return value",
  },
  {
    node_id: "src/click/_compat.py::_get_argv_encoding",
    name: "_get_argv_encoding",
    kind: "function",
    file_path: "src/click/_compat.py",
    start_line: 45,
    end_line: 52,
    source_code:
      "def _get_argv_encoding():\n    if WIN:\n        return 'mbcs'\n    return sys.getfilesystemencoding() or 'utf-8'",
  },
];

export const mockQueryResponse: QueryResponse = {
  answer:
    "`StringParamType.convert` checks if the value is bytes; if so, it decodes using the system argv encoding obtained from `_get_argv_encoding()`, falling back to UTF-8 with `errors='replace'` on failure. Otherwise it returns the value unchanged.",
  context: {
    nodes: sampleNodes,
    edges: [
      {
        source: "src/click/types.py::StringParamType.convert",
        target: "src/click/_compat.py::_get_argv_encoding",
      },
    ],
  },
};