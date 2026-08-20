"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { SourceBadge } from "@/components/ui/SourceBadge";
import { Reveal, easeOut } from "@/components/ui/motion";

const SLACK_TIMELINE = [
  {
    step: 0,
    type: "user_query",
    time: "10:14 AM",
    user: "Alex",
    avatar: "👨‍💻",
    content: "@continuum who owns Acme now?",
  },
  {
    step: 1,
    type: "bot_answer",
    time: "10:14 AM",
    user: "Continuum",
    isBot: true,
    title: "Priya owns Acme now.",
    subtitle: "Morgan owned it before the handoff.",
    status: "Definitive State",
    sources: ["Slack", "Gmail", "Linear"],
  },
  {
    step: 2,
    type: "live_event",
    time: "11:42 AM",
    user: "Priya",
    avatar: "👩‍💼",
    content: "Heads up team: I'm handing over Acme account lead to Sarah starting today!",
    highlight: "New Memory Event Ingested",
  },
  {
    step: 3,
    type: "bot_update",
    time: "11:43 AM",
    user: "Continuum",
    isBot: true,
    title: "Sarah owns Acme now.",
    subtitle: "Updated automatically. Lineage preserved: Morgan → Priya → Sarah.",
    status: "Memory Updated",
    sources: ["Slack"],
  },
];

export function SlackAnswer() {
  const [activeStep, setActiveStep] = useState<number>(1);
  const [autoPlay, setAutoPlay] = useState<boolean>(true);

  useEffect(() => {
    if (!autoPlay) return;
    const timer = setInterval(() => {
      setActiveStep((prev) => (prev + 1) % 4);
    }, 4200);
    return () => clearInterval(timer);
  }, [autoPlay]);

  return (
    <section id="slack" className="bg-[var(--paper)] px-6 py-28">
      <div className="mx-auto grid max-w-6xl gap-12 lg:grid-cols-[1.1fr_1.3fr] lg:items-center">
        {/* Left Editorial Copy */}
        <Reveal>
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--charcoal-muted)]">
              Slack Live Integration
            </p>
          </div>
          <h2 className="mt-4 font-serif text-4xl leading-tight text-[var(--charcoal)] md:text-6xl text-balance tracking-tight">
            Continuum lives where your team already works.
          </h2>
          <p className="mt-6 text-base leading-relaxed text-[var(--charcoal-muted)]">
            Ask directly in Slack channels or DMs. Continuum returns structured Block Kit answers
            with state, history, and verifiable citations — not another unstructured thread to dig through.
          </p>

          <div className="mt-8 flex flex-wrap items-center gap-4">
            <SourceBadge source="Slack" status="connected" size="lg" />
            <span className="text-xs font-mono text-emerald-700 bg-emerald-50 border border-emerald-200 px-2.5 py-1 rounded-full font-semibold">
              Bot Loop: verified active
            </span>
          </div>

          {/* Interactive Step Navigator */}
          <div className="mt-10 rounded-2xl border border-black/[0.08] bg-white p-4 shadow-xs">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-[var(--charcoal-muted)] mb-3">
              Interactive Scenario Progression:
            </p>
            <div className="grid grid-cols-4 gap-2">
              {[
                { label: "1. Query" },
                { label: "2. Answer" },
                { label: "3. Handoff" },
                { label: "4. Update" },
              ].map((s, idx) => (
                <button
                  key={s.label}
                  type="button"
                  onClick={() => {
                    setAutoPlay(false);
                    setActiveStep(idx);
                  }}
                  className={`rounded-xl py-2 text-xs font-semibold transition-all ${
                    activeStep === idx
                      ? "bg-[var(--charcoal)] text-white shadow-xs"
                      : "bg-[#faf8f5] text-[var(--charcoal-muted)] hover:bg-black/5 hover:text-[var(--charcoal)]"
                  }`}
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>
        </Reveal>

        {/* Right Slack Channel Mockup (Authentic Slack Light Theme) */}
        <Reveal delay={0.1}>
          <div className="overflow-hidden rounded-3xl border border-black/[0.08] bg-white shadow-[0_20px_60px_-15px_rgba(15,23,42,0.08)]">
            {/* Slack Header */}
            <div className="flex items-center justify-between border-b border-black/[0.06] bg-[#f8fafc] px-6 py-3.5 text-[var(--charcoal)]">
              <div className="flex items-center gap-2.5">
                <span className="font-bold text-slate-400">#</span>
                <span className="text-sm font-semibold">team-leads</span>
                <span className="rounded-full bg-black/[0.04] px-2 py-0.5 text-[10px] text-slate-500 font-medium">
                  42 members
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                <span className="text-xs text-slate-500 font-mono font-medium">Continuum Bot: Active</span>
              </div>
            </div>

            {/* Slack Messages Stream */}
            <div className="min-h-[420px] p-6 space-y-6 bg-white">
              <AnimatePresence mode="popLayout">
                {SLACK_TIMELINE.slice(0, activeStep + 1).map((msg) => (
                  <motion.div
                    key={msg.step}
                    initial={{ opacity: 0, y: 14 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    transition={{ duration: 0.4, ease: easeOut }}
                    className="flex items-start gap-3.5"
                  >
                    {/* Avatar */}
                    {msg.isBot ? (
                      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[var(--purple)] text-white font-bold text-sm shadow-xs">
                        ∞
                      </div>
                    ) : (
                      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-slate-100 border border-black/[0.06] text-base">
                        {msg.avatar}
                      </div>
                    )}

                    {/* Message Body */}
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-[var(--charcoal)]">{msg.user}</span>
                        {msg.isBot && (
                          <span className="rounded bg-slate-100 border border-black/[0.06] px-1.5 py-0.2 text-[9px] font-bold uppercase text-slate-600">
                            APP
                          </span>
                        )}
                        <span className="text-[10px] text-slate-400 font-mono">{msg.time}</span>
                      </div>

                      {/* Content */}
                      {msg.content && (
                        <p className="mt-1.5 text-sm text-[var(--charcoal-body)] leading-relaxed">
                          {msg.content.includes("@continuum") ? (
                            <>
                              <span className="rounded bg-sky-100 px-1.5 py-0.5 font-medium text-sky-800">
                                @continuum
                              </span>{" "}
                              {msg.content.replace("@continuum", "")}
                            </>
                          ) : (
                            msg.content
                          )}
                        </p>
                      )}

                      {/* Bot Block Kit Card */}
                      {msg.isBot && (
                        <div className="mt-2.5 rounded-2xl border-l-4 border-l-[var(--purple)] border border-black/[0.08] bg-[#faf8f5] p-4 text-[var(--charcoal)] shadow-2xs">
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--purple)]">
                              {msg.status}
                            </span>
                            <span className="font-mono text-[10px] text-slate-400">valid_now</span>
                          </div>

                          <p className="mt-1 text-base font-semibold text-[var(--charcoal)]">{msg.title}</p>
                          <p className="mt-0.5 text-xs text-[var(--charcoal-muted)]">{msg.subtitle}</p>

                          {msg.sources && (
                            <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-black/[0.04] pt-3">
                              <span className="text-[10px] font-semibold uppercase text-slate-400">
                                Grounded In:
                              </span>
                              {msg.sources.map((s) => (
                                <SourceBadge key={s} source={s} size="xs" />
                              ))}
                            </div>
                          )}
                        </div>
                      )}

                      {msg.highlight && (
                        <div className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-emerald-50 border border-emerald-200 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-emerald-800">
                          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-ping" />
                          <span>{msg.highlight}</span>
                        </div>
                      )}
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}

export function MemoryUpdateSection() {
  return (
    <section className="bg-white px-6 py-28 border-t border-black/[0.06]">
      <div className="mx-auto max-w-5xl text-center">
        <Reveal>
          <div className="inline-flex items-center gap-2 rounded-full border border-black/[0.08] bg-[#faf8f5] px-3.5 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--charcoal-muted)] shadow-2xs">
            Live Memory Loop
          </div>
          <h2 className="mt-4 font-serif text-4xl text-[var(--charcoal)] md:text-6xl tracking-tight">
            How Continuum updates company memory.
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-base text-[var(--charcoal-muted)] leading-relaxed">
            When Priya announced the handoff in Slack, Continuum processed the new evidence, updated the
            active state to Sarah, and preserved the historical lineage.
          </p>
        </Reveal>

        {/* 3-Stage Memory Evolution */}
        <div className="mt-16 grid gap-6 text-left md:grid-cols-3">
          <Reveal delay={0.05}>
            <div className="h-full rounded-3xl border border-black/[0.08] bg-[#faf8f5] p-6 shadow-2xs">
              <span className="rounded-full bg-black/5 px-2.5 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wider text-[var(--charcoal-muted)]">
                State Before
              </span>
              <p className="mt-4 text-xl font-semibold text-[var(--charcoal)]">Priya owns Acme</p>
              <p className="mt-2 text-xs text-[var(--charcoal-muted)] leading-relaxed">
                Resolved on Aug 01 from Linear & Gmail handoff agreements.
              </p>
            </div>
          </Reveal>

          <Reveal delay={0.1}>
            <div className="h-full rounded-3xl border-2 border-emerald-400/60 bg-emerald-50/40 p-6 shadow-xs">
              <span className="rounded-full bg-emerald-100 px-2.5 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wider text-emerald-800">
                New Information
              </span>
              <p className="mt-4 text-xl font-semibold text-emerald-950">
                &ldquo;Handing over Acme to Sarah today&rdquo;
              </p>
              <p className="mt-2 text-xs text-emerald-800 leading-relaxed">
                Ingested from Priya&apos;s Slack announcement in #team-leads at 11:42 AM.
              </p>
            </div>
          </Reveal>

          <Reveal delay={0.15}>
            <div className="h-full rounded-3xl border border-[var(--purple)] bg-[var(--purple-soft)] p-6 shadow-xs">
              <span className="rounded-full bg-[var(--purple)] px-2.5 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wider text-white">
                State After
              </span>
              <p className="mt-4 text-xl font-semibold text-[var(--charcoal)]">Sarah owns Acme now</p>
              <p className="mt-2 text-xs text-[var(--charcoal-muted)] leading-relaxed">
                State updated immediately. Lineage preserved: Morgan → Priya → Sarah.
              </p>
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  );
}
