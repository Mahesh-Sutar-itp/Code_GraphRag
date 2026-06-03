import { useState, useEffect } from "react";
import { X, Check, Loader2, Circle, AlertCircle } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { useIndexJob } from "./useIndexJob";
import { useRepoStore } from "../../stores/repo-store";
import type { IndexJob } from "../../api/types";

type Props = {
  open: boolean;
  onClose: () => void;
  initialUrl?: string;
};

const STAGES: { key: IndexJob["stage"]; label: string }[] = [
  { key: "cloning", label: "Cloning repository" },
  { key: "parsing", label: "Parsing definitions" },
  { key: "edges", label: "Extracting call edges" },
  { key: "writing", label: "Writing to graph" },
];

export function IndexModal({ open, onClose, initialUrl = "" }: Props) {
  const [url, setUrl] = useState("");
  const queryClient = useQueryClient();
  const setSelectedRepoId = useRepoStore((s) => s.setSelectedRepoId);
  const { phase, job, start, reset } = useIndexJob((repoId) => {
    queryClient.invalidateQueries({ queryKey: ["repos"] });
    setSelectedRepoId(repoId);
  });

  useEffect(() => {
    if (open) {
      setUrl(initialUrl);
      if (initialUrl.trim()) {
        start(initialUrl.trim());
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  if (!open) return null;

  const close = () => {
    reset();
    setUrl("");
    onClose();
  };

  const stageIndex = job ? STAGES.findIndex((s) => s.key === job.stage) : -1;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/40">
      <div className="w-[420px] bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-lg shadow-xl">
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-zinc-200 dark:border-zinc-800">
          <h3 className="text-sm font-medium">Index repository</h3>
          <button
            onClick={close}
            className="p-1 rounded hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-500"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="p-5">
          {phase === "idle" && (
            <>
              <input
                type="text"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && url.trim() && start(url.trim())}
                placeholder="https://github.com/pallets/click"
                autoFocus
                className="w-full h-9 px-3 text-sm bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded outline-none focus:ring-1 focus:ring-blue-500"
              />
              <div className="flex justify-end gap-2 mt-4">
                <button
                  onClick={close}
                  className="h-9 px-4 text-sm text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded"
                >
                  Cancel
                </button>
                <button
                  onClick={() => url.trim() && start(url.trim())}
                  disabled={!url.trim()}
                  className="h-9 px-4 text-sm font-medium bg-blue-600 hover:bg-blue-700 disabled:bg-zinc-300 dark:disabled:bg-zinc-800 disabled:text-zinc-500 text-white rounded"
                >
                  Index
                </button>
              </div>
            </>
          )}

          {(phase === "running" || phase === "completed") && (
            <>
              <div className="text-xs font-mono text-zinc-500 dark:text-zinc-400 mb-4 truncate">
                {url}
              </div>
              <div className="space-y-2.5">
                {STAGES.map((stage, idx) => {
                  const done = phase === "completed" || idx < stageIndex;
                  const active = phase === "running" && idx === stageIndex;
                  return (
                    <div
                      key={stage.key}
                      className="flex items-center gap-2.5 text-sm"
                    >
                      {done ? (
                        <Check className="h-4 w-4 text-green-600 dark:text-green-500" />
                      ) : active ? (
                        <Loader2 className="h-4 w-4 text-blue-600 dark:text-blue-400 animate-spin" />
                      ) : (
                        <Circle className="h-4 w-4 text-zinc-300 dark:text-zinc-700" />
                      )}
                      <span
                        className={
                          done || active
                            ? "text-zinc-900 dark:text-zinc-100"
                            : "text-zinc-400 dark:text-zinc-600"
                        }
                      >
                        {stage.label}
                      </span>
                    </div>
                  );
                })}
              </div>

              <div className="mt-4 h-1 bg-zinc-100 dark:bg-zinc-800 rounded overflow-hidden">
                <div
                  className="h-full bg-blue-600 dark:bg-blue-500 transition-all duration-500"
                  style={{ width: `${job?.progress ?? 0}%` }}
                />
              </div>

              {phase === "completed" && (
                <div className="flex justify-end mt-4">
                  <button
                    onClick={close}
                    className="h-9 px-4 text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white rounded"
                  >
                    Done
                  </button>
                </div>
              )}
            </>
          )}

          {phase === "failed" && (
            <>
              <div className="flex items-center gap-2 text-sm text-red-600 dark:text-red-400">
                <AlertCircle className="h-4 w-4" />
                Indexing failed. Please check the URL and try again.
              </div>
              <div className="flex justify-end gap-2 mt-4">
                <button
                  onClick={close}
                  className="h-9 px-4 text-sm text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded"
                >
                  Close
                </button>
                <button
                  onClick={reset}
                  className="h-9 px-4 text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white rounded"
                >
                  Try again
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}