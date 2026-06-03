import { create } from "zustand";
import type { GraphNode, GraphEdge } from "../api/types";

export type ChatContext = {
  nodes: GraphNode[];
  edges: GraphEdge[];
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  context?: ChatContext;
};

export type CodeView = {
  path: string;
  content: string;
  startLine: number;
};

type ChatStore = {
  messagesByRepo: Record<string, ChatMessage[]>;
  activeContext: ChatContext | null;
  codeView: CodeView | null;

  addMessage: (repoId: string, msg: ChatMessage) => void;
  setActiveContext: (ctx: ChatContext | null) => void;
  setCodeView: (cv: CodeView | null) => void;
  clearRepo: (repoId: string) => void;
};

export const useChatStore = create<ChatStore>((set) => ({
  messagesByRepo: {},
  activeContext: null,
  codeView: null,

  addMessage: (repoId, msg) =>
    set((s) => ({
      messagesByRepo: {
        ...s.messagesByRepo,
        [repoId]: [...(s.messagesByRepo[repoId] ?? []), msg],
      },
    })),

  setActiveContext: (ctx) => set({ activeContext: ctx }),
  setCodeView: (cv) => set({ codeView: cv }),

  clearRepo: (repoId) =>
    set((s) => ({
      messagesByRepo: { ...s.messagesByRepo, [repoId]: [] },
    })),
}));