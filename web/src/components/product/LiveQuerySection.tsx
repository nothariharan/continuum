"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { QueryExperiencePanel } from "@/components/product/QueryExperiencePanel";
import { askQuestion, isApiAvailable } from "@/lib/api";
import type { AskResult } from "@/lib/contracts";
import { Reveal } from "@/components/ui/motion";

const SAMPLE_QUESTIONS = [
  "Who owns Acme now?",
  "When did the Acme handoff happen?",
  "Who maintains payments-service?",
  "Show Acme ownership history",
];

export function LiveQuerySection() {
  const [question, setQuestion] = useState("Who owns Acme now?");
  const [result, setResult] = useState<AskResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [live, setLive] = useState(false);

  useEffect(() => {
    isApiAvailable().then(setLive);
  }, []);

  async function submit(targetQuery = question) {
    setLoading(true);
    try {
      if (live) {
        const payload = await askQuestion(targetQuery);
        setResult(payload);
      } else {
        // Deterministic state response when offline
        setResult(null);
      }
    } finally {
      setLoading(false);
    }
  }

  const handlePresetClick = (q: string) => {
    setQuestion(q);
    void submit(q);
  };

  return (
    <section
      id="query"
      className="relative overflow-hidden bg-[var(--paper)] px-6 py-28 text-[var(--charcoal)]"
    >
      <div className="relative mx-auto max-w-6xl">
        <Reveal className="mb-12 flex flex-wrap items-end justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-[var(--purple)] animate-pulse" />
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--charcoal-muted)]">
                Query Layer
              </p>
            </div>
            <h2 className="mt-3 font-serif text-4xl text-[var(--charcoal)] md:text-6xl tracking-tight">
              Ask once. Know why.
            </h2>
            <p className="mt-2 text-sm text-[var(--charcoal-muted)] max-w-xl leading-relaxed">
              Unlike generic chatbots that guess from raw text, Continuum queries resolved graph state and returns verifiable provenance.
            </p>
          </div>

          <motion.div
            className="flex items-center gap-2 rounded-full border border-black/[0.08] bg-white px-4 py-1.5 text-xs text-[var(--charcoal-muted)] shadow-xs"
            animate={live ? { borderColor: ["rgba(0,0,0,0.08)", "rgba(99,102,241,0.5)", "rgba(0,0,0,0.08)"] } : {}}
            transition={{ duration: 3, repeat: Infinity }}
          >
            <span className={`h-2 w-2 rounded-full ${live ? "bg-emerald-500" : "bg-purple-500"}`} />
            <span className="font-mono text-[11px] font-medium">{live ? "API: Live (HydraDB)" : "Deterministic Query Engine"}</span>
          </motion.div>
        </Reveal>

        {/* Preset Question Pills */}
        <Reveal delay={0.05} className="mb-6">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs text-[var(--charcoal-muted)] mr-1">Suggested:</span>
            {SAMPLE_QUESTIONS.map((preset) => (
              <button
                key={preset}
                type="button"
                onClick={() => handlePresetClick(preset)}
                className={`rounded-full border px-3.5 py-1 text-xs font-medium transition-all ${
                  question === preset
                    ? "border-[var(--purple)] bg-[var(--purple-soft)] text-[var(--purple)] shadow-xs"
                    : "border-black/[0.08] bg-white text-[var(--charcoal)] hover:border-black/20 hover:shadow-2xs"
                }`}
              >
                {preset}
              </button>
            ))}
          </div>
        </Reveal>

        {/* Input Form */}
        <Reveal delay={0.08}>
          <form
            className="mb-10 flex flex-col gap-3 sm:flex-row"
            onSubmit={(e) => {
              e.preventDefault();
              void submit();
            }}
          >
            <div className="relative flex-1">
              <input
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                className="w-full rounded-2xl border border-black/[0.08] bg-white px-5 py-4 text-sm text-[var(--charcoal)] placeholder-slate-400 outline-none transition focus:border-[var(--purple)] focus:ring-4 focus:ring-[var(--purple-tint)] shadow-sm"
                placeholder="Ask Continuum about people, projects, decisions..."
              />
              <span className="absolute right-4 top-1/2 -translate-y-1/2 font-mono text-[10px] text-slate-400">
                ↵ Enter
              </span>
            </div>
            <motion.button
              type="submit"
              disabled={loading}
              className="inline-flex items-center justify-center gap-2 rounded-2xl bg-[var(--charcoal)] px-8 py-4 text-sm font-semibold text-white shadow-md transition hover:bg-black disabled:opacity-60"
              whileHover={{ scale: loading ? 1 : 1.02 }}
              whileTap={{ scale: loading ? 1 : 0.98 }}
            >
              {loading ? (
                <>
                  <span className="h-4 w-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                  <span>Traversing HydraDB…</span>
                </>
              ) : (
                <>
                  <span>Ask Continuum</span>
                  <span>→</span>
                </>
              )}
            </motion.button>
          </form>
        </Reveal>

        {/* Experience Panel */}
        <Reveal delay={0.12}>
          <QueryExperiencePanel result={result} loading={loading} demo={!live && !result} />
        </Reveal>
      </div>
    </section>
  );
}
