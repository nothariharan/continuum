"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { TopNav } from "@/components/ui/TopNav";
import { Footer, CTA } from "@/components/ui/Footer";
import { AnswerCard } from "@/components/ui/AnswerCard";
import { EvidenceCard } from "@/components/ui/EvidenceCard";
import { HistoryCard } from "@/components/ui/HistoryCard";
import { GraphCanvas } from "@/components/ui/GraphCanvas";
import { AnimatedBackground } from "@/components/ui/AnimatedBackground";
import { DEMO_ANSWER_AFTER, DEMO_ANSWER_BEFORE, DEMO_GRAPH, DEMO_SCRIPT } from "@/data/demo-script";
import { easeOut } from "@/components/ui/motion";

export function DemoPlayer() {
  const [stepIndex, setStepIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [owner, setOwner] = useState("Priya");

  const totalSteps = DEMO_SCRIPT.length;

  // Sync state owner depending on step progression
  useEffect(() => {
    if (stepIndex >= 7) {
      setOwner("Sarah");
    } else {
      setOwner("Priya");
    }
  }, [stepIndex]);

  // Autoplay handler
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("autoplay") === "1") {
      setIsPlaying(true);
    }
  }, []);

  useEffect(() => {
    if (!isPlaying) return;
    const timer = setInterval(() => {
      setStepIndex((current) => {
        if (current >= totalSteps - 1) {
          setIsPlaying(false);
          return current;
        }
        return current + 1;
      });
    }, 3200);
    return () => clearInterval(timer);
  }, [isPlaying, totalSteps]);

  const stepTitles = [
    "01. User Query",
    "02. Investigation",
    "03. State Resolved",
    "04. History Lineage",
    "05. Grounding Evidence",
    "06. Graph Traversal",
    "07. New Memory Event",
    "08. Memory Update",
    "09. Re-querying State",
    "10. Updated State with History",
  ];

  return (
    <div className="min-h-screen bg-[var(--paper)] relative">
      <AnimatedBackground variant="marketing" />
      <div className="relative z-10">
        <TopNav />

      <main className="mx-auto max-w-6xl px-6 py-16">
        {/* Header Title */}
        <div className="flex flex-wrap items-end justify-between gap-4 border-b border-black/[0.08] pb-8">
          <div>
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-[var(--purple)] animate-pulse" />
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--charcoal-muted)]">
                Deterministic Presentation
              </p>
            </div>
            <h1 className="mt-3 font-serif text-4xl text-[var(--charcoal)] md:text-6xl tracking-tight">
              The Company Memory Story
            </h1>
            <p className="mt-2 text-sm text-[var(--charcoal-muted)] max-w-xl">
              Step through a complete lifecycle: Question → Investigation → Evidence → Spatial Graph → Real-time Memory Update.
            </p>
          </div>

          {/* Player Controls Bar */}
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => {
                setIsPlaying(false);
                setStepIndex(0);
              }}
              className="rounded-full border border-black/10 bg-white px-4 py-2 text-xs font-medium text-[var(--charcoal)] shadow-2xs hover:bg-black/5"
            >
              Reset
            </button>
            <button
              type="button"
              onClick={() => {
                setIsPlaying(false);
                setStepIndex((c) => Math.max(0, c - 1));
              }}
              disabled={stepIndex === 0}
              className="rounded-full border border-black/10 bg-white px-4 py-2 text-xs font-medium text-[var(--charcoal)] shadow-2xs disabled:opacity-40"
            >
              ← Prev
            </button>
            <button
              type="button"
              onClick={() => setIsPlaying((p) => !p)}
              className="rounded-full bg-[var(--charcoal)] px-5 py-2 text-xs font-semibold text-white shadow-xs hover:bg-black"
            >
              {isPlaying ? "Pause ⏸" : "Autoplay ▶"}
            </button>
            <button
              type="button"
              onClick={() => {
                setIsPlaying(false);
                setStepIndex((c) => Math.min(totalSteps - 1, c + 1));
              }}
              disabled={stepIndex === totalSteps - 1}
              className="rounded-full bg-[var(--purple)] px-5 py-2 text-xs font-semibold text-white shadow-xs hover:bg-[var(--purple-hover)] disabled:opacity-40"
            >
              Next Step →
            </button>
          </div>
        </div>

        {/* 10-Step Scrubber Bar */}
        <div className="mt-8">
          <div className="flex items-center justify-between text-xs text-[var(--charcoal-muted)] mb-2 font-mono">
            <span>Step {stepIndex + 1} of {totalSteps}</span>
            <span className="font-semibold text-[var(--purple)]">{stepTitles[stepIndex]}</span>
          </div>
          <div className="grid grid-cols-10 gap-1.5">
            {stepTitles.map((title, idx) => (
              <button
                key={title}
                type="button"
                onClick={() => {
                  setIsPlaying(false);
                  setStepIndex(idx);
                }}
                className={`h-2 rounded-full transition-all ${
                  idx === stepIndex
                    ? "bg-[var(--purple)] ring-2 ring-[var(--purple)]/30"
                    : idx < stepIndex
                    ? "bg-emerald-500"
                    : "bg-black/10"
                }`}
                title={title}
              />
            ))}
          </div>
        </div>

        {/* Main Stage Stage Display */}
        <div className="mt-10 grid gap-8 lg:grid-cols-[1fr_1.3fr]">
          {/* Left: Narrative & Current Action */}
          <div className="flex flex-col justify-between rounded-3xl border border-black/[0.08] bg-white p-8 shadow-sm">
            <div>
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-semibold uppercase tracking-wider text-[var(--purple)]">
                  Action Narrative
                </span>
                <span className="rounded-full bg-black/5 px-2.5 py-0.5 text-[10px] font-semibold uppercase text-[var(--charcoal-muted)]">
                  {stepIndex >= 7 ? "Post-Handoff State" : "Initial State"}
                </span>
              </div>

              <div className="mt-6">
                <AnimatePresence mode="wait">
                  <motion.div
                    key={stepIndex}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    transition={{ duration: 0.35, ease: easeOut }}
                  >
                    {stepIndex === 0 && (
                      <div>
                        <p className="text-sm font-semibold text-[var(--charcoal-muted)] uppercase tracking-wider">
                          User Prompt:
                        </p>
                        <p className="mt-2 text-2xl font-semibold text-[var(--charcoal)]">
                          &ldquo;Who owns Acme now?&rdquo;
                        </p>
                        <p className="mt-4 text-xs text-[var(--charcoal-muted)] leading-relaxed">
                          The user needs to find the accountable lead for client Acme across Slack, Linear, and Gmail.
                        </p>
                      </div>
                    )}

                    {stepIndex === 1 && (
                      <div>
                        <p className="text-sm font-semibold text-[var(--purple)] uppercase tracking-wider">
                          Continuum Investigation:
                        </p>
                        <p className="mt-2 text-xl font-semibold text-[var(--charcoal)]">
                          Traversing multi-source evidence…
                        </p>
                        <div className="mt-5 space-y-2">
                          {["Slack handoff announcement (#leads)", "Gmail contract renewal memo", "Linear project lead assignment"].map((s) => (
                            <div key={s} className="flex items-center gap-2 text-xs font-medium text-[var(--charcoal)]">
                              <span className="text-emerald-500">✓</span>
                              <span>{s}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {stepIndex === 2 && (
                      <div>
                        <p className="text-sm font-semibold text-emerald-600 uppercase tracking-wider">
                          Resolved State:
                        </p>
                        <p className="mt-2 text-3xl font-semibold text-[var(--charcoal)]">
                          Priya owns Acme now.
                        </p>
                        <p className="mt-4 text-xs text-[var(--charcoal-muted)] leading-relaxed">
                          Synthesized with 98% confidence. Valid from Aug 01, 2026. Previous owner was Morgan.
                        </p>
                      </div>
                    )}

                    {stepIndex === 3 && (
                      <div>
                        <p className="text-sm font-semibold text-[var(--purple)] uppercase tracking-wider">
                          Temporal Lineage:
                        </p>
                        <p className="mt-2 text-xl font-semibold text-[var(--charcoal)]">
                          Morgan → Priya
                        </p>
                        <p className="mt-4 text-xs text-[var(--charcoal-muted)] leading-relaxed">
                          Continuum preserves the historical record so past audits remain 100% accurate.
                        </p>
                      </div>
                    )}

                    {stepIndex === 4 && (
                      <div>
                        <p className="text-sm font-semibold text-[var(--purple)] uppercase tracking-wider">
                          Grounding Evidence:
                        </p>
                        <p className="mt-2 text-xl font-semibold text-[var(--charcoal)]">
                          3 Independent Artifacts Anchor the State
                        </p>
                        <p className="mt-4 text-xs text-[var(--charcoal-muted)] leading-relaxed">
                          Slack announcement, Gmail client notice, and Linear ticket all confirm Priya&apos;s ownership.
                        </p>
                      </div>
                    )}

                    {stepIndex === 5 && (
                      <div>
                        <p className="text-sm font-semibold text-[var(--purple)] uppercase tracking-wider">
                          HydraDB Graph Substrate:
                        </p>
                        <p className="mt-2 text-xl font-semibold text-[var(--charcoal)]">
                          Connected Topology
                        </p>
                        <p className="mt-4 text-xs text-[var(--charcoal-muted)] leading-relaxed">
                          Every person, entity, artifact, and claim is stored as a graph node in HydraDB.
                        </p>
                      </div>
                    )}

                    {stepIndex === 6 && (
                      <div className="rounded-2xl border border-[var(--purple)]/30 bg-[var(--purple-soft)] p-5">
                        <div className="flex items-center gap-2">
                          <span className="h-2 w-2 rounded-full bg-[var(--purple)] animate-ping" />
                          <p className="text-xs font-semibold uppercase tracking-wider text-[var(--purple)]">
                            Live Memory Event Ingested
                          </p>
                        </div>
                        <p className="mt-3 text-base font-semibold text-[var(--charcoal)]">
                          Priya posts in Slack: &ldquo;I&apos;m handing over Acme to Sarah starting today.&rdquo;
                        </p>
                        <p className="mt-2 text-xs text-[var(--charcoal-muted)]">
                          Continuum extracts atomic claim: <code>Sarah OWNS Acme</code>.
                        </p>
                      </div>
                    )}

                    {stepIndex === 7 && (
                      <div>
                        <p className="text-sm font-semibold text-[var(--purple)] uppercase tracking-wider">
                          Memory Engine Delta:
                        </p>
                        <p className="mt-2 text-2xl font-semibold text-[var(--charcoal)]">
                          Continuum Updates State Automatically
                        </p>
                        <p className="mt-4 text-xs text-[var(--charcoal-muted)] leading-relaxed">
                          Active owner changes to Sarah. Morgan and Priya remain in immutable historical lineage.
                        </p>
                      </div>
                    )}

                    {stepIndex === 8 && (
                      <div>
                        <p className="text-sm font-semibold text-[var(--charcoal-muted)] uppercase tracking-wider">
                          Re-Querying Same Question:
                        </p>
                        <p className="mt-2 text-2xl font-semibold text-[var(--charcoal)]">
                          &ldquo;Who owns Acme now?&rdquo;
                        </p>
                        <p className="mt-4 text-xs text-[var(--charcoal-muted)] leading-relaxed">
                          Asking the exact same query immediately returns the updated ground truth.
                        </p>
                      </div>
                    )}

                    {stepIndex === 9 && (
                      <div>
                        <p className="text-sm font-semibold text-emerald-600 uppercase tracking-wider">
                          Final Evolved State:
                        </p>
                        <p className="mt-2 text-3xl font-semibold text-[var(--charcoal)]">
                          Sarah owns Acme now.
                        </p>
                        <p className="mt-4 text-xs text-[var(--charcoal-muted)] leading-relaxed">
                          Lineage: Morgan → Priya → Sarah. All past context retained with zero hallucinations.
                        </p>
                      </div>
                    )}
                  </motion.div>
                </AnimatePresence>
              </div>
            </div>

            <div className="mt-8 border-t border-black/[0.08] pt-4 flex items-center justify-between text-xs text-[var(--charcoal-muted)]">
              <span className="font-mono">Continuum v1.0</span>
              <span className="font-medium text-[var(--purple)]">Deterministic Simulation</span>
            </div>
          </div>

          {/* Right: Dynamic UI Component Preview */}
          <div className="space-y-6">
            <AnswerCard
              answer={owner === "Sarah" ? DEMO_ANSWER_AFTER.answer : DEMO_ANSWER_BEFORE.answer}
              status="definitive"
              previous={owner === "Sarah" ? DEMO_ANSWER_AFTER.previous : DEMO_ANSWER_BEFORE.previous}
              effective={owner === "Sarah" ? DEMO_ANSWER_AFTER.effective : DEMO_ANSWER_BEFORE.effective}
              confidence={0.98}
              sources={owner === "Sarah" ? ["Slack"] : ["Slack", "Gmail", "Linear"]}
            />

            {stepIndex >= 3 && (
              <HistoryCard
                rows={
                  owner === "Sarah"
                    ? [
                        { from: "Priya", to: "Sarah", date: "Today", reason: "Live Slack handoff message" },
                        { from: "Morgan", to: "Priya", date: "Aug 01, 2026", reason: "Formal transfer memo" },
                      ]
                    : [
                        { from: "Morgan", to: "Priya", date: "Aug 01, 2026", reason: "Formal transfer memo" },
                        { from: "Bootstrap", to: "Morgan", date: "Jul 18, 2026", reason: "Initial assignment" },
                      ]
                }
              />
            )}

            {stepIndex >= 4 && (
              <EvidenceCard
                expanded
                dark={false}
                items={
                  owner === "Sarah"
                    ? [
                        {
                          artifact_id: "art_slack_handoff_sarah_902",
                          artifact_kind: "Slack Handoff Message (#leads)",
                          source: "slack",
                          observed_at: "Today at 11:42 AM",
                          subject_mention: "Sarah",
                          object_mention: "Acme",
                          claim_id: "clm_902s",
                        },
                      ]
                    : [
                        {
                          artifact_id: "art_slack_handoff_891",
                          artifact_kind: "Slack Handoff Thread (#leads)",
                          source: "slack",
                          observed_at: "2026-08-01",
                          subject_mention: "Priya",
                          object_mention: "Acme",
                          claim_id: "clm_891a",
                        },
                        {
                          artifact_id: "art_gmail_notice_204",
                          artifact_kind: "Gmail Handoff Confirmation Notice",
                          source: "gmail",
                          observed_at: "2026-08-01",
                          subject_mention: "Priya",
                          object_mention: "Acme",
                          claim_id: "clm_204g",
                        },
                      ]
                }
              />
            )}

            {stepIndex >= 5 && (
              <div className="rounded-3xl border border-black/[0.08] bg-white p-4 shadow-sm">
                <p className="text-xs font-semibold uppercase tracking-wider text-[var(--charcoal-muted)] mb-3">
                  Spatial Knowledge Graph View:
                </p>
                <GraphCanvas graph={DEMO_GRAPH} compact selectedId="account:acme" />
              </div>
            )}
          </div>
        </div>
      </main>

      <CTA />
      <Footer />
      </div>
    </div>
  );
}
