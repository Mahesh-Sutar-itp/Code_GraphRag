import { useState } from "react";
import { Send } from "lucide-react";

type Props = {
  onSend: (text: string) => void;
  disabled?: boolean;
};

export function ChatInput({ onSend, disabled }: Props) {
  const [text, setText] = useState("");

  const submit = () => {
    const t = text.trim();
    if (!t || disabled) return;
    onSend(t);
    setText("");
  };

  return (
    <div className="h-12 flex items-center gap-2 px-4 border-t border-zinc-200 dark:border-zinc-800">
      <input
        type="text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && submit()}
        placeholder="Ask about this codebase..."
        className="flex-1 h-8 px-3 text-sm bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded outline-none focus:ring-1 focus:ring-blue-500"
      />
      <button
        onClick={submit}
        disabled={!text.trim() || disabled}
        className="p-1.5 rounded text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-800 disabled:opacity-40"
      >
        <Send className="h-[18px] w-[18px]" />
      </button>
    </div>
  );
}