"use client";

import { useEffect, useRef, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { AnimatePresence, motion } from "framer-motion";
import { easeOut } from "@/components/ui/motion";

/* Continuum Cloud — workspace onboarding (UI demo).
 * create workspace -> connect sources -> index -> ready.
 * Fully client-side/mocked: no real OAuth, but it looks and feels like a real
 * "Connect → Index → Ask" flow. */

type Step = "create" | "connect" | "indexing" | "ready";

type Connector = {
  id: string;
  name: string;
  icon: string;
  unit: string;
  total: number;
  totalLabel: string;
};

const CONNECTORS: Connector[] = [
  { id: "slack", name: "Slack", icon: "/brand/slack.svg", unit: "messages", total: 1_200_000, totalLabel: "1.2M" },
  { id: "gmail", name: "Gmail", icon: "/brand/gmail.svg", unit: "threads", total: 48_000, totalLabel: "48K" },
  { id: "github", name: "GitHub", icon: "/brand/github.svg", unit: "PRs", total: 2_300, totalLabel: "2.3K" },
  { id: "linear", name: "Linear", icon: "/brand/linear.svg", unit: "issues", total: 5_100, totalLabel: "5.1K" },
  { id: "notion", name: "Notion", icon: "/brand/notion.svg", unit: "pages", total: 12_000, totalLabel: "12K" },
];

const STEPS: { id: Step; label: string }[] = [
  { id: "create", label: "Workspace" },
  { id: "connect", label: "Connect" },
  { id: "indexing", label: "Index" },
  { id: "ready", label: "Ready" },
];

export function WorkspaceOnboarding() {
  const [step, setStep] = useState<Step>("create");
  const [name, setName] = useState("Acme Inc.");
  const [connected, setConnected] = useState<Set<string>>(new Set(["slack", "gmail"]));
  const [connecting, setConnecting] = useState<string | null>(null);
  const [pct, setPct] = useState(0);
  const rafRef = useRef<number>(0);

  const toggle = (id: string) => {
    if (connected.has(id) || connecting) return;
    setConnecting(id);
    setTimeout(() => {
      setConnected((prev) => new Set(prev).add(id));
      setConnecting(null);
    }, 850);
  };

  // Indexing animation.
  useEffect(() => {
    if (step !== "indexing") return;
    setPct(0);
    const start = performance.now();
    const dur = 3400;
    const tick = (t: number) => {
      const p = Math.min((t - start) / dur, 1);
      setPct(p);
      if (p < 1) rafRef.current = requestAnimationFrame(tick);
      else setTimeout(() => setStep("ready"), 700);
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [step]);

  const activeConnectors = CONNECTORS.filter((c) => connected.has(c.id));
  const stepIndex = STEPS.findIndex((s) => s.id === step);

  return (
    <section className="bg-[var(--paper)] px-6 py-16">
      <div className="mx-auto max-w-3xl">
        {/* progress rail */}
        <div className="mb-10 flex items-center justify-center gap-2">
          {STEPS.map((s, i) => (
            <div key={s.id} className="flex items-center gap-2">
              <div className="flex items-center gap-2">
                <span
                  className={`flex h-7 w-7 items-center justify-center rounded-full text-[11px] font-bold transition-colors ${
                    i < stepIndex
                      ? "bg-[var(--emerald)] text-white"
                      : i === stepIndex
                        ? "bg-[var(--charcoal)] text-white"
                        : "bg-[var(--surface)] text-[var(--charcoal-faint)]"
                  }`}
                >
                  {i < stepIndex ? "✓" : i + 1}
                </span>
                <span className={`hidden text-xs font-medium sm:inline ${i === stepIndex ? "text-[var(--charcoal)]" : "text-[var(--charcoal-muted)]"}`}>
                  {s.label}
                </span>
              </div>
              {i < STEPS.length - 1 && <span className="h-px w-6 bg-[var(--paper-border-strong)]" />}
            </div>
          ))}
        </div>

        <AnimatePresence mode="wait">
          {/* ── Create ─────────────────────────────────────── */}
          {step === "create" && (
            <Panel key="create">
              <h1 className="font-serif text-4xl leading-tight text-[var(--charcoal)] md:text-5xl">
                Create your <span className="italic">Continuum workspace.</span>
              </h1>
              <p className="mt-3 text-[var(--charcoal-muted)]">
                One isolated company memory, built from the tools your team already uses.
              </p>
              <label className="mt-8 block text-[11px] font-semibold uppercase tracking-wider text-[var(--charcoal-muted)]">
                Organization name
              </label>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="mt-2 w-full rounded-2xl border border-[var(--paper-border)] bg-white px-5 py-4 text-lg font-medium text-[var(--charcoal)] outline-none transition focus:border-[var(--purple)] focus:ring-4 focus:ring-[var(--purple-tint)]"
                placeholder="Acme Inc."
              />
              <button
                type="button"
                onClick={() => setStep("connect")}
                disabled={!name.trim()}
                className="group mt-6 inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-[var(--charcoal)] px-8 py-4 text-sm font-semibold text-white shadow-md transition-all hover:bg-black hover:scale-[1.01] active:scale-[0.99] disabled:opacity-50"
              >
                Create workspace
                <span className="transition-transform group-hover:translate-x-1" aria-hidden>→</span>
              </button>
            </Panel>
          )}

          {/* ── Connect ────────────────────────────────────── */}
          {step === "connect" && (
            <Panel key="connect">
              <div className="flex items-center gap-2">
                <span className="flex h-6 w-6 items-center justify-center rounded-md bg-[var(--purple-soft)] text-xs font-bold text-[var(--purple)]">
                  {name.trim().charAt(0).toUpperCase()}
                </span>
                <span className="text-sm font-semibold text-[var(--charcoal)]">{name}</span>
              </div>
              <h1 className="mt-4 font-serif text-3xl leading-tight text-[var(--charcoal)] md:text-4xl">
                Connect your company&apos;s knowledge.
              </h1>
              <p className="mt-2 text-sm text-[var(--charcoal-muted)]">
                Continuum indexes each source into one canonical memory. Connect at least one to continue.
              </p>

              <div className="mt-6 space-y-2.5">
                {CONNECTORS.map((c) => {
                  const isConnected = connected.has(c.id);
                  const isConnecting = connecting === c.id;
                  return (
                    <div
                      key={c.id}
                      className={`flex items-center gap-3 rounded-2xl border p-4 transition-colors ${
                        isConnected ? "border-[var(--emerald-border)] bg-[var(--emerald-soft)]/40" : "border-[var(--paper-border)] bg-white"
                      }`}
                    >
                      <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-white ring-1 ring-black/5">
                        <Image src={c.icon} alt="" width={20} height={20} className="h-5 w-5 object-contain" />
                      </span>
                      <div className="flex-1">
                        <p className="text-sm font-semibold text-[var(--charcoal)]">{c.name}</p>
                        <p className="text-xs text-[var(--charcoal-muted)]">~{c.totalLabel} {c.unit}</p>
                      </div>
                      <button
                        type="button"
                        onClick={() => toggle(c.id)}
                        disabled={isConnected || !!connecting}
                        className={`inline-flex items-center gap-2 rounded-full px-4 py-2 text-xs font-semibold transition-all ${
                          isConnected
                            ? "bg-[var(--emerald-soft)] text-[var(--emerald)]"
                            : "bg-[var(--charcoal)] text-white hover:bg-black disabled:opacity-50"
                        }`}
                      >
                        {isConnected ? (
                          <>✓ Connected</>
                        ) : isConnecting ? (
                          <>
                            <span className="h-3 w-3 animate-spin rounded-full border-2 border-white/40 border-t-white" />
                            Connecting…
                          </>
                        ) : (
                          "Connect"
                        )}
                      </button>
                    </div>
                  );
                })}
              </div>

              {/* progress */}
              <div className="mt-6">
                <div className="flex justify-between text-xs text-[var(--charcoal-muted)]">
                  <span>{connected.size} of {CONNECTORS.length} connected</span>
                </div>
                <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-[var(--surface)]">
                  <motion.div
                    className="h-full rounded-full bg-[var(--purple)]"
                    animate={{ width: `${(connected.size / CONNECTORS.length) * 100}%` }}
                    transition={{ duration: 0.5, ease: easeOut }}
                  />
                </div>
              </div>

              <button
                type="button"
                onClick={() => setStep("indexing")}
                disabled={connected.size === 0}
                className="group mt-6 inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-[var(--charcoal)] px-8 py-4 text-sm font-semibold text-white shadow-md transition-all hover:bg-black hover:scale-[1.01] active:scale-[0.99] disabled:opacity-50"
              >
                Build company memory
                <span className="transition-transform group-hover:translate-x-1" aria-hidden>→</span>
              </button>
            </Panel>
          )}

          {/* ── Indexing ───────────────────────────────────── */}
          {step === "indexing" && (
            <Panel key="indexing">
              <h1 className="font-serif text-3xl leading-tight text-[var(--charcoal)] md:text-4xl">
                Indexing {name}
              </h1>
              <p className="mt-2 text-sm text-[var(--charcoal-muted)]">
                Normalizing artifacts, resolving identities, and building the knowledge graph.
              </p>

              <div className="mt-8 space-y-5">
                {activeConnectors.map((c, i) => {
                  const p = Math.min(Math.max(pct * 1.35 - i * 0.12, 0), 1);
                  const count = Math.floor(p * c.total);
                  return (
                    <div key={c.id}>
                      <div className="flex items-center gap-2.5">
                        <Image src={c.icon} alt="" width={18} height={18} className="h-[18px] w-[18px] object-contain" />
                        <span className="text-sm font-semibold text-[var(--charcoal)]">{c.name}</span>
                        <span className="ml-auto font-mono text-xs text-[var(--charcoal-muted)]">
                          {count.toLocaleString()} / {c.totalLabel} {c.unit}
                          {p >= 1 && <span className="ml-2 text-[var(--emerald)]">✓</span>}
                        </span>
                      </div>
                      <div className="mt-2 h-2 overflow-hidden rounded-full bg-[var(--surface)]">
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-[var(--purple)] to-[#22d3ee] transition-[width] duration-150"
                          style={{ width: `${p * 100}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>

              <p className="mt-8 flex items-center justify-center gap-2 text-sm text-[var(--charcoal-muted)]">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[var(--purple)]" />
                Building company memory…
              </p>
            </Panel>
          )}

          {/* ── Ready ──────────────────────────────────────── */}
          {step === "ready" && (
            <Panel key="ready">
              <div className="flex flex-col items-center text-center">
                <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--emerald-soft)] text-2xl text-[var(--emerald)]">
                  ✓
                </span>
                <h1 className="mt-5 font-serif text-3xl leading-tight text-[var(--charcoal)] md:text-4xl">
                  {name}&apos;s memory is ready.
                </h1>
                <p className="mt-2 max-w-md text-sm text-[var(--charcoal-muted)]">
                  {activeConnectors.length} source{activeConnectors.length > 1 ? "s" : ""} indexed into one canonical,
                  temporal company memory. Ask it anything.
                </p>
              </div>

              <div className="mt-8 grid grid-cols-2 gap-2.5 sm:grid-cols-3">
                {activeConnectors.map((c) => (
                  <div key={c.id} className="rounded-2xl border border-[var(--paper-border)] bg-white p-4 text-center">
                    <Image src={c.icon} alt="" width={20} height={20} className="mx-auto h-5 w-5 object-contain" />
                    <p className="mt-2 font-mono text-sm font-semibold text-[var(--charcoal)]">{c.totalLabel}</p>
                    <p className="text-[10px] uppercase tracking-wider text-[var(--charcoal-faint)]">{c.unit}</p>
                  </div>
                ))}
              </div>

              <div className="mt-8 flex flex-col gap-2.5 sm:flex-row">
                <Link
                  href="/query"
                  className="group inline-flex flex-1 items-center justify-center gap-2 rounded-2xl bg-[var(--charcoal)] px-6 py-4 text-sm font-semibold text-white shadow-md transition-all hover:bg-black hover:scale-[1.01]"
                >
                  Ask your memory
                  <span className="transition-transform group-hover:translate-x-1" aria-hidden>→</span>
                </Link>
                <Link
                  href="/graph"
                  className="inline-flex flex-1 items-center justify-center gap-2 rounded-2xl border border-[var(--paper-border-strong)] bg-white px-6 py-4 text-sm font-semibold text-[var(--charcoal)] transition-all hover:border-[var(--purple)] hover:text-[var(--purple)]"
                >
                  Explore the graph
                </Link>
              </div>

              <button
                type="button"
                onClick={() => { setStep("create"); setConnected(new Set(["slack", "gmail"])); }}
                className="mx-auto mt-5 block text-xs font-medium text-[var(--charcoal-muted)] hover:text-[var(--charcoal)]"
              >
                ↺ Restart onboarding
              </button>
            </Panel>
          )}
        </AnimatePresence>
      </div>
    </section>
  );
}

function Panel({ children }: { children: React.ReactNode }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12 }}
      transition={{ duration: 0.4, ease: easeOut }}
      className="rounded-3xl border border-[var(--paper-border)] bg-white p-7 shadow-[var(--shadow-elevated)] md:p-9"
    >
      {children}
    </motion.div>
  );
}
