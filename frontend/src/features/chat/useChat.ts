import { useMutation } from "@tanstack/react-query";
import { api } from "../../api/client";
import { useChatStore } from "../../stores/chat-store";
import type { ChatMessage } from "../../stores/chat-store";
import { useRepoStore } from "../../stores/repo-store";

const EMPTY: ChatMessage[] = [];

export function useChat() {
  const repoId = useRepoStore((s) => s.selectedRepoId);
  const messages = useChatStore((s) =>
    repoId ? s.messagesByRepo[repoId] ?? EMPTY : EMPTY
  );
  const addMessage = useChatStore((s) => s.addMessage);

  const mutation = useMutation({
    mutationFn: (question: string) =>
      api.query({ repo_id: repoId!, question }),
  });

  const send = async (question: string) => {
    const q = question.trim();
    if (!q || !repoId) return;

    addMessage(repoId, {
      id: `u_${Date.now()}`,
      role: "user",
      content: q,
    });

    try {
      const res = await mutation.mutateAsync(q);
      addMessage(repoId, {
        id: `a_${Date.now()}`,
        role: "assistant",
        content: res.answer,
        context: res.context,
      });
    } catch {
      addMessage(repoId, {
        id: `e_${Date.now()}`,
        role: "assistant",
        content: "Sorry, something went wrong. Please try again.",
      });
    }
  };

  return { messages, send, isLoading: mutation.isPending };
}