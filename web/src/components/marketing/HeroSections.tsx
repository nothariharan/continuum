"use client";

import { motion } from "framer-motion";
import { Reveal, Stagger, StaggerItem } from "@/components/ui/motion";

export function HowItWorksSection() {
  const stages = [
    {
      step: "01",
      title: "Ingest",
      body: "Messages, emails, commits, and tickets stream in and become immutable, timestamped artifacts — quoted history and duplicates handled.",
    },
    {
      step: "02",
      title: "Understand",
      body: "Handles resolve to canonical people and accounts. Atomic claims are extracted with validity intervals, so state has a past and a present.",
    },
    {
      step: "03",
      title: "Remember",
      body: "The graph resolves current state, keeps every transition, flags contradictions, and hands back answers with the evidence still attached.",
    },
  ];

  const flow = ["Raw message", "Canonical artifact", "Atomic claim", "Resolved entity", "Company state"];

  return (
    <section id="how-it-works" className="border-y border-[var(--paper-border)] bg-white px-6 py-28 md:py-32">
      <div className="mx-auto max-w-6xl">
        <Reveal className="max-w-2xl">
          <span className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--charcoal-muted)]">
            How it works
          </span>
          <h2 className="mt-4 font-serif text-4xl leading-[1.08] text-[var(--charcoal)] md:text-6xl">
            From raw chatter <span className="italic">to resolved truth.</span>
          </h2>
          <p className="mt-5 max-w-xl text-lg leading-relaxed text-[var(--charcoal-muted)]">
            A strict separation of layers keeps every answer deterministic and traceable — no opaque
            guesses, no black box.
          </p>
        </Reveal>

        <Stagger className="mt-14 grid gap-5 md:grid-cols-3">
          {stages.map((stage) => (
            <StaggerItem key={stage.title}>
              <motion.div
                whileHover={{ y: -6 }}
                transition={{ type: "spring", stiffness: 300, damping: 22 }}
                className="group h-full rounded-3xl border border-[var(--paper-border)] bg-white p-7 shadow-[var(--shadow-subtle)] transition-all hover:border-[var(--purple-border)] hover:shadow-[var(--shadow-soft)]"
              >
                <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-[var(--purple-soft)] font-mono text-xs font-semibold text-[var(--purple)] transition-transform duration-300 group-hover:scale-110">
                  {stage.step}
                </span>
                <p className="mt-4 text-xl font-semibold text-[var(--charcoal)]">{stage.title}</p>
                <p className="mt-2.5 text-sm leading-relaxed text-[var(--charcoal-muted)]">{stage.body}</p>
              </motion.div>
            </StaggerItem>
          ))}
        </Stagger>

        <Reveal delay={0.1}>
          <div className="mt-6 flex flex-wrap items-center justify-center gap-x-2 gap-y-3 rounded-3xl border border-[var(--paper-border)] bg-[var(--paper)] px-6 py-6">
            {flow.map((node, i) => (
              <div key={node} className="flex items-center gap-2">
                <span className="rounded-full border border-[var(--paper-border)] bg-white px-3.5 py-1.5 text-xs font-medium text-[var(--charcoal)]">
                  {node}
                </span>
                {i < flow.length - 1 && <span className="text-[var(--charcoal-faint)]" aria-hidden>→</span>}
              </div>
            ))}
          </div>
        </Reveal>
      </div>
    </section>
  );
}
