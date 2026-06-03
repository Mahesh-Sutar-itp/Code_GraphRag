import { X } from "lucide-react";
import { useRepoStore } from "../stores/repo-store";
import { FileTree } from "../features/file-tree/FileTree";

export function LeftPane() {
  const setLeftPaneOpen = useRepoStore((s) => s.setLeftPaneOpen);

  return (
    <aside className="h-full flex flex-col bg-white dark:bg-zinc-950 border-r border-zinc-200 dark:border-zinc-800">
      <div className="h-9 flex items-center justify-between px-3 border-b border-zinc-200 dark:border-zinc-800">
        <span className="text-[11px] uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
          Files
        </span>
        <button
          onClick={() => setLeftPaneOpen(false)}
          className="p-1 rounded hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-500"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>
      <div className="flex-1 overflow-y-auto">
        <FileTree />
      </div>
    </aside>
  );
}