import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronRight, ChevronDown, File, Folder } from "lucide-react";
import { api } from "../../api/client";
import { useRepoStore } from "../../stores/repo-store";
import { useChatStore } from "../../stores/chat-store";
import type { FileNode } from "../../api/types";

function FileTreeNode({
  node,
  depth,
  onFileClick,
}: {
  node: FileNode;
  depth: number;
  onFileClick: (path: string) => void;
}) {
  const [expanded, setExpanded] = useState(depth < 2);

  if (node.kind === "dir") {
    return (
      <div>
        <button
          onClick={() => setExpanded((e) => !e)}
          style={{ paddingLeft: `${depth * 12 + 8}px` }}
          className="w-full flex items-center gap-1 py-1 pr-2 text-sm text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded"
        >
          {expanded ? (
            <ChevronDown className="h-3.5 w-3.5 shrink-0 text-zinc-400" />
          ) : (
            <ChevronRight className="h-3.5 w-3.5 shrink-0 text-zinc-400" />
          )}
          <Folder className="h-3.5 w-3.5 shrink-0 text-zinc-400" />
          <span className="truncate">{node.name}</span>
        </button>
        {expanded &&
          node.children?.map((child) => (
            <FileTreeNode
              key={child.path}
              node={child}
              depth={depth + 1}
              onFileClick={onFileClick}
            />
          ))}
      </div>
    );
  }

  return (
    <button
      onClick={() => onFileClick(node.path)}
      style={{ paddingLeft: `${depth * 12 + 24}px` }}
      className="w-full flex items-center gap-1.5 py-1 pr-2 text-sm text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded"
    >
      <File className="h-3.5 w-3.5 shrink-0 text-zinc-400" />
      <span className="truncate">{node.name}</span>
    </button>
  );
}

export function FileTree() {
  const repoId = useRepoStore((s) => s.selectedRepoId);
  const setCodeView = useChatStore((s) => s.setCodeView);
  const setRightDrawerOpen = useRepoStore((s) => s.setRightDrawerOpen);
  const queryClient = useQueryClient();

  const { data: tree, isLoading } = useQuery({
    queryKey: ["tree", repoId],
    queryFn: () => api.getTree(repoId!),
    enabled: !!repoId,
  });

  const openFile = async (path: string) => {
    if (!repoId) return;
    const file = await queryClient.fetchQuery({
      queryKey: ["file", repoId, path],
      queryFn: () => api.getFile(repoId, path),
    });
    setCodeView({ path: file.path, content: file.content, startLine: 1 });
    setRightDrawerOpen(true);
  };

  if (isLoading) {
    return <div className="p-3 text-sm text-zinc-400">Loading files...</div>;
  }

  return (
    <div className="p-1.5">
      {tree?.map((node) => (
        <FileTreeNode
          key={node.path}
          node={node}
          depth={0}
          onFileClick={openFile}
        />
      ))}
    </div>
  );
}