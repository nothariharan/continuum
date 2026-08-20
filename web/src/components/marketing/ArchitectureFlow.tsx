"use client";

import Image from "next/image";
import Link from "next/link";
import { motion } from "framer-motion";
import { Reveal, Stagger, StaggerItem } from "@/components/ui/motion";
import { LogoMark } from "@/components/ui/LogoMark";

const SOURCES = [
  { name: "Slack", icon: "/brand/slack.svg" },
  { name: "Gmail", icon: "/brand/gmail.svg" },
  { name: "Linear", icon: "/brand/linear.svg" },
  { name: "GitHub", icon: "/brand/github.svg" },
  { name: "Drive", icon: "/brand/drive.svg" },
  { name: "Notion", icon: "/brand/notion.svg" },
];

const CORE_LAYERS = [
  { title: "Extraction", body: "Every message, email, and commit becomes an immutable, timestamped artifact." },
  { title: "Entity Resolution", body: "@priya, priya-dev and Priya S. collapse into one canonical identity." },
  { title: "Temporal State", body: "Ownership and status changes are tracked with validity intervals — past and present." },
  { title: "Conflict & Evidence", body: "Contradictions are surfaced, not hidden. Every answer keeps its source." },
];

const SURFACES = [
  { name: "Query API", desc: "Ask in plain language", href: "/query" },
  { name: "Knowledge Graph", desc: "Explore the connections", href: "/graph" },
  { name: "MCP", desc: "Plug in any agent", href: "/mcp" },
];

/** Animated flowing connector — horizontal on desktop, vertical on mobile. */
function FlowConnector() {
  return (
    <div className="flex items-center justify-center py-1 lg:px-1 lg:py-0" aria-hidden>
      <svg width="50" height="14" viewBox="0 0 50 14" fill="none" className="rotate-90 lg:rotate-0">
        <line x1="2" y1="7" x2="48" y2="7" stroke="var(--purple-border)" strokeWidth="2" strokeLinecap="round" />
        <line x1="2" y1="7" x2="42" y2="7" stroke="var(--purple)" strokeWidth="2" strokeLinecap="round" className="flow-path" />
        <path d="M41 3l5 4-5 4" stroke="var(--purple)" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </div>
  );
}

export function ArchitectureFlow() {
  return (
    <section id="architecture" className="relative bg-[var(--paper)] px-6 py-28 md:py-36">
      <div className="mx-auto max-w-6xl">
        <Reveal className="max-w-2xl">
          <span className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--charcoal-muted)]">
            The Architecture
          </span>
          <h2 className="mt-4 font-serif text-4xl leading-[1.08] text-[var(--charcoal)] md:text-6xl">
            One memory, <span className="italic">under everything.</span>
          </h2>
          <p className="mt-5 max-w-xl text-lg leading-relaxed text-[var(--charcoal-muted)]">
            Continuum ingests the tools your team already uses, resolves them into a single
            canonical model of company state, and exposes that state through a query API, a
            knowledge graph, and MCP — all reading the same source of truth.
          </p>
        </Reveal>

        <div className="mt-16 flex flex-col items-stretch gap-4 lg:flex-row lg:gap-2">
          {/* Sources */}
          <div className="flex-1 rounded-3xl border border-[var(--paper-border)] bg-[var(--surface)] p-6 shadow-[var(--shadow-soft)]">
            <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[var(--charcoal-muted)]">
              Your workplace
            </p>
            <Stagger className="mt-5 grid grid-cols-2 gap-2.5">
              {SOURCES.map((s) => (
                <StaggerItem key={s.name}>
                  <motion.div
                    whileHover={{ y: -3, scale: 1.02 }}
                    transition={{ type: "spring", stiffness: 400, damping: 22 }}
                    className="flex items-center gap-2.5 rounded-xl border border-[var(--paper-border)] bg-white px-3 py-2.5 transition-colors hover:border-[var(--purple-border)] hover:shadow-[var(--shadow-subtle)]"
                  >
                    <Image src={s.icon} alt="" width={17} height={17} className="object-contain" />
                    <span className="text-sm font-medium text-[var(--charcoal)]">{s.name}</span>
                  </motion.div>
                </StaggerItem>
              ))}
            </Stagger>
            <p className="mt-3 rounded-xl border border-dashed border-[var(--paper-border-strong)] px-3 py-2.5 text-center text-xs font-medium text-[var(--charcoal-muted)]">
              + any source with an API
            </p>
          </div>

          <FlowConnector />

          {/* Canonical Memory Core */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
            className="group relative flex-[1.35] overflow-hidden rounded-3xl border border-[var(--purple-border)] bg-white p-7 shadow-[var(--shadow-elevated)]"
          >
            {/* subtle living glow behind the core */}
            <div
              aria-hidden
              className="pointer-events-none absolute -right-10 -top-10 z-0 h-56 w-56 animate-glow-pulse rounded-full bg-[radial-gradient(circle,var(--purple-glow),transparent_70%)] blur-2xl"
            />

            <div className="relative z-10">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <LogoMark size={26} />
                  <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-[var(--purple)]">
                    Continuum
                  </p>
                </div>
                <span className="rounded-full bg-[var(--emerald-soft)] px-2.5 py-0.5 font-mono text-[9px] font-semibold uppercase tracking-wider text-[var(--emerald)]">
                  Canonical Memory
                </span>
              </div>

              <div className="mt-5 grid gap-2.5 sm:grid-cols-2">
                {CORE_LAYERS.map((layer) => (
                  <motion.div
                    key={layer.title}
                    whileHover={{ y: -3 }}
                    transition={{ type: "spring", stiffness: 350, damping: 22 }}
                    className="rounded-2xl border border-[var(--paper-border)] bg-[var(--paper)]/90 p-4 backdrop-blur-sm transition-colors hover:border-[var(--purple-border)]"
                  >
                    <p className="text-sm font-semibold text-[var(--charcoal)]">{layer.title}</p>
                    <p className="mt-1.5 text-xs leading-relaxed text-[var(--charcoal-muted)]">{layer.body}</p>
                  </motion.div>
                ))}
              </div>

              <div className="mt-4 flex items-center justify-center gap-2 rounded-2xl bg-[var(--charcoal)] px-4 py-3 text-center">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[var(--emerald)]" />
                <span className="font-mono text-[11px] font-semibold uppercase tracking-[0.18em] text-white/70">
                  HydraDB graph substrate
                </span>
              </div>
            </div>
          </motion.div>

          <FlowConnector />

          {/* Surfaces */}
          <div className="flex-1 rounded-3xl border border-[var(--paper-border)] bg-[var(--surface)] p-6 shadow-[var(--shadow-soft)]">
            <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[var(--charcoal-muted)]">
              Ask it anything
            </p>
            <Stagger className="mt-5 space-y-2.5">
              {SURFACES.map((s) => (
                <StaggerItem key={s.name}>
                  <Link
                    href={s.href}
                    className="group flex items-center justify-between rounded-xl border border-[var(--paper-border)] bg-white px-4 py-3.5 transition-all hover:-translate-y-0.5 hover:border-[var(--purple-border)] hover:shadow-[var(--shadow-subtle)]"
                  >
                    <span>
                      <span className="block text-sm font-semibold text-[var(--charcoal)]">{s.name}</span>
                      <span className="block text-xs text-[var(--charcoal-muted)]">{s.desc}</span>
                    </span>
                    <span className="text-[var(--charcoal-faint)] transition-all duration-200 group-hover:translate-x-1 group-hover:text-[var(--purple)]">
                      →
                    </span>
                  </Link>
                </StaggerItem>
              ))}
            </Stagger>
          </div>
        </div>
      </div>
    </section>
  );
}
