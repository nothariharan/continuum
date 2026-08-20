"use client";

import Link from "next/link";
import Image from "next/image";
import { motion } from "framer-motion";
import { Reveal } from "@/components/ui/motion";
import { LogoMark } from "@/components/ui/LogoMark";

/* Overlapping icon stack that fans out + lifts when its card is hovered. */
type StackIcon = { src: string; alt: string };

const CONNECT_ICONS: StackIcon[] = [
  { src: "/brand/slack.svg", alt: "Slack" },
  { src: "/brand/gmail.svg", alt: "Gmail" },
  { src: "/brand/notion.svg", alt: "Notion" },
  { src: "/brand/linear.svg", alt: "Linear" },
  { src: "/brand/github.svg", alt: "GitHub" },
  { src: "/brand/drive.svg", alt: "Drive" },
];

const AGENT_ICONS: StackIcon[] = [
  { src: "/brand/claude.svg", alt: "Claude" },
  { src: "/brand/openai.svg", alt: "OpenAI Codex" },
  { src: "/brand/cursor.svg", alt: "Cursor" },
  { src: "/brand/copilot.svg", alt: "GitHub Copilot" },
  { src: "/brand/gemini.svg", alt: "Gemini" },
];

function PopStack({ icons }: { icons: StackIcon[] }) {
  const n = icons.length;
  return (
    <div className="pop-stack flex items-center">
      {icons.map((ic, i) => (
        <span
          key={ic.alt}
          title={ic.alt}
          className="flex h-10 w-10 items-center justify-center rounded-full bg-white shadow-md ring-1 ring-black/5"
          style={
            {
              marginLeft: i === 0 ? 0 : -14,
              zIndex: i,
              "--pop-x": `${(i - (n - 1) / 2) * 13}px`,
            } as React.CSSProperties
          }
        >
          <Image src={ic.src} alt={ic.alt} width={22} height={22} className="h-[22px] w-[22px] object-contain" />
        </span>
      ))}
    </div>
  );
}

/**
 * ClosingCTA — the editorial "how you connect + how it scales" band.
 * Two honest promises: connect any workplace source, and query the whole
 * canonical memory through one MCP endpoint backed by a harness built to
 * scale across 1B+ targeted documents.
 */
export function ClosingCTA() {
  return (
    <section className="relative overflow-hidden border-t border-[var(--paper-border)] bg-[var(--paper)] px-6 py-28 md:py-36">
      <div aria-hidden className="hero-glow opacity-50" />
      <div className="relative mx-auto max-w-5xl">
        <Reveal className="max-w-2xl">
          <span className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--charcoal-muted)]">
            Connect & Scale
          </span>
          <h2 className="mt-4 font-serif text-4xl leading-[1.08] text-[var(--charcoal)] md:text-6xl text-balance">
            Bring your workplace.
            <br />
            <span className="italic">We&apos;ll remember all of it.</span>
          </h2>
          <p className="mt-5 max-w-xl text-lg leading-relaxed text-[var(--charcoal-muted)]">
            Point Continuum at the tools your company runs on — Slack, Gmail, or anything with an
            API — and every message, decision, and handoff flows into one temporal memory.
          </p>
        </Reveal>

        <div className="mt-14 grid gap-4 md:grid-cols-2">
          <Reveal>
            <motion.div
              whileHover={{ y: -6 }}
              transition={{ type: "spring", stiffness: 300, damping: 22 }}
              className="group relative h-full rounded-3xl border border-[var(--paper-border)] bg-[var(--surface)] p-8 shadow-[var(--shadow-subtle)] transition-all hover:border-[var(--purple-border)] hover:shadow-[var(--shadow-soft)]"
            >
              {/* connectors — overlap, then fan out on hover */}
              <div className="absolute bottom-6 right-6">
                <PopStack icons={CONNECT_ICONS} />
              </div>
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--purple-soft)] text-[var(--purple)] transition-transform duration-500 group-hover:rotate-90">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                  <path d="M12 3v18M3 12h18" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
                  <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.6" />
                </svg>
              </div>
              <h3 className="mt-5 text-xl font-semibold text-[var(--charcoal)]">
                Connect any source
              </h3>
              <p className="mt-2.5 text-sm leading-relaxed text-[var(--charcoal-muted)]">
                No lock-in to a single chat tool. Each connector normalizes into the same canonical
                model, so Slack and Gmail converge on one answer — with the original evidence attached.
              </p>
              <Link
                href="/connectors"
                className="mt-6 inline-flex items-center gap-1.5 text-sm font-semibold text-[var(--purple)] hover:text-[var(--purple-hover)]"
              >
                View connectors
                <span aria-hidden className="transition-transform duration-200 group-hover:translate-x-1">→</span>
              </Link>
            </motion.div>
          </Reveal>

          <Reveal delay={0.08}>
            <motion.div
              whileHover={{ y: -6 }}
              transition={{ type: "spring", stiffness: 300, damping: 22 }}
              className="group relative h-full rounded-3xl border border-[var(--charcoal)] bg-[var(--charcoal)] p-8 text-white shadow-[var(--shadow-elevated)]"
            >
              <div
                aria-hidden
                className="pointer-events-none absolute -right-10 -top-12 h-48 w-48 animate-glow-pulse rounded-full bg-[radial-gradient(circle,rgba(99,102,241,0.35),transparent_70%)] blur-2xl"
              />
              {/* agents & copilots that speak MCP — overlap, then fan out on hover */}
              <div className="absolute right-6 top-6 z-20">
                <PopStack icons={AGENT_ICONS} />
              </div>
              <div className="relative z-10">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/10 text-white transition-transform duration-500 group-hover:scale-110">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                    <rect x="3" y="4" width="18" height="5" rx="1.4" stroke="currentColor" strokeWidth="1.6" />
                    <rect x="3" y="15" width="18" height="5" rx="1.4" stroke="currentColor" strokeWidth="1.6" />
                    <path d="M7 6.5h.01M7 17.5h.01" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                  </svg>
                </div>
                <h3 className="mt-5 text-xl font-semibold">
                  One MCP endpoint, 1B+ documents
                </h3>
                <p className="mt-2.5 text-sm leading-relaxed text-white/70">
                  Agents and copilots talk to Continuum over MCP — an adapter over the same canonical
                  query layer, never a second brain. A purpose-built harness around HydraDB is
                  engineered to query across 1B+ targeted documents without losing provenance.
                </p>
                <Link
                  href="/mcp"
                  className="mt-6 inline-flex items-center gap-1.5 text-sm font-semibold text-white hover:text-white/80"
                >
                  Explore the MCP layer
                  <span aria-hidden className="transition-transform duration-200 group-hover:translate-x-1">→</span>
                </Link>
              </div>
            </motion.div>
          </Reveal>
        </div>

        <Reveal delay={0.12}>
          <div className="mt-10 flex flex-col items-start gap-4 sm:flex-row sm:items-center">
            <Link
              href="/demo?autoplay=1"
              className="group inline-flex items-center gap-2 rounded-full bg-[var(--charcoal)] px-8 py-4 text-sm font-semibold text-white shadow-md transition-all hover:bg-black hover:scale-[1.03] hover:shadow-lg active:scale-[0.99]"
            >
              <span>See it in motion</span>
              <span className="text-white/50 transition-transform duration-200 group-hover:translate-x-1" aria-hidden>→</span>
            </Link>
            <Link
              href="/graph?entity=account:acme"
              className="group inline-flex items-center gap-2 rounded-full border border-[var(--paper-border-strong)] bg-white px-8 py-4 text-sm font-semibold text-[var(--charcoal)] transition-all hover:border-[var(--purple)] hover:text-[var(--purple)] hover:scale-[1.03] active:scale-[0.99]"
            >
              <span>Open the knowledge graph</span>
              <span className="text-[var(--charcoal-faint)] transition-transform duration-200 group-hover:translate-x-1 group-hover:text-[var(--purple)]" aria-hidden>→</span>
            </Link>
          </div>
        </Reveal>
      </div>
    </section>
  );
}

/**
 * CTA — reusable editorial closing band used by the product/sub pages.
 * Kept prop-compatible with the original API.
 */
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
    <section className="relative overflow-hidden border-t border-[var(--paper-border)] bg-[var(--paper)] px-6 py-28 md:py-32">
      <div aria-hidden className="hero-glow opacity-40" />
      <div className="relative mx-auto max-w-3xl text-center">
        <Reveal>
          <span className="inline-flex rounded-full border border-[var(--paper-border)] bg-white/80 px-4 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-[var(--purple)]">
            Company Memory
          </span>
          <h2 className="mt-6 whitespace-pre-line font-serif text-4xl leading-[1.1] text-[var(--charcoal)] md:text-5xl text-balance">
            {title}
          </h2>
          <p className="mx-auto mt-5 max-w-lg text-base leading-relaxed text-[var(--charcoal-muted)]">
            Grounded, evidence-backed answers over one canonical memory — not fragile keyword search
            or a hallucinating chatbot.
          </p>
          <div className="mt-9 flex flex-wrap items-center justify-center gap-3">
            <Link
              href={primaryHref}
              className="inline-flex items-center gap-2 rounded-full bg-[var(--charcoal)] px-8 py-4 text-sm font-semibold text-white shadow-md transition hover:bg-black hover:scale-[1.02]"
            >
              <span>{primaryLabel}</span>
              <span className="text-white/50" aria-hidden>→</span>
            </Link>
            <Link
              href={secondaryHref}
              className="inline-flex items-center gap-2 rounded-full border border-[var(--paper-border-strong)] bg-white px-8 py-4 text-sm font-semibold text-[var(--charcoal)] transition hover:border-[var(--purple)] hover:text-[var(--purple)]"
            >
              <span>{secondaryLabel}</span>
            </Link>
          </div>
        </Reveal>
      </div>
    </section>
  );
}

const FOOTER_LINKS = [
  {
    heading: "Integrate",
    links: [
      { label: "Slack Setup", href: "/slack" },
      { label: "Use via MCP", href: "/mcp" },
    ],
  },
  {
    heading: "Explore",
    links: [{ label: "Live Demo", href: "/demo" }],
  },
];

export function Footer() {
  return (
    <footer className="border-t border-white/10 bg-[#0a0e1a] px-6 py-16 text-white">
      <div className="mx-auto flex max-w-6xl flex-col gap-12 lg:flex-row lg:justify-between">
        <div className="max-w-sm">
          <Link href="/" className="group inline-flex items-center gap-2.5">
            <LogoMark size={30} />
            <span className="text-[17px] font-semibold tracking-[-0.02em] text-white">
              Continuum
            </span>
          </Link>
          <p className="mt-4 text-sm leading-relaxed text-white/55">
            One temporal memory for your whole company — fed by every tool, queried through one layer,
            grounded in real evidence.
          </p>
          <div className="mt-5 inline-flex items-center gap-2 text-xs font-medium text-emerald-400">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            HydraDB graph core · MCP adapter
          </div>
        </div>

        <div className="grid grid-cols-2 gap-12 sm:gap-16">
          {FOOTER_LINKS.map((col) => (
            <div key={col.heading}>
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-white/90">
                {col.heading}
              </p>
              <ul className="mt-4 space-y-2.5 text-sm text-white/55">
                {col.links.map((link) => (
                  <li key={link.href}>
                    <Link href={link.href} className="transition-colors hover:text-white">
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>

      <div className="mx-auto mt-14 flex max-w-6xl flex-col items-center justify-between gap-3 border-t border-white/10 pt-7 text-xs text-white/45 sm:flex-row">
        <p>© {new Date().getFullYear()} Continuum. Company memory, finally connected.</p>
        <span className="font-mono text-[11px]">Slack + Gmail → one canonical memory</span>
      </div>
    </footer>
  );
}
