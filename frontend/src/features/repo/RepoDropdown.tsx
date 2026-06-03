import { useState, useRef, useEffect } from "react";
import { ChevronDown, Check, Plus } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../api/client";
import { useRepoStore } from "../../stores/repo-store";

type Props = {
  onIndexNew: () => void;
};

export function RepoDropdown({ onIndexNew }: Props) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const selectedRepoId = useRepoStore((s) => s.selectedRepoId);
  const setSelectedRepoId = useRepoStore((s) => s.setSelectedRepoId);

  const { data: repos } = useQuery({
    queryKey: ["repos"],
    queryFn: api.listRepos,
  });

  const selected = repos?.find((r) => r.id === selectedRepoId);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1 px-2.5 py-1 rounded border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-700 dark:text-zinc-300"
      >
        <span>{selected?.name ?? "Select repo"}</span>
        <ChevronDown className="h-3.5 w-3.5 text-zinc-400" />
      </button>

      {open && (
        <div className="absolute top-full left-0 mt-1 w-72 z-50 bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-md shadow-lg p-1.5">
          <div className="px-2 py-1.5 text-[11px] uppercase tracking-wide text-zinc-400 dark:text-zinc-500">
            Indexed Repos
          </div>

          {repos?.map((r) => {
            const isSelected = r.id === selectedRepoId;
            return (
              <button
                key={r.id}
                onClick={() => {
                  setSelectedRepoId(r.id);
                  setOpen(false);
                }}
                className={`w-full flex items-center justify-between px-2 py-1.5 rounded text-sm ${
                  isSelected
                    ? "bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300"
                    : "hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-700 dark:text-zinc-300"
                }`}
              >
                <span className="flex items-center gap-2">
                  {isSelected ? (
                    <Check className="h-3.5 w-3.5" />
                  ) : (
                    <span className="w-3.5" />
                  )}
                  {r.name}
                </span>
                <span className="text-xs text-zinc-400">
                  {r.total_files} files
                </span>
              </button>
            );
          })}

          <div className="border-t border-zinc-100 dark:border-zinc-800 mt-1 pt-1">
            <button
              onClick={() => {
                setOpen(false);
                onIndexNew();
              }}
              className="w-full flex items-center gap-2 px-2 py-1.5 rounded text-sm text-blue-600 dark:text-blue-400 hover:bg-zinc-100 dark:hover:bg-zinc-800"
            >
              <Plus className="h-3.5 w-3.5" />
              Index new repo
            </button>
          </div>
        </div>
      )}
    </div>
  );
}