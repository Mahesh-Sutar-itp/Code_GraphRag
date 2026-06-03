import { Files, Search, Network, History } from "lucide-react";
import { useRepoStore } from "../stores/repo-store";

type RailItem = {
  id: "files" | "search" | "graph" | "history";
  icon: typeof Files;
  label: string;
};

const items: RailItem[] = [
  { id: "files", icon: Files, label: "Files" },
  { id: "search", icon: Search, label: "Search" },
  { id: "graph", icon: Network, label: "Graph history" },
  { id: "history", icon: History, label: "Chat history" },
];

export function ActivityRail() {
  const leftPaneOpen = useRepoStore((s) => s.leftPaneOpen);
  const toggleLeftPane = useRepoStore((s) => s.toggleLeftPane);

  return (
    <nav className="w-12 border-r border-zinc-200 dark:border-zinc-800 flex flex-col items-center py-3 gap-1 bg-white dark:bg-zinc-950">
      {items.map((item) => {
        const Icon = item.icon;
        const isActive = item.id === "files" && leftPaneOpen;
        return (
          <button
            key={item.id}
            onClick={item.id === "files" ? toggleLeftPane : undefined}
            title={item.label}
            className={`
              w-9 h-9 rounded flex items-center justify-center
              hover:bg-zinc-100 dark:hover:bg-zinc-800
              ${
                isActive
                  ? "text-blue-600 dark:text-blue-400 bg-zinc-100 dark:bg-zinc-800"
                  : "text-zinc-500 dark:text-zinc-400"
              }
            `}
          >
            <Icon className="h-[18px] w-[18px]" />
          </button>
        );
      })}
    </nav>
  );
}