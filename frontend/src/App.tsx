import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { TopBar } from "./components/TopBar";
import { ActivityRail } from "./components/ActivityRail";
import { MainLayout } from "./components/MainLayout";
import { EmptyState } from "./features/repo/EmptyState";
import { IndexModal } from "./features/repo/IndexModal";
import { useRepoStore } from "./stores/repo-store";
import { useKeyboardShortcuts } from "./lib/use-keyboard-shortcuts";
import { api } from "./api/client";

function App() {
  const theme = useRepoStore((s) => s.theme);
  const selectedRepoId = useRepoStore((s) => s.selectedRepoId);
  const setSelectedRepoId = useRepoStore((s) => s.setSelectedRepoId);
  useKeyboardShortcuts();

  const [modalOpen, setModalOpen] = useState(false);
  const [modalInitialUrl, setModalInitialUrl] = useState("");

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
  }, [theme]);

  const { data: repos, isLoading } = useQuery({
    queryKey: ["repos"],
    queryFn: api.listRepos,
  });

  useEffect(() => {
    if (!selectedRepoId && repos && repos.length > 0) {
      setSelectedRepoId(repos[0].id);
    }
  }, [selectedRepoId, repos, setSelectedRepoId]);

  const showEmptyState = !isLoading && (!repos || repos.length === 0);

  const openModal = (url = "") => {
    setModalInitialUrl(url);
    setModalOpen(true);
  };

  return (
    <div className="h-full flex flex-col bg-white dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100">
      <TopBar onIndexNew={() => openModal()} />
      <div className="flex-1 flex overflow-hidden">
        {!showEmptyState && <ActivityRail />}
        <div className="flex-1 overflow-hidden">
          {showEmptyState ? (
            <EmptyState onIndex={(url) => openModal(url)} />
          ) : (
            <MainLayout />
          )}
        </div>
      </div>

      <IndexModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        initialUrl={modalInitialUrl}
      />
    </div>
  );
}

export default App;