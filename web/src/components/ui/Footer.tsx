"use client";

import Link from "next/link";
import Image from "next/image";
import { motion } from "framer-motion";
import { Reveal, easeOut } from "@/components/ui/motion";

export function Footer() {
  return (
    <footer className="border-t border-black/[0.08] bg-[var(--paper)] px-6 py-20">
      <div className="mx-auto grid max-w-7xl gap-12 sm:grid-cols-2 lg:grid-cols-5">
        {/* Brand Column */}
        <div className="lg:col-span-2">
          <Link href="/" className="inline-block">
            <Image
              src="/brand/continuum-logo.svg"
              alt="Continuum"
              width={140}
              height={30}
              className="text-[var(--charcoal)]"
            />
          </Link>
          <p className="mt-4 max-w-sm text-sm leading-relaxed text-[var(--charcoal-muted)]">
            A new category of company memory. Continuum turns fragmented conversations, documents,
            and decisions across enterprise tools into a persistent, temporal, explainable model of
            organizational state.
          </p>
          <div className="mt-6 flex items-center gap-3 text-xs text-[var(--charcoal-muted)]">
            <span className="flex items-center gap-1.5 font-medium text-emerald-600">
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
              Slack Live Loop
            </span>
            <span>·</span>
            <span>HydraDB Graph Core</span>
          </div>
        </div>

        {/* Product Column */}
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--charcoal)]">
            Product
          </p>
          <ul className="mt-4 space-y-2.5 text-xs text-[var(--charcoal-muted)]">
            <li>
              <a href="#memory" className="hover:text-[var(--charcoal)] transition-colors">
                Company Memory
              </a>
            </li>
            <li>
              <a href="#query" className="hover:text-[var(--charcoal)] transition-colors">
                Structured Query Engine
              </a>
            </li>
            <li>
              <Link href="/graph" className="hover:text-[var(--charcoal)] transition-colors">
                Knowledge Graph Explorer
              </Link>
            </li>
            <li>
              <a href="#slack" className="hover:text-[var(--charcoal)] transition-colors">
                Slack Live Integration
              </a>
            </li>
            <li>
              <a href="#connectors" className="hover:text-[var(--charcoal)] transition-colors">
                Connector Support
              </a>
            </li>
          </ul>
        </div>

        {/* Architecture & Interface */}
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--charcoal)]">
            Architecture
          </p>
          <ul className="mt-4 space-y-2.5 text-xs text-[var(--charcoal-muted)]">
            <li>
              <a href="#mcp" className="hover:text-[var(--charcoal)] transition-colors">
                MCP Agent Interface
              </a>
            </li>
            <li>
              <a href="#trust" className="hover:text-[var(--charcoal)] transition-colors">
                Provenance & Evidence
              </a>
            </li>
            <li>
              <a href="#timeline" className="hover:text-[var(--charcoal)] transition-colors">
                Temporal State Model
              </a>
            </li>
            <li>
              <a href="#conflict" className="hover:text-[var(--charcoal)] transition-colors">
                Conflict Resolution
              </a>
            </li>
            <li>
              <Link href="/demo" className="hover:text-[var(--charcoal)] transition-colors">
                Interactive Demo
              </Link>
            </li>
          </ul>
        </div>

        {/* Status Column */}
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--charcoal)]">
            System Status
          </p>
          <div className="mt-4 space-y-2.5 font-mono text-[11px] text-[var(--charcoal-muted)]">
            <div className="flex items-center justify-between rounded-md bg-black/[0.03] p-2">
              <span>Slack Bot</span>
              <span className="font-semibold text-emerald-600">CONNECTED</span>
            </div>
            <div className="flex items-center justify-between rounded-md bg-black/[0.03] p-2">
              <span>Query Core</span>
              <span className="font-semibold text-emerald-600">ACTIVE</span>
            </div>
            <div className="flex items-center justify-between rounded-md bg-black/[0.03] p-2">
              <span>MCP Layer</span>
              <span className="font-semibold text-[var(--purple)]">ADAPTER READY</span>
            </div>
            <div className="flex items-center justify-between rounded-md bg-black/[0.03] p-2">
              <span>Gmail OAuth</span>
              <span className="font-semibold text-zinc-400">PLANNED</span>
            </div>
          </div>
        </div>
      </div>

      <div className="mx-auto mt-16 flex max-w-7xl flex-col items-center justify-between gap-4 border-t border-black/[0.06] pt-8 text-xs text-[var(--charcoal-muted)] sm:flex-row">
        <p>© {new Date().getFullYear()} Continuum. Built for Hack Hydra Track 01.</p>
        <div className="flex items-center gap-6">
          <span className="font-mono text-[11px]">HydraDB Substrate</span>
          <span>·</span>
          <span className="font-mono text-[11px]">Strict Provenance Separation</span>
        </div>
      </div>
    </footer>
  );
}

export function CTA({
  title = "Stop searching for the thread.\nAsk your company's memory.",
  primaryHref = "/demo?autoplay=1",
  primaryLabel = "Explore Continuum",
  secondaryHref = "/graph?entity=account:acme",
  secondaryLabel = "See the knowledge graph",
}: {
  title?: string;
  primaryHref?: string;
  primaryLabel?: string;
  secondaryHref?: string;
  secondaryLabel?: string;
}) {
  return (
    <section className="relative overflow-hidden bg-gradient-to-b from-[var(--paper)] via-[#f3efe6] to-[var(--paper)] px-6 py-32">
      <div aria-hidden className="hero-glow opacity-40" />
      <div className="relative mx-auto max-w-4xl text-center">
        <Reveal>
          <span className="inline-flex rounded-full border border-black/10 bg-white/80 px-4 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--purple)]">
            Company Memory
          </span>
          <h2 className="mt-6 whitespace-pre-line font-serif text-4xl leading-[1.1] text-[var(--charcoal)] md:text-6xl text-balance">
            {title}
          </h2>
          <p className="mx-auto mt-6 max-w-xl text-base text-[var(--charcoal-muted)]">
            Move beyond fragile keyword search and hallucinating chatbots. Get grounded,
            evidence-backed answers that evolve with your team in real time.
          </p>
        </Reveal>
        <motion.div
          className="mt-10 flex flex-wrap items-center justify-center gap-4"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.15, duration: 0.55, ease: easeOut }}
        >
          <motion.div whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.98 }}>
            <Link
              href={primaryHref}
              className="inline-flex items-center gap-2 rounded-full bg-[var(--charcoal)] px-8 py-4 text-sm font-semibold text-white shadow-lg transition hover:bg-black"
            >
              <span>{primaryLabel}</span>
              <span>→</span>
            </Link>
          </motion.div>
          <motion.div whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.98 }}>
            <Link
              href={secondaryHref}
              className="inline-flex items-center gap-2 rounded-full border border-black/15 bg-white/80 px-8 py-4 text-sm font-semibold text-[var(--charcoal)] transition hover:border-[var(--purple)] hover:text-[var(--purple)]"
            >
              <span>{secondaryLabel}</span>
            </Link>
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}
