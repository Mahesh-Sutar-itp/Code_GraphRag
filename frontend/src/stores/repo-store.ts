import { create } from "zustand";
import { persist } from "zustand/middleware";

type RepoStore = {
  selectedRepoId: string | null;
  setSelectedRepoId: (id: string | null) => void;

  leftPaneOpen: boolean;
  rightDrawerOpen: boolean;
  toggleLeftPane: () => void;
  toggleRightDrawer: () => void;
  setLeftPaneOpen: (open: boolean) => void;
  setRightDrawerOpen: (open: boolean) => void;

  theme: "light" | "dark";
  toggleTheme: () => void;
};

export const useRepoStore = create<RepoStore>()(
  persist(
    (set) => ({
      selectedRepoId: null,
      setSelectedRepoId: (id) => set({ selectedRepoId: id }),

      leftPaneOpen: false,
      rightDrawerOpen: false,
      toggleLeftPane: () => set((s) => ({ leftPaneOpen: !s.leftPaneOpen })),
      toggleRightDrawer: () =>
        set((s) => ({ rightDrawerOpen: !s.rightDrawerOpen })),
      setLeftPaneOpen: (open) => set({ leftPaneOpen: open }),
      setRightDrawerOpen: (open) => set({ rightDrawerOpen: open }),

      theme: "dark",
      toggleTheme: () =>
        set((s) => ({ theme: s.theme === "dark" ? "light" : "dark" })),
    }),
    {
      name: "codegraph-ui-state",
    }
  )
);