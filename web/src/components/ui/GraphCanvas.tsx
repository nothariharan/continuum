"use client";

import { useCallback, useEffect, useMemo } from "react";
import Image from "next/image";
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  type Node,
  type Edge,
  useNodesState,
  useEdgesState,
  Handle,
  Position,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type { GraphExport, GraphNode } from "@/lib/contracts";

const SOURCE_ICONS: Record<string, string> = {
  slack: "/brand/slack.svg",
  gmail: "/brand/gmail.svg",
  linear: "/brand/linear.svg",
  github: "/brand/github.svg",
  drive: "/brand/drive.svg",
  notion: "/brand/notion.svg",
  jira: "/brand/jira.svg",
  confluence: "/brand/confluence.svg",
  teams: "/brand/teams.svg",
};

// Custom Node Component for ReactFlow (Light Mode Attio Style)
function CustomGraphNode({ data, selected }: { data: GraphNode & { selected?: boolean }; selected?: boolean }) {
  const isSelected = selected || data.selected;
  const isEntity = data.type === "entity";
  const isPerson = data.type === "person";
  const isSource = data.type === "source";
  const isArtifact = data.type === "artifact";

  const iconSrc = data.source ? SOURCE_ICONS[data.source.toLowerCase()] : null;

  return (
    <div
      className={`group relative flex items-center gap-2.5 rounded-2xl border px-4 py-2.5 shadow-sm transition-all duration-200 ${
        isSelected
          ? "border-[var(--purple)] bg-white shadow-[0_8px_24px_-4px_rgba(99,102,241,0.25)] ring-2 ring-[var(--purple)]/30 text-[var(--charcoal)]"
          : isEntity
          ? "border-indigo-200 bg-white text-[var(--charcoal)] hover:border-indigo-400 hover:shadow-md"
          : isPerson
          ? "border-sky-200 bg-white text-[var(--charcoal)] hover:border-sky-400 hover:shadow-md"
          : isSource
          ? "border-emerald-200 bg-white text-[var(--charcoal)] hover:border-emerald-400 hover:shadow-md"
          : isArtifact
          ? "border-amber-200 bg-white text-[var(--charcoal)] hover:border-amber-400 hover:shadow-md"
          : "border-slate-200 bg-white text-[var(--charcoal)] hover:border-slate-300 hover:shadow-md"
      }`}
    >
      <Handle type="target" position={Position.Top} className="opacity-0" />
      <Handle type="source" position={Position.Bottom} className="opacity-0" />

      {iconSrc && (
        <div className="flex h-5 w-5 shrink-0 items-center justify-center">
          <Image src={iconSrc} alt={data.name} width={16} height={16} className="object-contain" />
        </div>
      )}

      {!iconSrc && isPerson && (
        <div className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-sky-100 text-[10px] font-bold text-sky-700">
          {data.name.charAt(0)}
        </div>
      )}

      {!iconSrc && isEntity && (
        <div className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-[10px] font-bold text-indigo-700">
          ★
        </div>
      )}

      <div>
        <div className="flex items-center gap-1.5">
          <span className="font-semibold text-xs text-[var(--charcoal)]">{data.name}</span>
        </div>
        <div className="flex items-center gap-1 font-mono text-[9px] uppercase tracking-wider text-[var(--charcoal-muted)]">
          <span>{data.type}</span>
          {data.source && <span>· {data.source}</span>}
        </div>
      </div>
    </div>
  );
}

const nodeTypes = {
  custom: CustomGraphNode,
};

function layoutNodes(nodes: GraphNode[], centerId: string): Node[] {
  const center = nodes.find((n) => n.id === centerId) ?? nodes[0];
  const others = nodes.filter((n) => n.id !== center?.id);
  const positioned: Node[] = [];

  const centerX = 360;
  const centerY = 240;

  if (center) {
    positioned.push({
      id: center.id,
      type: "custom",
      data: { ...center, selected: true },
      position: { x: centerX - 60, y: centerY - 25 },
    });
  }

  others.forEach((node, index) => {
    const angle = (index / Math.max(others.length, 1)) * Math.PI * 2;
    const radius = node.type === "source" ? 220 : node.type === "person" ? 150 : 180;
    positioned.push({
      id: node.id,
      type: "custom",
      data: { ...node, selected: false },
      position: {
        x: centerX + Math.cos(angle) * radius - 55,
        y: centerY + Math.sin(angle) * radius - 20,
      },
    });
  });

  return positioned;
}

export function GraphCanvas({
  graph,
  compact = false,
  selectedId,
  onSelect,
}: {
  graph: GraphExport;
  compact?: boolean;
  selectedId?: string;
  onSelect?: (node: GraphNode | null) => void;
}) {
  const centerId = selectedId ?? graph.entity;

  const initialNodes = useMemo(
    () => layoutNodes(graph.nodes, centerId),
    [graph.nodes, centerId],
  );

  const initialEdges = useMemo<Edge[]>(
    () =>
      graph.edges.map((e, i) => ({
        id: `e-${i}-${e.source}-${e.target}`,
        source: e.source,
        target: e.target,
        label: e.predicate,
        animated: true,
        style: { stroke: "rgba(99, 102, 241, 0.45)", strokeWidth: 1.5 },
        labelStyle: { fill: "#64748b", fontSize: 9, fontFamily: "monospace" },
        labelBgStyle: { fill: "#ffffff", stroke: "#e2e8f0", strokeWidth: 1 },
        labelBgPadding: [4, 2] as [number, number],
        labelBgBorderRadius: 4,
      })),
    [graph.edges],
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  useEffect(() => {
    setNodes(layoutNodes(graph.nodes, centerId));
    setEdges(
      graph.edges.map((e, i) => ({
        id: `e-${i}-${e.source}-${e.target}`,
        source: e.source,
        target: e.target,
        label: e.predicate,
        animated: true,
        style: { stroke: "rgba(99, 102, 241, 0.45)", strokeWidth: 1.5 },
        labelStyle: { fill: "#64748b", fontSize: 9, fontFamily: "monospace" },
        labelBgStyle: { fill: "#ffffff", stroke: "#e2e8f0", strokeWidth: 1 },
        labelBgPadding: [4, 2] as [number, number],
        labelBgBorderRadius: 4,
      })),
    );
  }, [graph, centerId, setNodes, setEdges]);

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      const found = graph.nodes.find((n) => n.id === node.id) ?? null;
      onSelect?.(found);
      setNodes((nds) =>
        nds.map((n) => ({
          ...n,
          data: {
            ...n.data,
            selected: n.id === node.id,
          },
        })),
      );
    },
    [graph.nodes, onSelect, setNodes],
  );

  return (
    <div
      className={`relative w-full overflow-hidden rounded-3xl border border-black/[0.08] bg-[#f8fafc] shadow-xs ${
        compact ? "h-[360px]" : "h-[540px] md:h-[620px]"
      }`}
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.5}
        maxZoom={1.5}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="rgba(15, 23, 42, 0.08)" gap={24} size={1.5} />
        {!compact && (
          <MiniMap
            nodeColor={(n) => {
              const nodeData = n.data as unknown as GraphNode;
              if (nodeData.type === "person") return "#0284c7";
              if (nodeData.type === "source") return "#059669";
              if (nodeData.type === "artifact") return "#d97706";
              return "#6366f1";
            }}
            className="!bg-white/90 !border !border-black/[0.08] !rounded-xl !shadow-xs"
          />
        )}
        <Controls className="!bg-white !border !border-black/[0.08] !rounded-xl !shadow-xs overflow-hidden [&>button]:!bg-white [&>button]:!border-black/[0.06] [&>button]:!text-slate-700 hover:[&>button]:!bg-slate-50" />
      </ReactFlow>
    </div>
  );
}

export function EntityCard({ node }: { node: GraphNode | null }) {
  if (!node) {
    return (
      <div className="rounded-3xl border border-black/[0.08] bg-white p-6 text-sm text-[var(--charcoal-muted)] shadow-xs">
        <p className="font-semibold text-[var(--charcoal)]">Spatial Entity Inspector</p>
        <p className="mt-2 text-xs text-[var(--charcoal-muted)] leading-relaxed">
          Click any node in the graph above to inspect canonical state, aliases, and provenance edges.
        </p>
      </div>
    );
  }

  const isEntity = node.type === "entity";
  const isPerson = node.type === "person";
  const isArtifact = node.type === "artifact";

  return (
    <div className="rounded-3xl border border-black/[0.08] bg-white p-6 text-[var(--charcoal)] shadow-sm">
      <div className="flex items-center justify-between">
        <span className="rounded-full bg-indigo-50 border border-indigo-200 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-indigo-700">
          {node.type}
        </span>
        <span className="font-mono text-[10px] text-[var(--charcoal-muted)]">{node.id}</span>
      </div>

      <p className="mt-3 text-2xl font-semibold tracking-tight text-[var(--charcoal)]">{node.name}</p>

      <div className="mt-4 space-y-3 border-t border-black/[0.06] pt-4 text-xs">
        {isEntity && (
          <div>
            <span className="text-[var(--charcoal-muted)]">Current Resolved State:</span>
            <p className="mt-0.5 font-semibold text-emerald-700">Owner: Priya (effective Aug 01)</p>
          </div>
        )}

        {isPerson && (
          <div>
            <span className="text-[var(--charcoal-muted)]">Role / Status:</span>
            <p className="mt-0.5 font-semibold text-sky-700">Active Maintainer & Team Lead</p>
          </div>
        )}

        {isArtifact && (
          <div>
            <span className="text-[var(--charcoal-muted)]">Provenance Artifact:</span>
            <p className="mt-0.5 font-mono text-[11px] text-[var(--charcoal-body)]">
              Source: {node.source ?? "Slack"} · Hash: sha256_e829fa
            </p>
          </div>
        )}

        <div>
          <span className="text-[var(--charcoal-muted)]">Canonical Key:</span>
          <p className="mt-0.5 font-mono text-[11px] text-[var(--charcoal-body)]">{node.id}</p>
        </div>

        {node.source && (
          <div>
            <span className="text-[var(--charcoal-muted)]">Ingestion Origin:</span>
            <p className="mt-0.5 font-semibold capitalize text-emerald-700">{node.source}</p>
          </div>
        )}
      </div>
    </div>
  );
}
