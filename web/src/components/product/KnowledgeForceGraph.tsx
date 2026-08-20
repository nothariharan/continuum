"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import dynamic from "next/dynamic";

// react-force-graph-2d is canvas/DOM-only — load client-side.
const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false });

export type GState = "dim" | "highlight" | "primary";
export type GNode = { id: string; label?: string; group?: string; val?: number; state?: GState };
export type GLink = { source: string; target: string; state?: GState };

const COLORS: Record<GState, string> = {
  dim: "#3b3f4a",
  highlight: "#f472d0", // pink — relevant cluster
  primary: "#f59e0b", // orange — primary path
};
const LINK_COLORS: Record<GState, string> = {
  dim: "rgba(120,124,140,0.16)",
  highlight: "rgba(232,121,249,0.75)",
  primary: "rgba(245,158,11,0.85)",
};

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
  const fgRef = useRef<{ d3Force: (name: string) => { strength?: (n: number) => void; distance?: (n: number) => void } | undefined } | null>(null);
  const [width, setWidth] = useState(600);

  useEffect(() => {
    const measure = () => {
      if (wrapRef.current) setWidth(wrapRef.current.clientWidth);
    };
    measure();
    const ro = new ResizeObserver(measure);
    if (wrapRef.current) ro.observe(wrapRef.current);
    return () => ro.disconnect();
  }, []);

  // Tune forces for an organic, clustered (Obsidian-like) layout.
  useEffect(() => {
    const fg = fgRef.current;
    if (!fg) return;
    try {
      fg.d3Force("charge")?.strength?.(-38);
      fg.d3Force("link")?.distance?.(26);
    } catch {
      /* forces not ready yet */
    }
  }, [nodes, links]);

  const data = useMemo(() => ({ nodes: nodes.map((n) => ({ ...n })), links: links.map((l) => ({ ...l })) }), [nodes, links]);

  return (
    <div ref={wrapRef} className="w-full overflow-hidden rounded-3xl" style={{ height, background: "#0a0e1a" }}>
      {/* @ts-expect-error dynamic import loses generic typing */}
      <ForceGraph2D
        ref={fgRef}
        width={width}
        height={height}
        graphData={data}
        backgroundColor="#0a0e1a"
        cooldownTicks={120}
        d3VelocityDecay={0.28}
        nodeRelSize={4}
        nodeCanvasObject={(node: GNode & { x?: number; y?: number }, ctx: CanvasRenderingContext2D, scale: number) => {
          const st = node.state ?? "dim";
          const base = st === "primary" ? 6 : st === "highlight" ? 4.5 : 1.6 + (node.val ?? 1) * 0.9;
          ctx.beginPath();
          ctx.arc(node.x ?? 0, node.y ?? 0, base, 0, 2 * Math.PI);
          ctx.fillStyle = COLORS[st];
          ctx.fill();
          if (st !== "dim" && node.label) {
            const fontSize = Math.max(3, 11 / scale);
            ctx.font = `600 ${fontSize}px Inter, ui-sans-serif, sans-serif`;
            ctx.fillStyle = "#fff";
            ctx.textAlign = "left";
            ctx.textBaseline = "middle";
            ctx.fillText(node.label, (node.x ?? 0) + base + 2, node.y ?? 0);
          }
        }}
        linkColor={(l: GLink) => LINK_COLORS[l.state ?? "dim"]}
        linkWidth={(l: GLink) => (l.state === "primary" ? 1.8 : l.state === "highlight" ? 1.3 : 0.4)}
        linkDirectionalParticles={0}
      />
    </div>
  );
}
