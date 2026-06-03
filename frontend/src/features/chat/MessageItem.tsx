import { Network } from "lucide-react";
import type { ChatMessage } from "../../stores/chat-store";
import { useChatStore } from "../../stores/chat-store";
import { useRepoStore } from "../../stores/repo-store";
import { Markdown } from "./Markdown";

export function MessageItem({ message }: { message: ChatMessage }) {
  const setActiveContext = useChatStore((s) => s.setActiveContext);
  const setRightDrawerOpen = useRepoStore((s) => s.setRightDrawerOpen);

  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="px-3 py-2 rounded bg-blue-50 dark:bg-blue-950/40 text-blue-900 dark:text-blue-200 text-sm max-w-[80%]">
          {message.content}
        </div>
      </div>
    );
  }

  const nodeCount = message.context?.nodes.length ?? 0;

  return (
    <div className="space-y-2">
      <div className="text-sm text-zinc-700 dark:text-zinc-300">
        <Markdown>{message.content}</Markdown>
      </div>
      {nodeCount > 0 && (
        <button
          onClick={() => {
            setActiveContext(message.context!);
            setRightDrawerOpen(true);
          }}
          className="inline-flex items-center gap-2 px-3 py-1.5 text-xs border border-zinc-200 dark:border-zinc-800 rounded hover:bg-zinc-50 dark:hover:bg-zinc-900 text-zinc-600 dark:text-zinc-400"
        >
          <Network className="h-3.5 w-3.5" />
          Show graph context ({nodeCount} function{nodeCount > 1 ? "s" : ""})
        </button>
      )}
    </div>
  );
}