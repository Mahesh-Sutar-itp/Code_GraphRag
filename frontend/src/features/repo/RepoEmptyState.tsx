import { Network, Plus } from "lucide-react";
import { useState } from "react";

export function RepoEmptyState() {
  const [url, setUrl] = useState("");

  const handleIndex = () => {
    console.log("TODO: wire indexing in Step 2.3 —", url);
  };

  return (
    <div className="h-full flex items-center justify-center p-8">
      <div className="text-center max-w-md w-full">
        <Network className="h-9 w-9 text-zinc-400 dark:text-zinc-500 mx-auto mb-4" />
        <h2 className="text-lg font-medium mb-1">Index your first repo</h2>
        <p className="text-sm text-zinc-500 dark:text-zinc-400 mb-6">
          Paste a public GitHub URL to build a queryable code graph
        </p>
        <div className="flex gap-2">
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://github.com/pallets/click"
            className="flex-1 h-9 px-3 text-sm bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded outline-none focus:ring-1 focus:ring-blue-500"
          />
          <button
            onClick={handleIndex}
            disabled={!url}
            className="px-4 h-9 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5"
          >
            <Plus className="h-3.5 w-3.5" />
            Index
          </button>
        </div>
        <p className="text-xs text-zinc-400 dark:text-zinc-500 mt-3">
          Shallow clone, ~30–60s for medium repos
        </p>
      </div>
    </div>
  );
}