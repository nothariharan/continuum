"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { TopNav } from "@/components/ui/TopNav";
import { Footer } from "@/components/ui/Footer";
import { GraphCanvas, EntityCard } from "@/components/ui/GraphCanvas";
import { AnimatedBackground } from "@/components/ui/AnimatedBackground";
import { DEMO_GRAPH } from "@/data/demo-script";
import { exportGraph, isApiAvailable } from "@/lib/api";
import type { GraphExport, GraphNode } from "@/lib/contracts";

const AVAILABLE_ENTITIES = [
  { id: "account:acme", name: "Acme Account", type: "Account" },
  { id: "person:priya", name: "Priya Sharma", type: "Person" },
  { id: "person:morgan", name: "Morgan Reed", type: "Person" },
  { id: "person:sarah", name: "Sarah Chen", type: "Person" },
];

function GraphPageInner() {
  const params = useSearchParams();
  const initialEntity = params.get("entity") ?? "account:acme";
  const [currentEntity, setCurrentEntity] = useState<string>(initialEntity);
  const [graph, setGraph] = useState<GraphExport>(DEMO_GRAPH);
  const [selected, setSelected] = useState<GraphNode | null>(null);
  const [sourceFilter, setSourceFilter] = useState<string>("all");
  const [live, setLive] = useState(false);

  useEffect(() => {
    isApiAvailable().then(async (ok) => {
      setLive(ok);
      if (!ok) return;
      try {
        const payload = await exportGraph(currentEntity);
        if (payload.nodes.length) {
          setGraph(payload);
          setSelected(payload.nodes.find((n) => n.id === currentEntity) ?? payload.nodes[0]);
        }
      } catch {
        setGraph(DEMO_GRAPH);
      }
    });
  }, [currentEntity]);

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
    <div className="min-h-screen bg-[var(--paper)] text-[var(--charcoal)] relative">
      <AnimatedBackground variant="graph" />
      <div className="relative z-10">
        <TopNav />

        <main className="mx-auto max-w-7xl px-6 py-12">
          {/* Header Bar */}
          <div className="flex flex-wrap items-end justify-between gap-4 border-b border-black/[0.08] pb-6">
            <div>
              <div className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-[var(--purple)] animate-pulse" />
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--charcoal-muted)]">
                  Spatial Knowledge Graph Explorer
                </p>
              </div>
              <h1 className="mt-2 font-serif text-3xl md:text-5xl text-[var(--charcoal)] tracking-tight">
                Enterprise State Topology
              </h1>
              <p className="mt-1 text-xs text-[var(--charcoal-muted)] leading-relaxed">
                Interactive structural reasoning executed directly inside the HydraDB graph substrate.
              </p>
            </div>

            <div className="flex items-center gap-3">
              <span className="rounded-full bg-white border border-black/[0.08] px-3.5 py-1 font-mono text-xs text-[var(--charcoal-muted)] shadow-2xs">
                Status: {live ? "Connected to HydraDB" : "Deterministic Engine"}
              </span>
              <Link
                href="/"
                className="rounded-full border border-black/[0.08] bg-white px-4 py-1.5 text-xs font-medium text-[var(--charcoal)] hover:bg-[#faf8f5] shadow-xs"
              >
                ← Back to Overview
              </Link>
            </div>
          </div>

          {/* Entity Switcher & Filter Pills */}
          <div className="mt-6 flex flex-wrap items-center justify-between gap-4">
            {/* Entity Selector */}
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs text-[var(--charcoal-muted)] mr-1 font-medium">Focus Entity:</span>
              {AVAILABLE_ENTITIES.map((ent) => (
                <button
                  key={ent.id}
                  type="button"
                  onClick={() => setCurrentEntity(ent.id)}
                  className={`rounded-full border px-3.5 py-1 text-xs font-medium transition-all ${
                    currentEntity === ent.id
                      ? "border-[var(--purple)] bg-[var(--purple-soft)] text-[var(--purple)] shadow-xs"
                      : "border-black/[0.08] bg-white text-[var(--charcoal-muted)] hover:border-black/20 hover:text-[var(--charcoal)]"
                  }`}
                >
                  {ent.name}
                </button>
              ))}
            </div>

            {/* Source Filter */}
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs text-[var(--charcoal-muted)] mr-1 font-medium">Source Filter:</span>
              {[
                { id: "all", label: "All Sources" },
                { id: "slack", label: "Slack" },
                { id: "gmail", label: "Gmail" },
                { id: "linear", label: "Linear" },
              ].map((f) => (
                <button
                  key={f.id}
                  type="button"
                  onClick={() => setSourceFilter(f.id)}
                  className={`rounded-full border px-3 py-1 text-xs font-medium transition-all ${
                    sourceFilter === f.id
                      ? "border-sky-400 bg-sky-50 text-sky-700 font-semibold"
                      : "border-black/[0.08] bg-white text-[var(--charcoal-muted)] hover:border-black/20 hover:text-[var(--charcoal)]"
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>
          </div>

          {/* Spatial Canvas and Inspector Layout */}
          <div className="mt-8 grid gap-6 lg:grid-cols-[1fr_360px]">
            <GraphCanvas
              graph={filteredGraph}
              selectedId={selected?.id ?? currentEntity}
              onSelect={setSelected}
            />
            <div className="space-y-4">
              <EntityCard node={selected} />
              <div className="rounded-3xl border border-black/[0.08] bg-white p-6 text-xs text-[var(--charcoal-muted)] shadow-xs space-y-3">
                <p className="font-semibold text-[var(--charcoal)]">HydraDB Native Graph Execution</p>
                <p className="leading-relaxed">
                  Graph traversals are executed natively inside HydraDB. Graph structures are never
                  pulled into raw Python or flattened for heuristic similarity search.
                </p>
                <div className="border-t border-black/[0.06] pt-3 font-mono text-[11px] space-y-1 text-[var(--charcoal-body)]">
                  <p>Depth: 2 hops</p>
                  <p>Traversed Nodes: {filteredGraph.nodes.length}</p>
                  <p>Edges: {filteredGraph.edges.length}</p>
                </div>
              </div>
            </div>
          </div>
        </main>
        <Footer />
      </div>
    </div>
  );
}

export default function GraphPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[var(--paper)]" />}>
      <GraphPageInner />
    </Suspense>
  );
}
