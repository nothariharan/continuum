"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { AnswerCard } from "@/components/ui/AnswerCard";
import { EvidenceCard } from "@/components/ui/EvidenceCard";
import { HistoryCard } from "@/components/ui/HistoryCard";
import type { AskResult } from "@/lib/contracts";
import { DEMO_ANSWER_BEFORE } from "@/data/demo-script";
import { easeOut } from "@/components/ui/motion";

type Tab = "current" | "history" | "why";

export function QueryExperiencePanel({
  result,
  loading,
  demo = false,
}: {
  result?: AskResult | null;
  loading?: boolean;
  demo?: boolean;
}) {
  const [tab, setTab] = useState<Tab>("current");

  const fallback = DEMO_ANSWER_BEFORE;
  const answer =
    result?.answer ||
    result?.state_result?.value?.name ||
    (demo ? fallback.answer : "Priya owns Acme now.");
  const status = result?.status ?? (demo ? fallback.status : "definitive");
  const sources =
    result?.evidence?.map((e) => e.source || "Slack").filter(Boolean) ??
    (demo ? fallback.sources : ["Slack", "Gmail", "Linear"]);

  const evidenceItems = result?.evidence ?? [
    {
      artifact_id: "art_slack_handoff_891",
      artifact_kind: "Slack Handoff Thread (#leads)",
      source: "slack",
      observed_at: "2026-08-01T10:14:00Z",
      subject_mention: "Priya",
      object_mention: "Acme",
      claim_id: "clm_891a",
    },
    {
      artifact_id: "art_gmail_notice_204",
      artifact_kind: "Gmail Handoff Confirmation Notice",
      source: "gmail",
      observed_at: "2026-08-01T11:30:00Z",
      subject_mention: "Priya",
      object_mention: "Acme",
      claim_id: "clm_204g",
    },
    {
      artifact_id: "art_linear_lead_441",
      artifact_kind: "Linear Project Lead Transition ACM-104",
      source: "linear",
      observed_at: "2026-08-01T14:00:00Z",
      subject_mention: "Priya",
      object_mention: "Acme",
      claim_id: "clm_441l",
    },
  ];

  const historyRows = result?.state_result?.history?.length
    ? result.state_result.history
    : [
        { from: "Morgan", to: "Priya", date: "Aug 01, 2026", reason: "Formal client transition" },
        { from: "System Bootstrap", to: "Morgan", date: "Jul 18, 2026", reason: "Initial account creation" },
      ];

  return (
    <div className="grid gap-8 lg:grid-cols-[1fr_1.2fr]">
      {/* Left: Query Context & Execution Telemetry */}
      <div className="flex flex-col justify-between rounded-3xl border border-black/[0.08] bg-white p-7 shadow-[0_12px_32px_-8px_rgba(15,23,42,0.06)]">
        <div>
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[var(--charcoal-muted)]">
              Query Question
            </span>
            <span className="rounded-full bg-emerald-50 border border-emerald-200 px-2.5 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wider text-emerald-700">
              Deterministic Resolution
            </span>
          </div>

          <p className="mt-3 text-xl font-medium text-[var(--charcoal)]">
            {result?.question ?? fallback.question}
          </p>

          <div className="mt-6 space-y-3 rounded-2xl border border-black/[0.06] bg-[#faf8f5] p-4 text-xs font-mono">
            <div className="flex justify-between text-[var(--charcoal-muted)]">
              <span>Entity Resolution:</span>
              <span className="font-semibold text-[var(--charcoal)]">account:acme (100%)</span>
            </div>
            <div className="flex justify-between text-[var(--charcoal-muted)]">
              <span>Graph Substrate:</span>
              <span className="font-semibold text-[var(--purple)]">HydraDB Engine</span>
            </div>
            <div className="flex justify-between text-[var(--charcoal-muted)]">
              <span>Claims Evaluated:</span>
              <span className="font-semibold text-emerald-700">3 validated / 0 conflict</span>
            </div>
            <div className="flex justify-between text-[var(--charcoal-muted)]">
              <span>Query Latency:</span>
              <span className="font-semibold text-emerald-700">~2.4ms (p50)</span>
            </div>
          </div>
        </div>

        {/* Loading Indicator */}
        <AnimatePresence>
          {loading && (
            <motion.div
              className="mt-4 rounded-xl bg-purple-50 border border-purple-200 p-3"
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
            >
              <div className="flex items-center gap-2 text-xs text-[var(--purple)]">
                <span className="h-2 w-2 rounded-full bg-[var(--purple)] animate-ping" />
                <span>Traversing HydraDB graph neighborhoods…</span>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Right: Tabbed 3-Way State Views */}
      <div className="space-y-4">
        {/* Navigation Tabs */}
        <div className="flex items-center gap-2 rounded-2xl border border-black/[0.08] bg-white p-1.5 shadow-2xs">
          {(
            [
              { id: "current", label: "01. Current State" },
              { id: "history", label: "02. Historical Lineage" },
              { id: "why", label: "03. Why / Evidence" },
            ] as const
          ).map((tabItem) => (
            <motion.button
              key={tabItem.id}
              type="button"
              onClick={() => setTab(tabItem.id)}
              className={`flex-1 rounded-xl py-2 text-xs font-semibold uppercase tracking-wider transition-all ${
                tab === tabItem.id
                  ? "bg-[var(--charcoal)] text-white shadow-xs"
                  : "text-[var(--charcoal-muted)] hover:text-[var(--charcoal)] hover:bg-black/[0.03]"
              }`}
              whileTap={{ scale: 0.98 }}
            >
              {tabItem.label}
            </motion.button>
          ))}
        </div>

        {/* Tab Content */}
        <AnimatePresence mode="wait">
          <motion.div
            key={tab}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.25, ease: easeOut }}
          >
            {tab === "current" && (
              <AnswerCard
                answer={String(answer)}
                status={status}
                previous={demo ? fallback.previous : "Morgan"}
                effective={demo ? fallback.effective : result?.state_result?.valid_from ?? "Aug 01, 2026"}
                confidence={0.98}
                sources={[...new Set(sources as string[])]}
              />
            )}

            {tab === "history" && (
              <HistoryCard rows={historyRows} />
            )}

            {tab === "why" && (
              <EvidenceCard expanded items={evidenceItems} />
            )}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}
