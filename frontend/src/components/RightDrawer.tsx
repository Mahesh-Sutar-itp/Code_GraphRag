import { X } from "lucide-react";
import { useState, useEffect } from "react";
import { useRepoStore } from "../stores/repo-store";
import { useChatStore } from "../stores/chat-store";
import { GraphView } from "../features/graph/GraphView";
import { CodeViewer } from "../features/code-viewer/CodeViewer";

type Tab = "graph" | "code";

export function RightDrawer() {
  const setRightDrawerOpen = useRepoStore((s) => s.setRightDrawerOpen);
  const activeContext = useChatStore((s) => s.activeContext);
  const codeView = useChatStore((s) => s.codeView);
  const setCodeView = useChatStore((s) => s.setCodeView);
  const [activeTab, setActiveTab] = useState<Tab>("graph");

  const nodes = activeContext?.nodes ?? [];

  // When new code is selected anywhere (graph node or file tree), show Code tab
  useEffect(() => {
    if (codeView) setActiveTab("code");
  }, [codeView]);

  const selectById = (id: string) => {
    const n = nodes.find((x) => x.node_id === id);
    if (n) {
      setCodeView({
        path: n.file_path,
        content: n.source_code,
        startLine: n.start_line,
      });
    }
  };

  const tabClass = (tab: Tab) =>
    `px-3 h-full border-r border-zinc-200 dark:border-zinc-800 ${
      activeTab === tab
        ? "bg-zinc-50 dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100"
        : "text-zinc-500 dark:text-zinc-400"
    }`;

  return (
    <aside className="h-full flex flex-col bg-white dark:bg-zinc-950 border-l border-zinc-200 dark:border-zinc-800">
      <div className="h-9 flex items-center border-b border-zinc-200 dark:border-zinc-800 text-xs shrink-0">
        <button onClick={() => setActiveTab("graph")} className={tabClass("graph")}>
          Graph
        </button>
        <button onClick={() => setActiveTab("code")} className={tabClass("code")}>
          Code
        </button>
        <div className="flex-1" />
        <button
          onClick={() => setRightDrawerOpen(false)}
          className="p-2 hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-500"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>

      <div className="flex-1 min-h-0">
        {activeTab === "graph" &&
          (nodes.length === 0 ? (
            <div className="p-4 text-sm text-zinc-400 dark:text-zinc-600">
              No graph context yet. Ask a question, then click "Show graph
              context".
            </div>
          ) : (
            <div className="h-full">
              <GraphView context={activeContext!} onNodeSelect={selectById} />
            </div>
          ))}

        {activeTab === "code" &&
          (codeView ? (
            <CodeViewer view={codeView} />
          ) : (
            <div className="p-4 text-sm text-zinc-400 dark:text-zinc-600">
              Click a node or file to view its code.
            </div>
          ))}
      </div>
    </aside>
  );
}