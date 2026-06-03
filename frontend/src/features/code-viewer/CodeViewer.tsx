import { useState } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark, oneLight } from "react-syntax-highlighter/dist/esm/styles/prism";
import { Copy, Check } from "lucide-react";
import { useRepoStore } from "../../stores/repo-store";
import type { CodeView } from "../../stores/chat-store";

export function CodeViewer({ view }: { view: CodeView }) {
  const theme = useRepoStore((s) => s.theme);
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(view.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard not available */
    }
  };

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between px-3 py-2 border-b border-zinc-100 dark:border-zinc-800 shrink-0">
        <span className="text-xs font-mono text-zinc-500 dark:text-zinc-400 truncate">
          {view.path}:{view.startLine}
        </span>
        <button
          onClick={copy}
          title="Copy"
          className="p-1 rounded hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-500 shrink-0"
        >
          {copied ? (
            <Check className="h-3.5 w-3.5 text-green-500" />
          ) : (
            <Copy className="h-3.5 w-3.5" />
          )}
        </button>
      </div>

      <div className="flex-1 overflow-auto">
        <SyntaxHighlighter
          language="python"
          style={theme === "dark" ? oneDark : oneLight}
          showLineNumbers
          startingLineNumber={view.startLine}
          customStyle={{
            margin: 0,
            padding: "12px",
            background: "transparent",
            fontSize: "12px",
          }}
          codeTagProps={{ style: { fontFamily: "ui-monospace, monospace" } }}
        >
          {view.content}
        </SyntaxHighlighter>
      </div>
    </div>
  );
}