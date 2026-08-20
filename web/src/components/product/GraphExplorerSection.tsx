"use client";

import { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { GraphCanvas, EntityCard } from "@/components/ui/GraphCanvas";
import { DEMO_GRAPH } from "@/data/demo-script";
import { exportGraph, isApiAvailable } from "@/lib/api";
import type { GraphExport, GraphNode } from "@/lib/contracts";
import { Reveal } from "@/components/ui/motion";

export function GraphExplorerSection() {
  const [graph, setGraph] = useState<GraphExport>(DEMO_GRAPH);
  const [selected, setSelected] = useState<GraphNode | null>(
    DEMO_GRAPH.nodes.find((n) => n.id === DEMO_GRAPH.entity) ?? null,
  );
  const [sourceFilter, setSourceFilter] = useState<string>("all");
  const [live, setLive] = useState(false);

  useEffect(() => {
    isApiAvailable().then(async (ok) => {
      setLive(ok);
      if (ok) {
        try {
          const payload = await exportGraph("account:acme");
          if (payload.nodes.length) setGraph(payload);
        } catch {
          setGraph(DEMO_GRAPH);
        }
      }
    });
  }, []);

  // Filter nodes according to active source filter
  const filteredGraph = useMemo(() => {
    if (sourceFilter === "all") return graph;
    const matchingNodes = graph.nodes.filter(
      (n) => n.id === graph.entity || !n.source || n.source.toLowerCase() === sourceFilter.toLowerCase(),
    );
    const nodeIds = new Set(matchingNodes.map((n) => n.id));
    const matchingEdges = graph.edges.filter(
      (e) => nodeIds.has(e.source) && nodeIds.has(e.target),
    );
    return {
      entity: graph.entity,
      nodes: matchingNodes,
      edges: matchingEdges,
    };
  }, [graph, sourceFilter]);

  return (
    <section id="graph" className="relative overflow-hidden bg-[var(--paper)] px-6 py-28 text-[var(--charcoal)]">
      <div className="relative mx-auto max-w-6xl">
        <Reveal className="mb-10 flex flex-wrap items-end justify-between gap-6">
          <div>
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-[var(--purple)] animate-pulse" />
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--charcoal-muted)]">
                Knowledge Graph
              </p>
            </div>
            <h2 className="mt-3 font-serif text-4xl text-[var(--charcoal)] md:text-6xl tracking-tight">
              Explore company state spatially.
            </h2>
            <p className="mt-2 text-sm text-[var(--charcoal-muted)] max-w-xl leading-relaxed">
              Inspect canonical entities, historical ownership edges, and the source artifacts that anchor each relationship.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <span className="rounded-full border border-black/[0.08] bg-white px-3.5 py-1 font-mono text-[11px] text-[var(--charcoal-muted)] shadow-2xs">
              {live ? "Live HydraDB Export" : "Spatial Topology"}
            </span>
            <Link
              href="/graph?entity=account:acme"
              className="inline-flex items-center gap-1.5 rounded-full border border-black/[0.08] bg-white px-4 py-2 text-xs font-semibold text-[var(--charcoal)] shadow-xs transition hover:bg-[#faf8f5] hover:border-black/20"
            >
              <span>Full Screen Graph</span>
              <span>↗</span>
            </Link>
          </div>
        </Reveal>

        {/* Filter Controls Bar */}
        <Reveal delay={0.06} className="mb-6 flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs text-[var(--charcoal-muted)] mr-1 font-medium">Source Filter:</span>
            {[
              { id: "all", label: "All Connections" },
              { id: "slack", label: "Slack" },
              { id: "gmail", label: "Gmail" },
              { id: "linear", label: "Linear" },
            ].map((f) => (
              <button
                key={f.id}
                type="button"
                onClick={() => setSourceFilter(f.id)}
                className={`rounded-full border px-3.5 py-1 text-xs font-medium transition-all ${
                  sourceFilter === f.id
                    ? "border-[var(--purple)] bg-[var(--purple-soft)] text-[var(--purple)] shadow-xs"
                    : "border-black/[0.08] bg-white text-[var(--charcoal-muted)] hover:border-black/20 hover:text-[var(--charcoal)]"
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2 text-xs text-[var(--charcoal-muted)] font-mono">
            <span className="h-2 w-2 rounded-full bg-emerald-500" />
            <span>Target: account:acme</span>
          </div>
        </Reveal>

        {/* Spatial Graph & Side Inspector */}
        <Reveal delay={0.1}>
          <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
            <GraphCanvas graph={filteredGraph} selectedId={selected?.id} onSelect={setSelected} />
            <div className="space-y-4">
              <EntityCard node={selected} />
              <div className="rounded-3xl border border-black/[0.08] bg-white p-6 text-xs text-[var(--charcoal-muted)] shadow-xs">
                <p className="font-semibold text-[var(--charcoal)] mb-2">Graph Navigation Tips</p>
                <ul className="space-y-1.5 list-disc list-inside text-[var(--charcoal-body)] leading-relaxed">
                  <li>Scroll to zoom in and out</li>
                  <li>Click & drag to pan the canvas</li>
                  <li>Click any node or edge to inspect claims</li>
                </ul>
              </div>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
