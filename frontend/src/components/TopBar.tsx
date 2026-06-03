import { Settings, GitBranch, Sun, Moon } from "lucide-react";
import { useRepoStore } from "../stores/repo-store";
import { RepoDropdown } from "../features/repo/RepoDropdown";

type Props = {
  onIndexNew: () => void;
};

export function TopBar({ onIndexNew }: Props) {
  const theme = useRepoStore((s) => s.theme);
  const toggleTheme = useRepoStore((s) => s.toggleTheme);

  return (
    <header className="h-12 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between px-4 bg-white dark:bg-zinc-950">
      <div className="flex items-center gap-3 text-sm">
        <GitBranch className="h-[18px] w-[18px]" />
        <span className="font-medium">CodeGraph Studio</span>
        <span className="text-zinc-400 dark:text-zinc-600">·</span>
        <RepoDropdown onIndexNew={onIndexNew} />
      </div>
      <div className="flex items-center gap-1 text-zinc-500 dark:text-zinc-400">
        <button
          onClick={toggleTheme}
          title="Toggle theme (Ctrl+Shift+K)"
          className="p-1.5 rounded hover:bg-zinc-100 dark:hover:bg-zinc-800"
        >
          {theme === "dark" ? (
            <Sun className="h-4 w-4" />
          ) : (
            <Moon className="h-4 w-4" />
          )}
        </button>
        <button className="p-1.5 rounded hover:bg-zinc-100 dark:hover:bg-zinc-800">
          <Settings className="h-4 w-4" />
        </button>
      </div>
    </header>
  );
}