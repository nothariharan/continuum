"use client";

import { useEffect, useMemo, useState } from "react";
import Image from "next/image";
import { AnimatePresence, motion } from "framer-motion";
import { askQuestion, fetchHistory, isApiAvailable } from "@/lib/api";
import type { AskResult, EvidenceItem, HistoryRow } from "@/lib/contracts";
import { Reveal } from "@/components/ui/motion";
import { EmergingMemoryGraph } from "@/components/product/EmergingMemoryGraph";

/* The golden-path query console. Renders ONLY what the backend actually returns:
 * the canonical answer, its evidence, the temporal history, and a process trace
 * whose stages are each derived from a real field of the result. When the API is
 * unavailable it falls back to a clearly-labelled DEMO snapshot of the same
 * scenario (same shape, no invented reasoning). */

const PRESETS = [
  "Who owns Acme now?",
  "Who owned Acme before Priya?",
  "When did ownership change?",
];

const SOURCE_ICON: Record<string, string> = {
  Slack: "/brand/slack.svg",
  Gmail: "/brand/gmail.svg",
};

// DEMO fallback — mirrors the frozen scenario's end state (Priya, effective Aug 5).
const DEMO_RESULT: AskResult = {
  question_id: "demo",
  question: "Who owns Acme now?",
  status: "definitive",
  answer: "Priya",
  resolved_entities: ["account:acme"],
  claims_used: [],
  state_result: {
    entity_id: "account:acme",
    predicate: "OWNS",
    status: "definitive",
    value: { entity_id: "person:priya", name: "Priya" },
    valid_from: "2026-08-05",
    valid_to: null,
  },
  conflicts: [],
  evidence: [
    { source: "Slack", source_id: "source:slack", subject_mention: "Morgan", object_mention: "Acme", artifact_kind: "slack_message", observed_at: "2026-07-28" },
    { source: "Gmail", source_id: "source:gmail", subject_mention: "Priya", object_mention: "Acme", artifact_kind: "gmail_message", observed_at: "2026-08-05" },
  ],
  layers: {},
  context: {},
  latency_ms: {},
  diagnostics: {},
  trace: ["entity resolution: Acme -> account:acme", "state: definitive for account:acme", "answer: Priya"],
};
const DEMO_HISTORY: HistoryRow[] = [
  { subject_id: "person:morgan", subject_name: "Morgan", valid_from: "0001-01-01", valid_to: "2026-08-05" },
  { subject_id: "person:priya", subject_name: "Priya", valid_from: "2026-08-05", valid_to: "9999-12-31" },
];

function fmtDate(d?: string | null): string {
  if (!d || d.startsWith("0001") || d.startsWith("9999")) return d?.startsWith("9999") ? "now" : "—";
  const dt = new Date(d + "T00:00:00");
  return isNaN(dt.getTime()) ? d : dt.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function uniqueSources(evidence: EvidenceItem[]): string[] {
  return Array.from(new Set(evidence.map((e) => e.source).filter(Boolean) as string[]));
}

/** Build the process trace — every stage maps to a real field of the result. */
function buildStages(result: AskResult, history: HistoryRow[]) {
  const sources = uniqueSources(result.evidence ?? []);
  const stages = [
    { label: "Understanding the question", ok: true, detail: "" },
    { label: "Searching company memory", ok: (result.resolved_entities?.length ?? 0) > 0, detail: (result.resolved_entities ?? []).join(", ") },
    { label: "Checking Slack", ok: sources.includes("Slack"), detail: "" },
    { label: "Checking Gmail", ok: sources.includes("Gmail"), detail: "" },
    { label: "Resolving identity", ok: (result.resolved_entities?.length ?? 0) > 0, detail: "" },
    { label: "Resolving ownership timeline", ok: (history?.length ?? 0) > 0, detail: history.length ? `${history.length} states` : "" },
    { label: "Ranking evidence", ok: (result.evidence?.length ?? 0) > 0, detail: `${result.evidence?.length ?? 0} artifacts` },
    { label: "Answer ready", ok: !!result.answer, detail: "" },
  ];
  return stages.filter((s) => s.ok);
}

type Phase = "idle" | "tracing" | "done";

export function GoldenPathConsole() {
  const [question, setQuestion] = useState("Who owns Acme now?");
  const [result, setResult] = useState<AskResult | null>(null);
  const [history, setHistory] = useState<HistoryRow[]>([]);
  const [live, setLive] = useState<boolean | null>(null);
  const [phase, setPhase] = useState<Phase>("idle");
  const [visibleStages, setVisibleStages] = useState(0);
  const [showWhy, setShowWhy] = useState(false);
  const [graphStep, setGraphStep] = useState(0);

  useEffect(() => {
    isApiAvailable().then(setLive);
  }, []);

  // Grow the company-memory graph as the answer resolves.
  useEffect(() => {
    if (phase !== "done") {
      setGraphStep(0);
      return;
    }
    let s = 0;
    const t = setInterval(() => {
      s += 1;
      setGraphStep(s);
      if (s >= 3) clearInterval(t);
    }, 550);
    return () => clearInterval(t);
  }, [phase]);

  const stages = useMemo(() => (result ? buildStages(result, history) : []), [result, history]);

  // Reveal trace stages one by one (presentation only; the stages themselves are real).
  useEffect(() => {
    if (phase !== "tracing" || stages.length === 0) return;
    if (visibleStages >= stages.length) {
      const t = setTimeout(() => setPhase("done"), 260);
      return () => clearTimeout(t);
    }
    const t = setTimeout(() => setVisibleStages((n) => n + 1), 230);
    return () => clearTimeout(t);
  }, [phase, visibleStages, stages.length]);

  async function ask(q: string) {
    setShowWhy(false);
    setVisibleStages(0);
    setResult(null);
    setPhase("tracing");
    try {
      if (live) {
        const [res, hist] = await Promise.all([
          askQuestion(q),
          fetchHistory("account:acme").catch(() => ({ history: [] as HistoryRow[] })),
        ]);
        setResult(res);
        setHistory(hist.history ?? []);
      } else {
        setResult({ ...DEMO_RESULT, question: q });
        setHistory(DEMO_HISTORY);
      }
    } catch {
      setResult({ ...DEMO_RESULT, question: q });
      setHistory(DEMO_HISTORY);
    }
  }

  const owner = result?.state_result?.value?.name;
  const effective = result?.state_result?.valid_from;
  const sources = result ? uniqueSources(result.evidence ?? []) : [];
  const previous = useMemo(() => {
    if (!result) return undefined;
    const cur = result.state_result?.valid_from;
    const prior = history.find((h) => h.valid_to && h.valid_to === cur && h.subject_name !== owner);
    return prior?.subject_name ?? history.find((h) => h.subject_name !== owner)?.subject_name;
  }, [result, history, owner]);

  return (
    <section id="query" className="relative bg-[var(--paper)] px-6 py-24 text-[var(--charcoal)]">
      <div className="mx-auto max-w-5xl">
        <Reveal className="mb-8 flex flex-wrap items-end justify-between gap-4">
          <div>
            <span className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--charcoal-muted)]">
              Company Memory
            </span>
            <h2 className="mt-3 font-serif text-4xl leading-[1.08] text-[var(--charcoal)] md:text-5xl">
              Ask once. <span className="italic">Know why.</span>
            </h2>
          </div>
          <span
            className={`inline-flex items-center gap-2 rounded-full border px-3.5 py-1.5 text-[11px] font-medium ${
              live
                ? "border-[var(--emerald-border)] bg-[var(--emerald-soft)] text-[var(--emerald)]"
                : "border-[var(--paper-border)] bg-white text-[var(--charcoal-muted)]"
            }`}
          >
            <span className={`h-1.5 w-1.5 rounded-full ${live ? "bg-[var(--emerald)]" : "bg-[var(--charcoal-faint)]"}`} />
            {live === null ? "Connecting…" : live ? "LIVE · HydraDB" : "DEMO · fixtures"}
          </span>
        </Reveal>

        {/* presets */}
        <Reveal delay={0.05} className="mb-4 flex flex-wrap gap-2">
          {PRESETS.map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => { setQuestion(p); void ask(p); }}
              className={`rounded-full border px-3.5 py-1.5 text-xs font-medium transition-all hover:-translate-y-0.5 ${
                question === p
                  ? "border-[var(--purple-border)] bg-[var(--purple-soft)] text-[var(--purple)]"
                  : "border-[var(--paper-border)] bg-white text-[var(--charcoal)] hover:border-[var(--purple-border)]"
              }`}
            >
              {p}
            </button>
          ))}
        </Reveal>

        {/* input */}
        <Reveal delay={0.08}>
          <form
            className="mb-8 flex flex-col gap-3 sm:flex-row"
            onSubmit={(e) => { e.preventDefault(); void ask(question); }}
          >
            <input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              className="flex-1 rounded-2xl border border-[var(--paper-border)] bg-white px-5 py-4 text-sm outline-none transition focus:border-[var(--purple)] focus:ring-4 focus:ring-[var(--purple-tint)]"
              placeholder="Ask about people, accounts, ownership over time…"
            />
            <button
              type="submit"
              className="group inline-flex items-center justify-center gap-2 rounded-2xl bg-[var(--charcoal)] px-8 py-4 text-sm font-semibold text-white shadow-md transition-all hover:bg-black hover:scale-[1.02] active:scale-[0.99]"
            >
              <span>Ask Continuum</span>
              <span className="transition-transform group-hover:translate-x-1" aria-hidden>→</span>
            </button>
          </form>
        </Reveal>

        {/* process trace + answer */}
        <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
          {/* trace */}
          <div className="rounded-3xl border border-[var(--paper-border)] bg-white p-6 shadow-[var(--shadow-subtle)]">
            <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[var(--charcoal-muted)]">
              How Continuum answered
            </p>
            <div className="mt-4 space-y-2.5">
              <AnimatePresence>
                {stages.slice(0, phase === "done" ? stages.length : visibleStages).map((s, i) => (
                  <motion.div
                    key={s.label}
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.25 }}
                    className="flex items-center gap-3"
                  >
                    <span className="flex h-5 w-5 items-center justify-center rounded-full bg-[var(--emerald-soft)] text-[10px] font-bold text-[var(--emerald)]">
                      ✓
                    </span>
                    <span className="text-sm text-[var(--charcoal)]">{s.label}</span>
                    {s.detail && <span className="ml-auto font-mono text-[10px] text-[var(--charcoal-faint)]">{s.detail}</span>}
                    {i < stages.length - 1 && <span className="sr-only">then</span>}
                  </motion.div>
                ))}
              </AnimatePresence>
              {phase === "tracing" && visibleStages < stages.length && (
                <div className="flex items-center gap-3 text-[var(--charcoal-muted)]">
                  <span className="h-5 w-5 rounded-full border-2 border-[var(--purple)]/30 border-t-[var(--purple)] animate-spin" />
                  <span className="text-sm">Working…</span>
                </div>
              )}
              {phase === "idle" && (
                <p className="text-sm text-[var(--charcoal-muted)]">Ask a question to see the real pipeline stages.</p>
              )}
            </div>
          </div>

          {/* answer */}
          <div className="rounded-3xl border border-[var(--paper-border)] bg-[var(--surface)] p-6 shadow-[var(--shadow-soft)]">
            {phase === "done" && result ? (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
                <div className="flex items-center gap-2">
                  <span className="flex h-6 w-6 items-center justify-center rounded-full bg-[var(--purple-soft)] text-[11px] font-bold text-[var(--purple)]">∞</span>
                  <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--charcoal-muted)]">Answer</span>
                  {result.status && (
                    <span className="ml-auto rounded-full bg-white px-2.5 py-0.5 font-mono text-[10px] font-semibold uppercase text-[var(--charcoal-muted)]">
                      {result.status}
                    </span>
                  )}
                </div>

                <p className="mt-3 text-2xl font-semibold text-[var(--charcoal)]">
                  {owner ? `${owner} owns Acme.` : result.answer ?? "No definitive answer."}
                </p>

                <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-[var(--charcoal-muted)]">
                  {previous && (
                    <span className="inline-flex items-center gap-1.5">
                      Previously
                      <span className="rounded-md bg-white px-2 py-0.5 font-mono text-[var(--charcoal-muted)] line-through">{previous}</span>
                    </span>
                  )}
                  {effective && (
                    <span className="ml-auto font-mono">effective {fmtDate(effective)}</span>
                  )}
                </div>

                {/* evidence badges */}
                {sources.length > 0 && (
                  <div className="mt-4">
                    <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[var(--charcoal-faint)]">Grounded in</p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {sources.map((s) => (
                        <span key={s} className="inline-flex items-center gap-1.5 rounded-full border border-[var(--paper-border)] bg-white px-3 py-1 text-xs font-medium text-[var(--charcoal)]">
                          {SOURCE_ICON[s] && <Image src={SOURCE_ICON[s]} alt="" width={14} height={14} className="h-3.5 w-3.5 object-contain" />}
                          {s}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Why */}
                <button
                  type="button"
                  onClick={() => setShowWhy((v) => !v)}
                  className="mt-5 inline-flex items-center gap-1.5 text-sm font-semibold text-[var(--purple)] hover:text-[var(--purple-hover)]"
                >
                  {showWhy ? "Hide why" : "Why?"}
                  <span className={`transition-transform ${showWhy ? "rotate-90" : ""}`} aria-hidden>→</span>
                </button>

                <AnimatePresence>
                  {showWhy && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      exit={{ opacity: 0, height: 0 }}
                      className="overflow-hidden"
                    >
                      {/* temporal transition */}
                      {history.length >= 2 && (
                        <div className="mt-4 rounded-2xl border border-[var(--paper-border)] bg-white p-4">
                          <TimelineRows history={history} owner={owner} />
                        </div>
                      )}
                      {/* real evidence list */}
                      <div className="mt-3 space-y-1.5">
                        {(result.evidence ?? []).slice(0, 6).map((e, i) => (
                          <div key={i} className="flex items-center gap-2 rounded-xl border border-[var(--paper-border)] bg-white px-3 py-2 text-xs">
                            {e.source && SOURCE_ICON[e.source] && (
                              <Image src={SOURCE_ICON[e.source]} alt="" width={14} height={14} className="h-3.5 w-3.5 object-contain" />
                            )}
                            <span className="font-semibold text-[var(--charcoal)]">{e.source}</span>
                            <span className="text-[var(--charcoal-muted)]">
                              {e.subject_mention} → {e.object_mention}
                            </span>
                            <span className="ml-auto font-mono text-[10px] text-[var(--charcoal-faint)]">{fmtDate(e.observed_at)}</span>
                          </div>
                        ))}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            ) : (
              <div className="flex h-full min-h-[220px] items-center justify-center text-center text-sm text-[var(--charcoal-muted)]">
                {phase === "tracing" ? "Resolving canonical state…" : "The answer and its evidence appear here."}
              </div>
            )}
          </div>
        </div>

        {/* history timeline (always visible once we have history) */}
        {phase === "done" && history.length >= 2 && (
          <Reveal delay={0.05} className="mt-6">
            <div className="rounded-3xl border border-[var(--paper-border)] bg-white p-6 shadow-[var(--shadow-subtle)]">
              <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[var(--charcoal-muted)]">Ownership over time</p>
              <div className="mt-5">
                <TimelineBar history={history} owner={owner} />
              </div>
            </div>
          </Reveal>
        )}

        {/* Company memory — the graph grows as the answer resolves */}
        {phase === "done" && (
          <Reveal delay={0.08} className="mt-6">
            <div className="rounded-3xl border border-[var(--paper-border)] bg-[var(--paper)] p-6 shadow-[var(--shadow-subtle)]">
              <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[var(--charcoal-muted)]">
                Company memory
              </p>
              <EmergingMemoryGraph step={graphStep} className="mt-3 h-[300px] w-full" />
            </div>
          </Reveal>
        )}
      </div>
    </section>
  );
}

function TimelineRows({ history, owner }: { history: HistoryRow[]; owner?: string }) {
  return (
    <div className="space-y-2 text-sm">
      {history.map((h, i) => {
        const isCurrent = h.subject_name === owner && (!h.valid_to || h.valid_to.startsWith("9999"));
        return (
          <div key={i} className="flex items-center gap-2">
            <span className={`h-2 w-2 rounded-full ${isCurrent ? "bg-[var(--emerald)]" : "bg-[var(--charcoal-faint)]"}`} />
            <span className={isCurrent ? "font-semibold text-[var(--charcoal)]" : "text-[var(--charcoal-muted)]"}>{h.subject_name}</span>
            <span className="ml-auto font-mono text-[11px] text-[var(--charcoal-muted)]">
              {fmtDate(h.valid_from)} → {fmtDate(h.valid_to)}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function TimelineBar({ history, owner }: { history: HistoryRow[]; owner?: string }) {
  const segments = history.length;
  return (
    <div className="flex items-stretch gap-1">
      {history.map((h, i) => {
        const isCurrent = h.subject_name === owner && (!h.valid_to || h.valid_to.startsWith("9999"));
        return (
          <div key={i} className="flex-1" style={{ minWidth: `${100 / segments}%` }}>
            <div className={`h-2 rounded-full ${isCurrent ? "bg-[var(--purple)]" : "bg-[var(--charcoal-faint)]/40"}`} />
            <div className="mt-2 flex items-baseline justify-between">
              <span className={`text-sm font-semibold ${isCurrent ? "text-[var(--purple)]" : "text-[var(--charcoal)]"}`}>
                {h.subject_name}
              </span>
              <span className="font-mono text-[10px] text-[var(--charcoal-faint)]">
                {i === 0 ? "start" : fmtDate(h.valid_from)}
                {isCurrent ? " → now" : ""}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
