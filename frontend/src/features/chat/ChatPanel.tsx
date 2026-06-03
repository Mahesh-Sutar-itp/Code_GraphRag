import { useEffect, useRef } from "react";
import { Trash2 } from "lucide-react";
import { useChat } from "./useChat";
import { ChatInput } from "./ChatInput";
import { MessageItem } from "./MessageItem";
import { useChatStore } from "../../stores/chat-store";
import { useRepoStore } from "../../stores/repo-store";

export function ChatPanel() {
  const { messages, send, isLoading } = useChat();
  const repoId = useRepoStore((s) => s.selectedRepoId);
  const clearRepo = useChatStore((s) => s.clearRepo);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, isLoading]);

  return (
    <div className="h-full flex flex-col">
      <div className="h-9 flex items-center justify-between px-4 border-b border-zinc-200 dark:border-zinc-800">
        <span className="text-[11px] uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
          Chat
        </span>
        {messages.length > 0 && (
          <button
            onClick={() => repoId && clearRepo(repoId)}
            title="Clear chat"
            className="p-1 rounded hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-400"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        )}
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.length === 0 && !isLoading && (
          <div className="h-full flex flex-col items-center justify-center gap-4 text-center">
            <p className="text-sm text-zinc-400 dark:text-zinc-600">
              Ask anything about this codebase
            </p>
            <div className="text-xs text-zinc-400 dark:text-zinc-600 space-y-1">
              <div>
                <kbd className="px-1.5 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 font-mono">
                  Ctrl+B
                </kbd>{" "}
                files
                <span className="mx-2">·</span>
                <kbd className="px-1.5 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 font-mono">
                  Ctrl+J
                </kbd>{" "}
                graph
                <span className="mx-2">·</span>
                <kbd className="px-1.5 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 font-mono">
                  Ctrl+Shift+K
                </kbd>{" "}
                theme
              </div>
            </div>
          </div>
        )}
        {messages.map((m) => (
          <MessageItem key={m.id} message={m} />
        ))}
        {isLoading && (
          <div className="flex items-center gap-2 text-sm text-zinc-400">
            <span className="h-1.5 w-1.5 rounded-full bg-zinc-400 animate-pulse" />
            Thinking...
          </div>
        )}
      </div>

      <ChatInput onSend={send} disabled={isLoading} />
    </div>
  );
}