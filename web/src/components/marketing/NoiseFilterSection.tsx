"use client";

import { FunnelChart, type FunnelStage } from "@/components/ui/funnel-chart";
import { Reveal } from "@/components/ui/motion";

/**
 * NoiseFilterSection — shows how Continuum distills the firehose of company
 * chatter down to one grounded answer. The funnel narrows from raw signals to
 * a resolved fact; each stage maps to a real step in the pipeline.
 */

const STAGES: FunnelStage[] = [
  { label: "Raw signals", value: 1_000_000, displayValue: "1M+" },
  { label: "Deduplicated", value: 380_000, displayValue: "380k" },
  { label: "Resolved entities", value: 92_000, displayValue: "92k" },
  { label: "Temporal claims", value: 24_000, displayValue: "24k" },
  { label: "Grounded answer", value: 12_000, displayValue: "1" },
];

const STEPS = [
  { title: "Dedupe", body: "Quoted email history and reposted messages collapse to a single artifact." },
  { title: "Resolve", body: "Aliases across tools converge onto one canonical person, account, or project." },
  { title: "Bound in time", body: "Each claim gets a validity interval, so state has a past and a present." },
  { title: "Ground", body: "What survives is one answer — with the original evidence still attached." },
];

export function NoiseFilterSection() {
  return (
    <section className="border-y border-[var(--paper-border)] bg-[var(--surface)] px-6 py-28 md:py-36">
      <div className="mx-auto max-w-6xl">
        <Reveal className="max-w-2xl">
          <span className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--charcoal-muted)]">
            Signal, not noise
          </span>
          <h2 className="mt-4 font-serif text-4xl leading-[1.08] text-[var(--charcoal)] md:text-6xl">
            We filter the noise out of <span className="italic">everything you know.</span>
          </h2>
          <p className="mt-5 max-w-xl text-lg leading-relaxed text-[var(--charcoal-muted)]">
            Millions of raw signals stream across your tools. Continuum narrows them —
            deduping, resolving identities, bounding claims in time — until what&apos;s left is one
            grounded, current answer.
          </p>
        </Reveal>

        <Reveal delay={0.1} className="mt-14">
          <div className="mx-auto max-w-4xl rounded-3xl border border-[var(--paper-border)] bg-white p-5 shadow-[var(--shadow-soft)] sm:p-8">
            <FunnelChart
              data={STAGES}
              color="#6366f1"
              layers={3}
              grid
              formatPercentage={(p) => (p < 1 ? "<1%" : `${Math.round(p)}%`)}
            />
          </div>
        </Reveal>

        <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((step, i) => (
            <Reveal key={step.title} delay={0.05 * i}>
              <div className="h-full rounded-2xl border border-[var(--paper-border)] bg-white p-5 transition-colors hover:border-[var(--purple-border)] hover:shadow-[var(--shadow-subtle)]">
                <span className="font-mono text-xs font-semibold text-[var(--purple)]">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <p className="mt-2 text-base font-semibold text-[var(--charcoal)]">{step.title}</p>
                <p className="mt-1.5 text-sm leading-relaxed text-[var(--charcoal-muted)]">{step.body}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
