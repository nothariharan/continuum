"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import { motion, AnimatePresence } from "framer-motion";
import { SourceBadge } from "@/components/ui/SourceBadge";
import { EmergingMemoryGraph } from "@/components/product/EmergingMemoryGraph";
import { Reveal, easeOut } from "@/components/ui/motion";

/* Authentic Slack chrome colors */
const AUBERGINE = "#3F0E40";
const AUBERGINE_RAIL = "#350D36";
const SLACK_ACTIVE = "#1164A3";

/* Workplace tools Continuum lives inside — cycled in the hero headline. */
const WORKPLACE_ICONS = [
  { src: "/brand/slack.svg", label: "Slack" },
  { src: "/brand/gmail.svg", label: "Gmail" },
  { src: "/brand/notion.svg", label: "Notion" },
  { src: "/brand/outlook.svg", label: "Outlook" },
  { src: "/brand/teams.svg", label: "Teams" },
  { src: "/brand/drive.svg", label: "Drive" },
];

function RotatingSourceIcon() {
  const [i, setI] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setI((x) => (x + 1) % WORKPLACE_ICONS.length), 1600);
    return () => clearInterval(t);
  }, []);
  const cur = WORKPLACE_ICONS[i];
  return (
    <span
      className="relative mx-1 inline-flex h-[0.82em] w-[0.82em] translate-y-[0.1em] items-center justify-center overflow-hidden rounded-[0.22em] bg-white align-baseline shadow-sm ring-1 ring-black/10"
      aria-hidden
    >
      <AnimatePresence mode="popLayout">
        <motion.span
          key={cur.src}
          initial={{ opacity: 0, rotateX: -90 }}
          animate={{ opacity: 1, rotateX: 0 }}
          exit={{ opacity: 0, rotateX: 90 }}
          transition={{ duration: 0.4, ease: easeOut }}
          className="absolute inset-0 flex items-center justify-center p-[0.14em]"
        >
          <Image src={cur.src} alt={cur.label} width={28} height={28} className="h-full w-full object-contain" />
        </motion.span>
      </AnimatePresence>
    </span>
  );
}

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
    sources: ["Slack", "Gmail"],
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

const CHANNELS = ["team-leads", "sales-support", "general", "announcements"];

function BotAvatar({ size = 36 }: { size?: number }) {
  return (
    <span
      className="flex shrink-0 items-center justify-center overflow-hidden rounded-lg bg-white ring-1 ring-black/10"
      style={{ height: size, width: size }}
    >
      <Image src="/brand/continuum-mark.png" alt="Continuum" width={size - 10} height={size - 10} className="object-contain" />
    </span>
  );
}

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
      <div className="mx-auto max-w-5xl">
        {/* Editorial header */}
        <Reveal className="mx-auto max-w-2xl text-center">
          <div className="inline-flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
            <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[var(--charcoal-muted)]">
              Slack Live Integration
            </p>
          </div>
          <h2 className="mt-4 font-serif text-4xl leading-[1.08] text-[var(--charcoal)] md:text-6xl tracking-tight">
            Continuum lives <RotatingSourceIcon /> <span className="italic">where your team works.</span>
          </h2>
          <p className="mt-5 text-base leading-relaxed text-[var(--charcoal-muted)]">
            Ask right in a channel or DM. Continuum answers with structured Block Kit — state, history,
            and verifiable citations — not another thread to dig through.
          </p>
        </Reveal>

        {/* Step navigator */}
        <Reveal delay={0.05} className="mx-auto mt-8 flex max-w-md flex-wrap items-center justify-center gap-2">
          {["1. Query", "2. Answer", "3. Handoff", "4. Update"].map((label, idx) => (
            <button
              key={label}
              type="button"
              onClick={() => { setAutoPlay(false); setActiveStep(idx); }}
              className={`rounded-full px-4 py-1.5 text-xs font-semibold transition-all ${
                activeStep === idx
                  ? "bg-[var(--charcoal)] text-white shadow-sm"
                  : "bg-white text-[var(--charcoal-muted)] border border-[var(--paper-border)] hover:text-[var(--charcoal)]"
              }`}
            >
              {label}
            </button>
          ))}
        </Reveal>

        {/* Slack window */}
        <Reveal delay={0.1} className="mt-10">
          <div className="flex h-[560px] overflow-hidden rounded-2xl border border-black/10 bg-white shadow-[0_30px_80px_-20px_rgba(15,23,42,0.28)]">
            {/* Workspace rail */}
            <div className="hidden w-[58px] flex-col items-center gap-3 py-3 sm:flex" style={{ background: AUBERGINE_RAIL }}>
              <span className="flex h-9 w-9 items-center justify-center overflow-hidden rounded-xl bg-white ring-2 ring-white/20">
                <Image src="/brand/continuum-mark.png" alt="Continuum" width={22} height={22} className="object-contain" />
              </span>
              <div className="mt-1 flex flex-col items-center gap-3.5 text-white/60">
                {["🏠", "✉︎", "🔔", "⌗"].map((g, i) => (
                  <span key={i} className={`flex h-8 w-8 items-center justify-center rounded-lg text-sm ${i === 0 ? "bg-white/15 text-white" : ""}`}>{g}</span>
                ))}
              </div>
              <span className="mt-auto flex h-8 w-8 items-center justify-center rounded-full bg-white/10 text-sm">🧑</span>
            </div>

            {/* Channel sidebar */}
            <div className="hidden w-[200px] flex-col text-white/85 md:flex" style={{ background: AUBERGINE }}>
              <div className="flex items-center justify-between border-b border-white/10 px-4 py-3.5">
                <span className="text-[15px] font-bold text-white">Redwood</span>
                <span className="text-white/50">⌄</span>
              </div>
              <div className="flex-1 overflow-hidden px-2 py-3 text-sm">
                <div className="space-y-0.5">
                  {["Threads", "Drafts & sent"].map((x) => (
                    <div key={x} className="rounded-md px-2 py-1 text-white/70">{x}</div>
                  ))}
                </div>
                <p className="mt-4 px-2 text-xs font-semibold text-white/50">Channels</p>
                <div className="mt-1 space-y-0.5">
                  {CHANNELS.map((ch) => (
                    <div
                      key={ch}
                      className="flex items-center gap-1.5 rounded-md px-2 py-1"
                      style={ch === "team-leads" ? { background: SLACK_ACTIVE, color: "#fff" } : undefined}
                    >
                      <span className="text-white/50">#</span>
                      <span className={ch === "team-leads" ? "font-semibold text-white" : "text-white/70"}>{ch}</span>
                    </div>
                  ))}
                </div>
                <p className="mt-4 px-2 text-xs font-semibold text-white/50">Apps</p>
                <div className="mt-1 flex items-center gap-2 rounded-md px-2 py-1.5">
                  <BotAvatar size={22} />
                  <span className="text-white/80">Continuum</span>
                  <span className="ml-auto h-2 w-2 rounded-full bg-emerald-400" />
                </div>
              </div>
            </div>

            {/* Main pane */}
            <div className="flex flex-1 flex-col bg-white">
              {/* channel header */}
              <div className="flex items-center justify-between border-b border-black/[0.08] px-5 py-3.5">
                <div className="flex items-center gap-2 text-[var(--charcoal)]">
                  <span className="font-bold text-slate-400">#</span>
                  <span className="text-[15px] font-bold">team-leads</span>
                  <span className="text-slate-400">⌄</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-emerald-500" />
                  <span className="font-mono text-[11px] text-slate-500">Continuum · Active</span>
                </div>
              </div>

              {/* messages */}
              <div className="flex-1 space-y-5 overflow-y-auto px-5 py-5">
                <AnimatePresence mode="popLayout">
                  {SLACK_TIMELINE.slice(0, activeStep + 1).map((msg) => (
                    <motion.div
                      key={msg.step}
                      initial={{ opacity: 0, y: 14 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -10 }}
                      transition={{ duration: 0.4, ease: easeOut }}
                      className="flex items-start gap-3"
                    >
                      {msg.isBot ? (
                        <BotAvatar />
                      ) : (
                        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-base ring-1 ring-black/5">
                          {msg.avatar}
                        </span>
                      )}

                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="text-[15px] font-bold text-[var(--charcoal)]">{msg.user}</span>
                          {msg.isBot && (
                            <span className="rounded bg-slate-200 px-1.5 py-[1px] text-[9px] font-bold uppercase text-slate-600">
                              APP
                            </span>
                          )}
                          <span className="font-mono text-[10px] text-slate-400">{msg.time}</span>
                        </div>

                        {msg.content && (
                          <p className="mt-0.5 text-[15px] leading-relaxed text-[var(--charcoal-body)]">
                            {msg.content.includes("@continuum") ? (
                              <>
                                <span className="rounded bg-sky-100 px-1 py-0.5 font-medium text-sky-800">@continuum</span>
                                {msg.content.replace("@continuum", "")}
                              </>
                            ) : (
                              msg.content
                            )}
                          </p>
                        )}

                        {msg.isBot && (
                          <div className="mt-2 rounded-lg border border-black/[0.08] border-l-4 border-l-[var(--purple)] bg-[var(--paper)] p-3.5 text-[var(--charcoal)]">
                            <div className="flex items-center justify-between">
                              <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--purple)]">{msg.status}</span>
                              <span className="font-mono text-[10px] text-slate-400">valid_now</span>
                            </div>
                            <p className="mt-1 text-[15px] font-semibold">{msg.title}</p>
                            <p className="mt-0.5 text-xs text-[var(--charcoal-muted)]">{msg.subtitle}</p>
                            {msg.sources && (
                              <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-black/[0.06] pt-3">
                                <span className="text-[10px] font-semibold uppercase text-slate-400">Grounded in</span>
                                {msg.sources.map((s) => (
                                  <SourceBadge key={s} source={s} size="xs" />
                                ))}
                              </div>
                            )}
                          </div>
                        )}

                        {msg.highlight && (
                          <div className="mt-2 inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-emerald-800">
                            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-ping" />
                            {msg.highlight}
                          </div>
                        )}
                      </div>
                    </motion.div>
                  ))}
                </AnimatePresence>
              </div>

              {/* message input */}
              <div className="px-5 pb-5">
                <div className="flex items-center gap-2 rounded-xl border border-black/15 px-3 py-2.5 text-slate-400">
                  <span className="text-lg leading-none">+</span>
                  <span className="text-sm">Message #team-leads</span>
                  <span className="ml-auto text-slate-300">➤</span>
                </div>
              </div>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}

const MEMORY_STAGES = [
  {
    tag: "State Before",
    title: "Morgan owns Acme",
    body: "Resolved from a Slack message — the first evidence enters company memory.",
    tone: "neutral",
  },
  {
    tag: "New Information",
    title: "Ownership transfers to Priya",
    body: "A Gmail handoff arrives (effective Aug 5). Continuum ingests it automatically.",
    tone: "emerald",
  },
  {
    tag: "State After",
    title: "Priya owns Acme now",
    body: "State updates without a manual rebuild. Lineage preserved: Morgan → Priya.",
    tone: "purple",
  },
];

export function MemoryUpdateSection() {
  const [step, setStep] = useState(1);

  useEffect(() => {
    const t = setInterval(() => setStep((s) => (s >= 3 ? 1 : s + 1)), 2600);
    return () => clearInterval(t);
  }, []);

  return (
    <section className="border-t border-black/[0.06] bg-white px-6 py-28">
      <div className="mx-auto max-w-5xl text-center">
        <Reveal>
          <div className="inline-flex items-center gap-2 rounded-full border border-black/[0.08] bg-[var(--paper)] px-3.5 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--charcoal-muted)]">
            Live Memory Loop
          </div>
          <h2 className="mt-4 font-serif text-4xl leading-[1.08] text-[var(--charcoal)] md:text-6xl tracking-tight">
            Watch company memory <span className="italic">take shape.</span>
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-base leading-relaxed text-[var(--charcoal-muted)]">
            Each new signal adds a node. Continuum resolves the identities, links the evidence, and
            keeps the timeline — the graph grows as your company talks.
          </p>
        </Reveal>

        <Reveal delay={0.08}>
          <div className="mt-14 grid items-center gap-8 lg:grid-cols-[1.25fr_1fr]">
            {/* growing graph */}
            <div className="relative overflow-hidden rounded-3xl border border-[var(--paper-border)] bg-[var(--paper)] p-4 shadow-[var(--shadow-soft)]">
              <EmergingMemoryGraph step={step} className="h-[300px] w-full" />
            </div>

            {/* synced stage captions */}
            <div className="space-y-3 text-left">
              {MEMORY_STAGES.map((s, i) => {
                const active = step === i + 1;
                const done = step > i + 1;
                const accent =
                  s.tone === "emerald" ? "var(--emerald)" : s.tone === "purple" ? "var(--purple)" : "var(--charcoal-muted)";
                return (
                  <button
                    key={s.tag}
                    type="button"
                    onClick={() => setStep(i + 1)}
                    className={`w-full rounded-2xl border p-4 text-left transition-all ${
                      active
                        ? "border-[var(--purple-border)] bg-white shadow-[var(--shadow-soft)]"
                        : "border-[var(--paper-border)] bg-white/60 hover:bg-white"
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <span
                        className="flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold text-white"
                        style={{ background: active || done ? accent : "var(--charcoal-faint)" }}
                      >
                        {done ? "✓" : i + 1}
                      </span>
                      <span className="font-mono text-[10px] font-semibold uppercase tracking-wider" style={{ color: accent }}>
                        {s.tag}
                      </span>
                    </div>
                    <p className={`mt-2 text-lg font-semibold ${active ? "text-[var(--charcoal)]" : "text-[var(--charcoal-muted)]"}`}>
                      {s.title}
                    </p>
                    <p className="mt-1 text-xs leading-relaxed text-[var(--charcoal-muted)]">{s.body}</p>
                  </button>
                );
              })}
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
