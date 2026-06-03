import { Network } from "lucide-react";
import { useState } from "react";

type Props = {
  onIndex: (url: string) => void;
};

export function EmptyState({ onIndex }: Props) {
  const [url, setUrl] = useState("");

  const submit = () => {
    const trimmed = url.trim();
    if (!trimmed) return;
    onIndex(trimmed);
  };

  return (
    <div className="h-full flex items-center justify-center p-8">
      <div className="max-w-md w-full text-center">
        <div className="inline-flex items-center justify-center h-14 w-14 rounded-full bg-zinc-100 dark:bg-zinc-900 mb-5">
          <Network className="h-7 w-7 text-zinc-500 dark:text-zinc-400" />
        </div>

        <h2 className="text-lg font-medium mb-1.5">Index your first repo</h2>
        <p className="text-sm text-zinc-500 dark:text-zinc-400 mb-6">
          Paste a public GitHub URL to build a queryable code graph
        </p>

        <div className="flex gap-2">
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && submit()}
            placeholder="https://github.com/pallets/click"
            className="flex-1 h-9 px-3 text-sm bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded outline-none focus:ring-1 focus:ring-blue-500"
          />
          <button
            onClick={submit}
            disabled={!url.trim()}
            className="h-9 px-4 text-sm font-medium bg-blue-600 hover:bg-blue-700 disabled:bg-zinc-300 dark:disabled:bg-zinc-800 disabled:text-zinc-500 text-white rounded transition-colors"
          >
            Index
          </button>
        </div>

        <p className="text-xs text-zinc-400 dark:text-zinc-500 mt-3">
          Shallow clone · typically 30–60s for medium repos
        </p>
      </div>
    </div>
  );
}