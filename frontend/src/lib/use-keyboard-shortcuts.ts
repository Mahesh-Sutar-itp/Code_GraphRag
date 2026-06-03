import { useEffect } from "react";
import { useRepoStore } from "../stores/repo-store";

export function useKeyboardShortcuts() {
  const toggleLeftPane = useRepoStore((s) => s.toggleLeftPane);
  const toggleRightDrawer = useRepoStore((s) => s.toggleRightDrawer);
  const toggleTheme = useRepoStore((s) => s.toggleTheme);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const mod = e.ctrlKey || e.metaKey;
      if (!mod) return;

      const key = e.key.toLowerCase();

      if (key === "b" && !e.shiftKey) {
        e.preventDefault();
        toggleLeftPane();
      } else if (key === "j" && !e.shiftKey) {
        e.preventDefault();
        toggleRightDrawer();
      } else if (key === "k" && e.shiftKey) {
        e.preventDefault();
        toggleTheme();
      }
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [toggleLeftPane, toggleRightDrawer, toggleTheme]);
}