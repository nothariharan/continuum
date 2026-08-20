"use client";

import { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { motion } from "framer-motion";
import { HeroQuery } from "@/components/ui/HeroQuery";
import { AnimatedArrow, Reveal, Stagger, StaggerItem, easeOut } from "@/components/ui/motion";

export function HeroSection() {
  return (
    <section data-theme="marketing" className="relative overflow-hidden bg-[var(--paper)] px-6 pb-28 pt-20">
      <div aria-hidden className="hero-glow" />
      <div className="relative mx-auto max-w-5xl text-center">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: easeOut }}
          className="inline-flex items-center gap-2 rounded-full border border-black/[0.08] bg-white/80 px-4 py-1.5 shadow-2xs"
        >
          <span className="h-1.5 w-1.5 rounded-full bg-[var(--purple)] animate-pulse" />
          <span className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[var(--charcoal-muted)]">
            A New Category of Company Memory
          </span>
        </motion.div>

        <motion.h1
          className="mt-8 font-serif text-5xl leading-[1.04] text-[var(--charcoal)] md:text-7xl lg:text-8xl tracking-tight text-balance"
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.1, ease: easeOut }}
        >
          Your company&apos;s memory,
          <br />
          <span className="italic font-normal">finally connected.</span>
        </motion.h1>

        <motion.p
          className="mx-auto mt-7 max-w-2xl text-lg text-[var(--charcoal-muted)] leading-relaxed text-balance"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.22, ease: easeOut }}
        >
          Continuum connects conversations, documents, decisions, and relationships
          across the tools your team already uses — turning fragmented context into grounded company state.
        </motion.p>

        <motion.div
          className="mt-10 flex flex-wrap items-center justify-center gap-4"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, delay: 0.35, ease: easeOut }}
        >
          <Link
            href="/demo?autoplay=1"
            className="inline-flex items-center gap-2 rounded-full bg-[var(--charcoal)] px-8 py-3.5 text-sm font-semibold text-white shadow-md transition hover:bg-black hover:scale-[1.02]"
          >
            <span>See Continuum</span>
            <span className="text-xs text-zinc-400">→</span>
          </Link>
          <Link
            href="/graph?entity=account:acme"
            className="inline-flex items-center gap-2 rounded-full border border-black/15 bg-white/70 px-8 py-3.5 text-sm font-semibold text-[var(--charcoal)] transition hover:border-[var(--purple)] hover:text-[var(--purple)]"
          >
            <span>View Knowledge Graph</span>
          </Link>
        </motion.div>

        {/* Live-looking Animated Hero Composition */}
        <HeroQuery />
      </div>
    </section>
  );
}

export function ProblemSection() {
  const fragments = [
    { name: "Slack", icon: "/brand/slack.svg", snippet: '"Morgan handed off Acme to Priya"' },
    { name: "Gmail", icon: "/brand/gmail.svg", snippet: '"Contract signed: Acme renewal #409"' },
    { name: "Linear", icon: "/brand/linear.svg", snippet: '"ENG-84: Migration completed"' },
    { name: "GitHub", icon: "/brand/github.svg", snippet: '"CODEOWNERS update by @priya"' },
    { name: "Google Drive", icon: "/brand/drive.svg", snippet: '"Q3 Enterprise Accounts.gdoc"' },
    { name: "Notion", icon: "/brand/notion.svg", snippet: '"Engineering Decision Records 2026"' },
  ];

  return (
    <section className="border-y border-black/[0.06] bg-white px-6 py-28">
      <div className="mx-auto max-w-5xl text-center">
        <Reveal>
          <span className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--charcoal-muted)]">
            The Fragmentation Problem
          </span>
          <h2 className="mt-4 font-serif text-4xl leading-tight text-[var(--charcoal)] md:text-6xl text-balance">
            Your company&apos;s knowledge
            <br />
            <span className="italic">isn&apos;t in one place.</span>
          </h2>
        </Reveal>

        {/* Fragmented Workspace Grid */}
        <Stagger className="mt-14 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {fragments.map((item, index) => (
            <StaggerItem key={item.name}>
              <motion.div
                className="group relative rounded-2xl border border-black/[0.08] bg-[#faf8f5] p-5 text-left transition-all hover:border-[var(--purple)]/40 hover:bg-white hover:shadow-md"
                whileHover={{ y: -4 }}
                animate={{ y: [0, index % 2 === 0 ? -3 : 3, 0] }}
                transition={{ y: { duration: 4 + index * 0.4, repeat: Infinity, ease: "easeInOut" } }}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Image src={item.icon} alt={item.name} width={18} height={18} className="object-contain" />
                    <span className="text-xs font-semibold text-[var(--charcoal)]">{item.name}</span>
                  </div>
                  <span className="text-[10px] uppercase font-mono text-[var(--charcoal-muted)]">Isolated Thread</span>
                </div>
                <p className="mt-3 font-mono text-xs italic text-[var(--charcoal-muted)]">
                  {item.snippet}
                </p>
              </motion.div>
            </StaggerItem>
          ))}
        </Stagger>

        <Reveal delay={0.15}>
          <div className="mt-16 rounded-3xl border border-black/[0.06] bg-[#faf8f5] p-8 max-w-2xl mx-auto">
            <p className="font-serif text-2xl md:text-3xl text-[var(--charcoal)] leading-snug">
              &ldquo;The answer is somewhere.
              <br />
              <span className="text-[var(--purple)] font-medium">The context is everywhere.&rdquo;</span>
            </p>
            <p className="mt-4 text-sm text-[var(--charcoal-muted)]">
              Traditional enterprise search indexes keyword strings. Continuum models enterprise reality.
            </p>
          </div>
        </Reveal>
      </div>
    </section>
  );
}



export function HowItWorksSection() {
  const [activeStep, setActiveStep] = useState<number>(0);

  const stages = [
    {
      step: "01",
      title: "Ingest",
      subtitle: "Normalize Evidence",
      body: "Continuously extract raw events, messages, commits, and handoff tickets across enterprise systems into immutable canonical artifacts.",
      tags: ["Slack", "Gmail", "Linear", "GitHub"],
    },
    {
      step: "02",
      title: "Understand",
      subtitle: "Resolve Entities & Claims",
      body: "Map disparate handles (@priya, priya-dev, Priya S.) to canonical entities. Extract atomic time-stamped claims with validity intervals.",
      tags: ["Entity Resolution", "Atomic Claims", "Temporal Bounds"],
    },
    {
      step: "03",
      title: "Remember",
      subtitle: "Persist Company State",
      body: "HydraDB graph engine resolves current state, preserves historical transitions, detects contradictions, and supplies deterministic context.",
      tags: ["HydraDB Graph", "State Resolver", "Zero Hallucination"],
    },
  ];

  const pipeline = [
    { name: "Raw Message", example: '"Priya taking over Acme from Morgan today"' },
    { name: "Canonical Artifact", example: 'art_8192 { source: "slack", ts: 1722510000 }' },
    { name: "Atomic Claim", example: 'Priya OWNS Acme [valid_from: 2026-08-01]' },
    { name: "Canonical Entity", example: 'person:priya ↔ account:acme' },
    { name: "Resolved State", example: 'Current Owner: Priya (History: Morgan)' },
  ];

  return (
    <section id="how-it-works" className="border-y border-black/[0.06] bg-white px-6 py-28">
      <div className="mx-auto max-w-6xl">
        <Reveal className="text-center">
          <span className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--charcoal-muted)]">
            Transformation Architecture
          </span>
          <h2 className="mt-4 font-serif text-4xl text-[var(--charcoal)] md:text-6xl">
            How company memory is built
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-base text-[var(--charcoal-muted)]">
            A strict 5-layer separation ensures answers are deterministic, verifiable, and free of opaque LLM guesses.
          </p>
        </Reveal>

        {/* 3 Main Stages Grid */}
        <Stagger className="mt-16 grid gap-6 md:grid-cols-3">
          {stages.map((stage, index) => (
            <StaggerItem key={stage.title}>
              <motion.div
                className={`relative h-full rounded-3xl border p-8 transition-all ${
                  activeStep === index
                    ? "border-[var(--purple)] bg-[#faf8ff] shadow-md"
                    : "border-black/[0.08] bg-[#faf8f5] hover:border-black/20"
                }`}
                whileHover={{ y: -4 }}
                onClick={() => setActiveStep(index)}
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-semibold text-[var(--purple)]">
                    {stage.step}
                  </span>
                  <span className="text-[11px] font-semibold uppercase tracking-wider text-[var(--charcoal-muted)]">
                    {stage.title}
                  </span>
                </div>
                <p className="mt-4 text-xl font-semibold text-[var(--charcoal)]">{stage.subtitle}</p>
                <p className="mt-3 text-sm leading-relaxed text-[var(--charcoal-muted)]">{stage.body}</p>

                <div className="mt-6 flex flex-wrap gap-1.5">
                  {stage.tags.map((tag) => (
                    <span
                      key={tag}
                      className="rounded-full border border-black/[0.06] bg-white px-2.5 py-0.5 text-[10px] font-medium text-[var(--charcoal-muted)]"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </motion.div>
            </StaggerItem>
          ))}
        </Stagger>

        {/* Pipeline Stream Visual */}
        <Reveal delay={0.15} className="mt-16">
          <div className="pipeline-track rounded-3xl border border-black/[0.08] bg-[#faf8f5] p-8">
            <p className="text-center text-xs font-semibold uppercase tracking-[0.2em] text-[var(--charcoal-muted)] mb-6">
              Deterministic Layer Transformation
            </p>
            <div className="flex flex-wrap items-center justify-center gap-3 text-xs">
              {pipeline.map((step, index) => (
                <div key={step.name} className="flex items-center gap-3">
                  <motion.div
                    className="rounded-2xl border border-black/[0.08] bg-white p-3.5 shadow-2xs hover:border-[var(--purple)] transition-colors text-center"
                    initial={{ opacity: 0, x: -10 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: index * 0.1, duration: 0.4, ease: easeOut }}
                  >
                    <p className="font-semibold text-[var(--charcoal)]">{step.name}</p>
                    <p className="mt-1 font-mono text-[10px] text-[var(--charcoal-muted)] max-w-[170px] truncate">
                      {step.example}
                    </p>
                  </motion.div>

                  {index < pipeline.length - 1 && (
                    <span className="flex items-center text-[var(--purple)]">
                      <AnimatedArrow />
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
