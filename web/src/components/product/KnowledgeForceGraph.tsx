"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import dynamic from "next/dynamic";

// react-force-graph-2d is canvas/DOM-only — load client-side.
const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false });

export type GState = "dim" | "highlight" | "primary";
export type GNode = { id: string; label?: string; group?: string; kind?: string; val?: number; state?: GState };
export type GLink = { source: string; target: string; state?: GState };

// Light-theme palette (matches the site).
const NODE: Record<GState, string> = {
  dim: "#c3c7d2", // soft slate — visible on paper, recedes
  highlight: "#7c6cf0", // brand purple — relevant cluster
  primary: "#f59e0b", // amber — the answer path
};
const LINK: Record<GState, string> = {
  dim: "rgba(15,23,42,0.10)",
  highlight: "rgba(124,108,240,0.55)",
  primary: "rgba(245,158,11,0.85)",
};
const BG = "#ffffff";

export function KnowledgeForceGraph({
  nodes,
  links,
  height = 440,
}: {
  nodes: GNode[];
  links: GLink[];
  height?: number;
}) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const fgRef = useRef<{ d3Force: (n: string) => { strength?: (v: number) => unknown; distance?: (v: number) => unknown } | undefined; d3ReheatSimulation?: () => void } | null>(null);
  const [width, setWidth] = useState(600);
  const hoverRef = useRef<string | null>(null);

  useEffect(() => {
    const measure = () => wrapRef.current && setWidth(wrapRef.current.clientWidth);
    measure();
    const ro = new ResizeObserver(measure);
    if (wrapRef.current) ro.observe(wrapRef.current);
    return () => ro.disconnect();
  }, []);

  // Organic, spread-out clustering (Obsidian-like).
  useEffect(() => {
    const fg = fgRef.current;
    if (!fg) return;
    try {
      fg.d3Force("charge")?.strength?.(-95);
      fg.d3Force("link")?.distance?.(34);
      fg.d3ReheatSimulation?.();
    } catch {
      /* forces not ready */
    }
  }, [nodes, links]);

  const data = useMemo(() => ({ nodes: nodes.map((n) => ({ ...n })), links: links.map((l) => ({ ...l })) }), [nodes, links]);

  return (
    <div ref={wrapRef} className="w-full overflow-hidden rounded-3xl border border-[var(--paper-border)]" style={{ height, background: BG }}>
      {/* @ts-expect-error dynamic import loses generic typing */}
      <ForceGraph2D
        ref={fgRef}
        width={width}
        height={height}
        graphData={data}
        backgroundColor={BG}
        cooldownTicks={140}
        d3VelocityDecay={0.3}
        warmupTicks={40}
        nodeRelSize={5}
        nodeLabel={(n: GNode) => n.label ?? n.id}
        onNodeHover={(n: GNode | null) => {
          hoverRef.current = n?.id ?? null;
          if (wrapRef.current) wrapRef.current.style.cursor = n ? "pointer" : "default";
        }}
        linkColor={(l: GLink) => LINK[l.state ?? "dim"]}
        linkWidth={(l: GLink) => (l.state === "primary" ? 2 : l.state === "highlight" ? 1.4 : 0.6)}
        nodeCanvasObject={(node: GNode & { x?: number; y?: number }, ctx: CanvasRenderingContext2D, scale: number) => {
          const st = node.state ?? "dim";
          const hovered = hoverRef.current === node.id;
          let r = st === "primary" ? 7 : st === "highlight" ? 5.5 : 2.4 + (node.val ?? 1) * 0.7;
          if (hovered) r += 2;
          const x = node.x ?? 0;
          const y = node.y ?? 0;
          // glow for highlighted or hovered nodes
          if (st !== "dim" || hovered) {
            ctx.beginPath();
            ctx.arc(x, y, r + 3, 0, 2 * Math.PI);
            ctx.fillStyle = st === "primary" ? "rgba(245,158,11,0.18)" : st === "highlight" ? "rgba(124,108,240,0.18)" : "rgba(15,23,42,0.12)";
            ctx.fill();
          }
          ctx.beginPath();
          ctx.arc(x, y, r, 0, 2 * Math.PI);
          ctx.fillStyle = hovered && st === "dim" ? "#8b90a0" : NODE[st];
          ctx.globalAlpha = st === "dim" && !hovered ? 0.9 : 1;
          ctx.fill();
          ctx.globalAlpha = 1;
          // labels: always for highlight/primary, and for the hovered node
          if ((st !== "dim" || hovered) && node.label) {
            const fontSize = Math.max(4, (hovered ? 12 : 11) / scale);
            ctx.font = `600 ${fontSize}px Inter, ui-sans-serif, sans-serif`;
            ctx.textAlign = "left";
            ctx.textBaseline = "middle";
            const tx = x + r + 3;
            ctx.lineWidth = Math.max(2, 3.5 / scale);
            ctx.strokeStyle = "rgba(255,255,255,0.97)";
            ctx.strokeText(node.label, tx, y);
            ctx.fillStyle = "#0f172a";
            ctx.fillText(node.label, tx, y);
          }
        }}
        linkDirectionalParticles={0}
      />
    </div>
  );
}
