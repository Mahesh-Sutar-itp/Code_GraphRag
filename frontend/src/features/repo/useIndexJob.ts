import { useState, useRef, useCallback } from "react";
import { api } from "../../api/client";
import type { IndexJob } from "../../api/types";

type Phase = "idle" | "running" | "completed" | "failed";

export function useIndexJob(onComplete?: (repoId: string) => void) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [job, setJob] = useState<IndexJob | null>(null);
  const pollRef = useRef<number | null>(null);

  const stopPolling = () => {
    if (pollRef.current !== null) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  const start = useCallback(
    async (url: string) => {
      setPhase("running");
      setJob(null);
      try {
        const { job_id, repo_id } = await api.startIndex(url);

        pollRef.current = window.setInterval(async () => {
          try {
            const status = await api.getIndexStatus(job_id);
            setJob(status);
            if (status.status === "completed") {
              stopPolling();
              setPhase("completed");
              onComplete?.(repo_id);
            } else if (status.status === "failed") {
              stopPolling();
              setPhase("failed");
            }
          } catch {
            stopPolling();
            setPhase("failed");
          }
        }, 700);
      } catch {
        setPhase("failed");
      }
    },
    [onComplete]
  );

  const reset = useCallback(() => {
    stopPolling();
    setPhase("idle");
    setJob(null);
  }, []);

  return { phase, job, start, reset };
}