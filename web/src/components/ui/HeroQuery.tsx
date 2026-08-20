"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import { motion, AnimatePresence } from "framer-motion";
import { SourceBadge } from "./SourceBadge";
import { easeOut } from "./motion";

const SOURCES = [
  { name: "Slack", icon: "/brand/slack.svg", quote: "Priya taking over Acme #leads" },
  { name: "Gmail", icon: "/brand/gmail.svg", quote: "Re: Acme client handoff memo" },
  { name: "Linear", icon: "/brand/linear.svg", quote: "ACM-104: Transfer project lead" },
  { name: "GitHub", icon: "/brand/github.svg", quote: "acme-infra CODEOWNERS @priya" },
];

export function HeroQuery() {
  const [phase, setPhase] = useState<"sources" | "query" | "answer">("sources");
  const [typedChars, setTypedChars] = useState(0);
  const fullQuery = "Who owns Acme now?";

  useEffect(() => {
    const timer1 = setTimeout(() => setPhase("query"), 1200);
    return () => clearTimeout(timer1);
  }, []);

  useEffect(() => {
    if (phase === "query") {
      let count = 0;
      const interval = setInterval(() => {
        count += 1;
        setTypedChars(count);
        if (count >= fullQuery.length) {
          clearInterval(interval);
          setTimeout(() => setPhase("answer"), 500);
        }
      }, 45);
      return () => clearInterval(interval);
    }
  }, [phase]);

  const replay = () => {
    setPhase("sources");
    setTypedChars(0);
    setTimeout(() => setPhase("query"), 800);
  };

  return (
    <motion.div
      className="relative mx-auto mt-16 max-w-3xl overflow-hidden rounded-[28px] border border-black/[0.08] bg-white p-6 shadow-[0_30px_90px_-20px_rgba(20,20,20,0.08)] md:p-10"
      initial={{ opacity: 0, y: 32 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.35, duration: 0.7, ease: easeOut }}
    >
      {/* Top Source Ingestion Row */}
      <div className="flex flex-wrap items-center justify-center gap-2.5 sm:gap-3">
        {SOURCES.map((source, index) => (
          <motion.div
            key={source.name}
            initial={{ opacity: 0, scale: 0.85, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            transition={{ delay: 0.15 + index * 0.15, duration: 0.45, ease: easeOut }}
            className="flex items-center gap-2 rounded-full border border-black/[0.06] bg-[#faf8f5] px-3 py-1.5 shadow-2xs hover:scale-105 transition-transform"
          >
            <Image
              src={source.icon}
              alt={source.name}
              width={16}
              height={16}
              className="object-contain"
            />
            <span className="text-xs font-medium text-[var(--charcoal)]">{source.name}</span>
          </motion.div>
        ))}
      </div>

      {/* Stream Convergence Vector */}
      <div className="relative my-6 flex flex-col items-center justify-center">
        <svg width="40" height="36" viewBox="0 0 40 36" fill="none" className="text-[var(--purple)]">
          <path
            d="M20 0V28M20 28L12 20M20 28L28 20"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="opacity-70 animate-pulse"
          />
        </svg>
        <div className="mt-1 flex items-center gap-1.5 rounded-full bg-[var(--purple-soft)] px-3 py-0.5 text-[10px] font-semibold uppercase tracking-widest text-[var(--purple)]">
          <span>Continuum State Engine</span>
        </div>
      </div>

      {/* Query Bar */}
      <div className="mx-auto max-w-lg rounded-2xl border border-black/[0.08] bg-[#faf8f5] px-5 py-3.5 shadow-inner">
        <div className="flex items-center gap-3 text-sm">
          <span className="font-mono text-xs text-[var(--charcoal-muted)]">Query:</span>
          <span className="font-medium text-[var(--charcoal)]">
            {phase === "sources" ? (
              <span className="text-[var(--charcoal-muted)]/50">Listening to workspace events…</span>
            ) : (
              <>
                {fullQuery.slice(0, typedChars)}
                {phase === "query" && typedChars < fullQuery.length && (
                  <span className="inline-block h-4 w-0.5 bg-[var(--purple)] animate-pulse" />
                )}
              </>
            )}
          </span>
        </div>
      </div>

      {/* Structured Answer Card */}
      <AnimatePresence>
        {phase === "answer" && (
          <motion.div
            initial={{ opacity: 0, y: 16, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.5, ease: easeOut }}
            className="mx-auto mt-5 max-w-lg rounded-2xl border border-[var(--purple)]/20 bg-gradient-to-b from-[#f7f5ff] to-white p-5 text-left shadow-sm"
          >
            <div className="flex items-center justify-between">
              <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-emerald-600">
                Resolved Answer
              </span>
              <span className="font-mono text-[10px] text-[var(--charcoal-muted)]">
                valid_from: 2026-08-01
              </span>
            </div>

            <p className="mt-2.5 text-xl font-semibold tracking-tight text-[var(--charcoal)]">
              Priya owns Acme now.
            </p>

            <div className="mt-3 flex items-center justify-between border-t border-black/5 pt-3 text-xs text-[var(--charcoal-muted)]">
              <span>
                Previous owner: <strong className="text-[var(--charcoal)]">Morgan</strong>
              </span>
              <span>
                Confidence: <strong className="text-emerald-600">98%</strong>
              </span>
            </div>

            <div className="mt-3.5 flex flex-wrap items-center gap-1.5">
              <span className="text-[10px] font-medium text-[var(--charcoal-muted)] uppercase tracking-wider mr-1">
                Grounded by:
              </span>
              {["Slack", "Gmail", "Linear"].map((s) => (
                <SourceBadge key={s} source={s} size="xs" />
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Sub-interactive Controls */}
      <div className="mt-6 flex items-center justify-center gap-3">
        <button
          type="button"
          onClick={replay}
          className="text-xs text-[var(--charcoal-muted)] hover:text-[var(--purple)] transition-colors flex items-center gap-1"
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M1 4v6h6M23 20v-6h-6" />
            <path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 0 1 3.51 15" />
          </svg>
          Replay simulation
        </button>
      </div>
    </motion.div>
  );
}
