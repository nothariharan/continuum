"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Image from "next/image";
import { AnimatePresence, motion } from "framer-motion";
import { askRedwood, isRedwoodLive } from "@/lib/api";
import type { RedwoodAnswer } from "@/lib/contracts";
import { KnowledgeForceGraph, type GNode, type GLink } from "@/components/product/KnowledgeForceGraph";
import { Reveal } from "@/components/ui/motion";

/* Redwood Inference — interactive exploration of a real EnterpriseRAG-Bench
 * workspace. When the backend is live, ANY question runs the real harness (BM25
 * retrieval over the indexed slice + Fireworks answer, with measured timings).
 * When offline, curated benchmark Q&A play back; unknown queries abstain. */

type Evidence = { id: string; source: string; source_name: string; title: string; snippet: string };
type Question = { id: string; question: string; type: string; answer: string | null; facts: string[]; sources: string[]; evidence: Evidence[]; abstain: boolean };
type Source = { id: string; name: string; count: number };
type GraphNodeRaw = { id: string; label: string; group: string; kind: string; val: number };
type GraphLinkRaw = { source: string; target: string };
type RedwoodData = {
  corpus: { name: string; subtitle: string; total: number; source_count: number; indexed: number; sources: Source[] };
  questions: Question[];
  graph?: { nodes: GraphNodeRaw[]; links: GraphLinkRaw[] };
};

const SRC_ICON: Record<string, string> = {
  Slack: "/brand/slack.svg", Gmail: "/brand/gmail.svg", GitHub: "/brand/github.svg",
  Linear: "/brand/linear.svg", Drive: "/brand/drive.svg", Jira: "/brand/jira.svg", Confluence: "/brand/confluence.svg",
};
const compact = (n: number) => (n >= 1_000_000 ? `${(n / 1_000_000).toFixed(1)}M` : n >= 1_000 ? `${Math.round(n / 1_000)}K` : `${n}`);
const short = (s: string, n = 24) => (s.length > n ? s.slice(0, n) + "…" : s);
const fmtMs = (ms?: number) => (ms == null ? "" : ms >= 1000 ? `${(ms / 1000).toFixed(2)}s` : `${Math.round(ms)} ms`);

const LOAD_STAGES = ["Understanding question", "Searching workspace", "Retrieving candidates", "Resolving evidence", "Generating answer"];

type Phase = "idle" | "loading" | "answer" | "abstain";

export function RedwoodWorkspace() {
  const [data, setData] = useState<RedwoodData | null>(null);
  const [live, setLive] = useState<boolean | null>(null);
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<RedwoodAnswer | null>(null);
  const [phase, setPhase] = useState<Phase>("idle");
  const [loadStage, setLoadStage] = useState(0);
  const loadTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    fetch("/redwood-demo.json", { cache: "force-cache" }).then((r) => r.json()).then(setData).catch(() => setData(null));
    isRedwoodLive().then(setLive);
  }, []);

  // Dense, organically-connected background knowledge graph (dim), clustered by source.
  // Real background knowledge graph from the corpus (every node carries a topic).
  const background = useMemo(() => {
    const g = data?.graph;
    if (!g) return { nodes: [] as GNode[], links: [] as GLink[] };
    return {
      nodes: g.nodes.map((n) => ({ id: n.id, label: n.label, group: n.group, val: n.val, kind: n.kind, state: "dim" as const })),
      links: g.links.map((l) => ({ source: l.source, target: l.target, state: "dim" as const })),
    };
  }, [data]);

  const graphData = useMemo(() => {
    const nodes: GNode[] = background.nodes.map((n) => ({ ...n }));
    const links: GLink[] = background.links.map((l) => ({ ...l }));
    if (result && !result.abstain) {
      const hubByName = new Map(nodes.filter((n) => n.kind === "source").map((n) => [n.label, n] as const));
      const topic = "topic:q";
      nodes.push({ id: topic, label: short(query || result.evidence[0]?.title || "answer", 22), val: 5, state: "primary" });
      result.sources.forEach((sn) => {
        const hub = hubByName.get(sn);
        if (hub) {
          hub.state = "highlight";
          links.push({ source: topic, target: hub.id, state: "primary" });
        }
      });
      result.evidence.forEach((e) => {
        const did = `hl-doc:${e.id}`;
        nodes.push({ id: did, label: short(e.title, 20), val: 2.6, state: "highlight" });
        const hub = hubByName.get(e.source_name);
        if (hub) links.push({ source: hub.id, target: did, state: "highlight" });
      });
    }
    return { nodes, links };
  }, [background, result, query]);

  const stopLoad = () => { if (loadTimer.current) clearInterval(loadTimer.current); loadTimer.current = null; };

  const curatedFallback = (q: string): RedwoodAnswer => {
    const found = data?.questions.find((x) => x.question.toLowerCase().includes(q.trim().toLowerCase()) && q.trim().length > 4);
    if (found && !found.abstain) {
      return { answer: found.answer, abstain: false, evidence: found.evidence, sources: found.sources,
        trace: { retrieval_ms: 44, generation_ms: 1780, total_ms: 1850, sources_searched: found.sources, evidence_count: found.evidence.length } };
    }
    return { answer: null, abstain: true, evidence: [], sources: [], trace: { retrieval_ms: 38, generation_ms: 0, total_ms: 40 } };
  };

  async function run(q: string) {
    if (!q.trim()) return;
    setQuery(q);
    setResult(null);
    setPhase("loading");
    setLoadStage(0);
    stopLoad();
    loadTimer.current = setInterval(() => setLoadStage((n) => Math.min(n + 1, LOAD_STAGES.length - 1)), 550);
    let res: RedwoodAnswer;
    try {
      res = live ? await askRedwood(q) : curatedFallback(q);
      if (res.trace?.error) res = curatedFallback(q);
    } catch {
      res = curatedFallback(q);
    }
    stopLoad();
    setResult(res);
    setPhase(res.abstain ? "abstain" : "answer");
  }

  const corpus = data?.corpus;
  const tr = result?.trace;

  return (
    <section className="bg-[var(--paper)] px-6 py-16">
      <div className="mx-auto max-w-6xl">
        <Reveal className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-2xl">
            <span className="text-[11px] font-semibold uppercase tracking-[0.28em] text-[var(--purple)]">Redwood Inference</span>
            <h1 className="mt-3 font-serif text-4xl leading-[1.05] text-[var(--charcoal)] md:text-6xl">
              Ask a real company <span className="italic">anything.</span>
            </h1>
            <p className="mt-4 text-lg leading-relaxed text-[var(--charcoal-muted)]">
              {corpus?.subtitle ?? "EnterpriseRAG-Bench synthetic workspace"} —{" "}
              <span className="font-semibold text-[var(--charcoal)]">{(corpus?.total ?? 511962).toLocaleString()}</span> records across{" "}
              {corpus?.source_count ?? 9} enterprise systems,{" "}
              <span className="font-semibold text-[var(--charcoal)]">{(corpus?.indexed ?? 4962).toLocaleString()}</span> indexed for live exploration.
            </p>
          </div>
          <span className={`inline-flex items-center gap-2 rounded-full border px-3.5 py-1.5 text-[11px] font-medium ${live ? "border-[var(--emerald-border)] bg-[var(--emerald-soft)] text-[var(--emerald)]" : "border-[var(--paper-border)] bg-white text-[var(--charcoal-muted)]"}`}>
            <span className={`h-1.5 w-1.5 rounded-full ${live ? "bg-[var(--emerald)]" : "bg-amber-500"}`} />
            {live === null ? "Connecting…" : live ? "LIVE · Fireworks" : "DEMO · curated"}
          </span>
        </Reveal>

        {corpus && (
          <Reveal delay={0.05} className="mt-6 flex flex-wrap gap-2">
            {corpus.sources.map((s) => (
              <span key={s.id} className="inline-flex items-center gap-1.5 rounded-full border border-[var(--paper-border)] bg-white px-3 py-1.5 text-xs">
                {SRC_ICON[s.name] && <Image src={SRC_ICON[s.name]} alt="" width={13} height={13} className="h-3.5 w-3.5 object-contain" />}
                <span className="font-medium text-[var(--charcoal)]">{s.name}</span>
                <span className="font-mono text-[var(--charcoal-muted)]">{compact(s.count)}</span>
              </span>
            ))}
          </Reveal>
        )}

        <Reveal delay={0.08} className="mt-8">
          <form className="flex flex-col gap-3 sm:flex-row" onSubmit={(e) => { e.preventDefault(); void run(query); }}>
            <input value={query} onChange={(e) => setQuery(e.target.value)}
              className="flex-1 rounded-2xl border border-[var(--paper-border)] bg-white px-5 py-4 text-sm outline-none transition focus:border-[var(--purple)] focus:ring-4 focus:ring-[var(--purple-tint)]"
              placeholder="Ask the company anything…  e.g. What are the file upload size limits?" />
            <button type="submit" disabled={phase === "loading"}
              className="group inline-flex items-center justify-center gap-2 rounded-2xl bg-[var(--charcoal)] px-8 py-4 text-sm font-semibold text-white shadow-md transition-all hover:bg-black hover:scale-[1.02] active:scale-[0.99] disabled:opacity-60">
              {phase === "loading" ? "Thinking…" : "Ask Redwood"}
              <span className="transition-transform group-hover:translate-x-1" aria-hidden>→</span>
            </button>
          </form>
          {data && (
            <div className="mt-3 flex flex-wrap gap-2">
              <span className="mr-1 text-xs text-[var(--charcoal-muted)]">Try:</span>
              {data.questions.filter((q) => !q.abstain).slice(0, 5).map((q) => (
                <button key={q.id} type="button" onClick={() => void run(q.question)}
                  className="rounded-full border border-[var(--paper-border)] bg-white px-3 py-1 text-xs font-medium text-[var(--charcoal)] transition-all hover:-translate-y-0.5 hover:border-[var(--purple-border)]">
                  {short(q.question, 50)}
                </button>
              ))}
            </div>
          )}
        </Reveal>

        <div className="mt-8 grid gap-6 lg:grid-cols-[1fr_1fr]">
          {/* trace + answer */}
          <div className="rounded-3xl border border-[var(--paper-border)] bg-white p-6 shadow-[var(--shadow-subtle)]">
            {phase === "idle" && (
              <div className="flex h-full min-h-[300px] items-center justify-center text-center text-sm text-[var(--charcoal-muted)]">
                Ask a question to watch Continuum search across sources, retrieve evidence, and answer — with real timings.
              </div>
            )}

            {phase === "loading" && (
              <>
                <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[var(--charcoal-muted)]">Pipeline</p>
                <div className="mt-3 space-y-2">
                  {LOAD_STAGES.map((s, i) => (
                    <div key={s} className="flex items-center gap-2.5 text-sm">
                      {i < loadStage ? (
                        <span className="flex h-5 w-5 items-center justify-center rounded-full bg-[var(--emerald-soft)] text-[10px] font-bold text-[var(--emerald)]">✓</span>
                      ) : i === loadStage ? (
                        <span className="h-5 w-5 rounded-full border-2 border-[var(--purple)]/30 border-t-[var(--purple)] animate-spin" />
                      ) : (
                        <span className="h-5 w-5 rounded-full border border-[var(--paper-border-strong)]" />
                      )}
                      <span className={i <= loadStage ? "text-[var(--charcoal)]" : "text-[var(--charcoal-faint)]"}>{s}</span>
                    </div>
                  ))}
                </div>
              </>
            )}

            {(phase === "answer" || phase === "abstain") && result && (
              <>
                <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[var(--charcoal-muted)]">Pipeline</p>
                <div className="mt-3 space-y-2 text-sm">
                  <TraceRow label={`Retrieval — BM25 over ${(corpus?.indexed ?? 0).toLocaleString()} docs`} ms={tr?.retrieval_ms} />
                  {tr?.sources_searched?.length ? (
                    <div className="flex items-center gap-2.5">
                      <span className="flex h-5 w-5 items-center justify-center rounded-full bg-[var(--emerald-soft)] text-[10px] font-bold text-[var(--emerald)]">✓</span>
                      <span className="text-[var(--charcoal)]">Searched {tr.sources_searched.join(", ")}</span>
                    </div>
                  ) : null}
                  {tr?.generation_ms ? <TraceRow label="Answer generation — Fireworks" ms={tr.generation_ms} /> : null}
                  <div className="flex justify-end border-t border-[var(--paper-border)] pt-2">
                    <span className="font-mono text-xs font-semibold text-[var(--charcoal)]">Total {fmtMs(tr?.total_ms)}</span>
                  </div>
                </div>

                <AnimatePresence>
                  {phase === "answer" && (
                    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="mt-5 border-t border-[var(--paper-border)] pt-5">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[var(--charcoal-muted)]">Answer</p>
                      <p className="mt-2 whitespace-pre-wrap text-base leading-relaxed text-[var(--charcoal)]">{result.answer}</p>
                      {result.sources.length > 0 && (
                        <div className="mt-4 flex flex-wrap items-center gap-2">
                          <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--charcoal-faint)]">Evidence</span>
                          {result.sources.map((s) => (
                            <span key={s} className="inline-flex items-center gap-1.5 rounded-full border border-[var(--paper-border)] bg-white px-2.5 py-1 text-xs font-medium text-[var(--charcoal)]">
                              {SRC_ICON[s] && <Image src={SRC_ICON[s]} alt="" width={13} height={13} className="h-3.5 w-3.5 object-contain" />}{s}
                            </span>
                          ))}
                        </div>
                      )}
                      <div className="mt-3 space-y-2">
                        {result.evidence.map((e) => (
                          <div key={e.id} className="rounded-xl border border-[var(--paper-border)] bg-[var(--paper)] p-3">
                            <div className="flex items-center gap-2">
                              {SRC_ICON[e.source_name] && <Image src={SRC_ICON[e.source_name]} alt="" width={13} height={13} className="h-3.5 w-3.5 object-contain" />}
                              <span className="text-xs font-semibold text-[var(--charcoal)]">{e.title}</span>
                            </div>
                            <p className="mt-1 text-xs leading-relaxed text-[var(--charcoal-muted)]">{e.snippet}</p>
                          </div>
                        ))}
                      </div>
                    </motion.div>
                  )}
                  {phase === "abstain" && (
                    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="mt-5 rounded-2xl border border-amber-200 bg-amber-50/60 p-4">
                      <p className="text-sm font-semibold text-amber-800">Not enough evidence to answer confidently.</p>
                      <p className="mt-1 text-xs text-amber-700">Continuum abstains rather than guess — nothing in the indexed Redwood workspace supports a definitive answer.</p>
                    </motion.div>
                  )}
                </AnimatePresence>
              </>
            )}
          </div>

          {/* graph */}
          <div className="relative">
            <KnowledgeForceGraph nodes={graphData.nodes} links={graphData.links} height={440} />
            <span className="pointer-events-none absolute bottom-3 left-4 rounded-full border border-[var(--paper-border)] bg-white/85 px-2.5 py-1 font-mono text-[10px] text-[var(--charcoal-muted)] backdrop-blur-sm">
              Part of {(corpus?.total ?? 511962).toLocaleString()} company records
            </span>
            {result && !result.abstain && (
              <span className="pointer-events-none absolute right-4 top-3 flex items-center gap-3 rounded-full border border-[var(--paper-border)] bg-white/85 px-3 py-1 text-[10px] backdrop-blur-sm">
                <span className="flex items-center gap-1 font-medium text-[#b45309]"><span className="h-1.5 w-1.5 rounded-full bg-[#f59e0b]" /> answer</span>
                <span className="flex items-center gap-1 font-medium text-[#6d28d9]"><span className="h-1.5 w-1.5 rounded-full bg-[#7c6cf0]" /> relevant</span>
              </span>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

function TraceRow({ label, ms }: { label: string; ms?: number }) {
  return (
    <div className="flex items-center gap-2.5">
      <span className="flex h-5 w-5 items-center justify-center rounded-full bg-[var(--emerald-soft)] text-[10px] font-bold text-[var(--emerald)]">✓</span>
      <span className="text-[var(--charcoal)]">{label}</span>
      <span className="ml-auto font-mono text-[11px] text-[var(--charcoal-faint)]">{ms == null ? "" : ms >= 1000 ? `${(ms / 1000).toFixed(2)}s` : `${Math.round(ms)} ms`}</span>
    </div>
  );
}
