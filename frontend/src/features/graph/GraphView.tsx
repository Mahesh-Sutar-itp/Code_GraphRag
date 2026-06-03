import { useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  Handle,
  Position,
  type Node,
  type Edge,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import dagre from "@dagrejs/dagre";
import type { ChatContext } from "../../stores/chat-store";

const NODE_W = 180;
const NODE_H = 52;

const KIND_COLOR: Record<string, string> = {
  function: "#10b981", // emerald
  method: "#3b82f6", // blue
  class: "#f59e0b", // amber
};

function CodeNode({ data }: { data: { label: string; kind: string } }) {
  const color = KIND_COLOR[data.kind] ?? "#71717a";
  return (
    <div className="px-3 py-2 rounded-md border bg-white dark:bg-zinc-800 border-zinc-200 dark:border-zinc-700 shadow-sm w-[180px]">
      <Handle
        type="target"
        position={Position.Top}
        className="!bg-zinc-400 !border-0"
      />
      <div className="flex items-center gap-2">
        <span
          className="h-2 w-2 rounded-full shrink-0"
          style={{ background: color }}
        />
        <span className="text-xs font-medium text-zinc-800 dark:text-zinc-100 truncate">
          {data.label}
        </span>
      </div>
      <div className="text-[10px] text-zinc-400 dark:text-zinc-500 mt-0.5 pl-4">
        {data.kind}
      </div>
      <Handle
        type="source"
        position={Position.Bottom}
        className="!bg-zinc-400 !border-0"
      />
    </div>
  );
}

const nodeTypes = { codeNode: CodeNode };

function layoutGraph(context: ChatContext): { rfNodes: Node[]; rfEdges: Edge[] } {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: "TB", nodesep: 40, ranksep: 70 });

  context.nodes.forEach((n) =>
    g.setNode(n.node_id, { width: NODE_W, height: NODE_H })
  );
  context.edges.forEach((e) => g.setEdge(e.source, e.target));
  dagre.layout(g);

  const rfNodes: Node[] = context.nodes.map((n) => {
    const pos = g.node(n.node_id);
    return {
      id: n.node_id,
      type: "codeNode",
      position: { x: pos.x - NODE_W / 2, y: pos.y - NODE_H / 2 },
      data: { label: n.name, kind: n.kind },
    };
  });

  const rfEdges: Edge[] = context.edges.map((e, i) => ({
    id: `e${i}`,
    source: e.source,
    target: e.target,
    animated: true,
  }));

  return { rfNodes, rfEdges };
}

type Props = {
  context: ChatContext;
  onNodeSelect: (nodeId: string) => void;
};

export function GraphView({ context, onNodeSelect }: Props) {
  const { rfNodes, rfEdges } = useMemo(() => layoutGraph(context), [context]);

  return (
    <ReactFlow
      nodes={rfNodes}
      edges={rfEdges}
      nodeTypes={nodeTypes}
      fitView
      onNodeClick={(_, node) => onNodeSelect(node.id)}
      proOptions={{ hideAttribution: true }}
      className="bg-zinc-50 dark:bg-zinc-900"
    >
      <Background gap={16} className="dark:opacity-30" />
      <Controls showInteractive={false} />
    </ReactFlow>
  );
}