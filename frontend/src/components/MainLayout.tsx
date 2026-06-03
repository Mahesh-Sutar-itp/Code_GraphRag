import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";
import { useRepoStore } from "../stores/repo-store";
import { LeftPane } from "./LeftPane";
import { RightDrawer } from "./RightDrawer";
import { ChatPanel } from "../features/chat/ChatPanel";

export function MainLayout() {
  const leftPaneOpen = useRepoStore((s) => s.leftPaneOpen);
  const rightDrawerOpen = useRepoStore((s) => s.rightDrawerOpen);

  return (
    <PanelGroup
      key={`${leftPaneOpen}|${rightDrawerOpen}`}
      direction="horizontal"
      className="h-full"
    >
      {leftPaneOpen && (
        <>
          <Panel defaultSize={18} minSize={12} maxSize={30}>
            <LeftPane />
          </Panel>
          <PanelResizeHandle className="w-px bg-zinc-200 dark:bg-zinc-800 hover:bg-blue-500 transition-colors" />
        </>
      )}

      <Panel minSize={30}>
        <ChatPanel />
      </Panel>

      {rightDrawerOpen && (
        <>
          <PanelResizeHandle className="w-px bg-zinc-200 dark:bg-zinc-800 hover:bg-blue-500 transition-colors" />
          <Panel defaultSize={28} minSize={18} maxSize={45}>
            <RightDrawer />
          </Panel>
        </>
      )}
    </PanelGroup>
  );
}