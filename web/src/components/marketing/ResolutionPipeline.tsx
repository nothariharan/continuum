"use client";

import Image from "next/image";
import { motion } from "framer-motion";
import { Reveal, Stagger, StaggerItem } from "@/components/ui/motion";

/* "From raw chatter to resolved truth" — the resolution pipeline, visualized.
 * Ingest -> Understand -> Remember, with a vertical pipeline rail on the right.
 * Everything is on the Continuum light theme with real brand icons + motion. */

const SOURCES = [
  { icon: "/brand/slack.svg", name: "Slack message", body: "@priya can take over the API migration", time: "10:42 AM" },
  { icon: "/brand/gmail.svg", name: "Gmail thread", body: "Re: API migration — sounds good, let's move forward.", time: "9:11 AM" },
  { icon: "/brand/github.svg", name: "GitHub commit", body: "feat(api): transfer ownership to Priya", time: "Yesterday" },
  { icon: "/brand/linear.svg", name: "Linear issue", body: "API migration ownership", time: "2 days ago" },
];

const ALIASES = ["@priya", "priya-dev", "Priya S.", "p.sharma"];

const PIPELINE = [
  { n: "01", label: "Raw message", glyph: <ChatGlyph /> },
  { n: "02", label: "Canonical artifact", glyph: <DocGlyph /> },
  { n: "03", label: "Atomic claim", glyph: <SparkGlyph /> },
  { n: "04", label: "Resolved entity", glyph: <PersonGlyph /> },
  { n: "05", label: "Company state", glyph: <BankGlyph /> },
];

export function ResolutionPipeline() {
  return (
    <section id="how-it-works" className="border-y border-[var(--paper-border)] bg-white px-6 py-28 md:py-32">
      <div className="mx-auto max-w-[1440px]">
        {/* header */}
        <Reveal className="mx-auto max-w-2xl text-center">
          <span className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--purple)]">
            How Continuum works
          </span>
          <h2 className="mt-3 font-serif text-4xl leading-[1.05] text-[var(--charcoal)] md:text-6xl">
            From raw chatter <span className="italic">to resolved truth.</span>
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-base leading-relaxed text-[var(--charcoal-muted)]">
            A strict separation of layers keeps every answer deterministic and traceable — no opaque
            guesses, no black box.
          </p>
        </Reveal>

        <div className="mt-14 grid gap-6 lg:grid-cols-[1fr_260px]">
          {/* main pipeline panel */}
          <div className="space-y-5 rounded-3xl border border-[var(--paper-border)] bg-[var(--paper)] p-5 md:p-7 shadow-[var(--shadow-soft)]">
            {/* 01 Ingest */}
            <Row n="01" title="Ingest" body="Messages, emails, commits, and tickets stream in and become immutable, timestamped artifacts.">
              <Stagger className="grid gap-2.5 sm:grid-cols-2 xl:grid-cols-4">
                {SOURCES.map((s) => (
                  <StaggerItem key={s.name}>
                    <motion.div
                      whileHover={{ y: -4 }}
                      transition={{ type: "spring", stiffness: 350, damping: 22 }}
                      className="h-full rounded-2xl border border-[var(--paper-border)] bg-white p-3.5 shadow-[var(--shadow-subtle)]"
                    >
                      <div className="flex items-center gap-2">
                        <Image src={s.icon} alt="" width={16} height={16} className="h-4 w-4 object-contain" />
                        <span className="text-xs font-semibold text-[var(--charcoal)]">{s.name}</span>
                      </div>
                      <p className="mt-2 text-[13px] leading-snug text-[var(--charcoal-body)]">{s.body}</p>
                      <p className="mt-2 text-right font-mono text-[10px] text-[var(--charcoal-faint)]">{s.time}</p>
                    </motion.div>
                  </StaggerItem>
                ))}
              </Stagger>
              <Connector />
              <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-[var(--purple-border)] bg-[var(--purple-soft)]/50 p-4">
                <DocGlyph />
                <div className="flex-1">
                  <p className="text-sm font-semibold text-[var(--charcoal)]">Immutable, timestamped artifact</p>
                  <p className="text-xs text-[var(--charcoal-muted)]">Quoted history and duplicates handled.</p>
                </div>
                <span className="inline-flex items-center gap-1.5 rounded-full border border-[var(--paper-border)] bg-white px-3 py-1 text-xs font-medium text-[var(--charcoal)]">
                  Canonical artifact <span className="text-[var(--emerald)]">✓</span>
                </span>
              </div>
            </Row>

            {/* 02 Understand */}
            <Row n="02" title="Understand" body="Handles resolve to canonical people and accounts. Atomic claims are extracted with validity intervals, so state has a past and a present.">
              <div className="grid gap-2.5 md:grid-cols-3">
                <Card title="Resolve identities" glyph={<PersonGlyph />}>
                  <div className="mt-2 flex items-center gap-2.5">
                    <div className="shrink-0 space-y-1">
                      {ALIASES.map((a) => (
                        <p key={a} className="font-mono text-[11px] text-[var(--charcoal-muted)]">{a}</p>
                      ))}
                    </div>
                    <div className="shrink-0 text-[var(--charcoal-faint)]">→</div>
                    <div className="flex min-w-0 flex-1 items-center gap-2 rounded-xl border border-[var(--paper-border)] bg-white px-2.5 py-2">
                      <Monogram initials="PS" />
                      <div className="min-w-0">
                        <p className="whitespace-nowrap text-xs font-semibold text-[var(--charcoal)]">Priya Sharma</p>
                        <p className="text-[10px] text-[var(--charcoal-muted)]">Canonical person</p>
                      </div>
                    </div>
                  </div>
                </Card>

                <Card title="Extract atomic claims" glyph={<SparkGlyph />}>
                  <div className="mt-2 rounded-xl border border-[var(--paper-border)] bg-white p-3">
                    <p className="font-mono text-[9px] font-semibold uppercase tracking-wider text-[var(--purple)]">Claim</p>
                    <p className="mt-1 text-[13px] font-medium text-[var(--charcoal)]">Priya Sharma owns the API migration</p>
                    <p className="mt-2 text-[9px] font-semibold uppercase tracking-wider text-[var(--charcoal-faint)]">Source</p>
                    <div className="mt-1 flex items-center gap-1.5">
                      {["slack", "gmail", "github", "linear"].map((s) => (
                        <Image key={s} src={`/brand/${s}.svg`} alt="" width={14} height={14} className="h-3.5 w-3.5 object-contain" />
                      ))}
                    </div>
                  </div>
                </Card>

                <Card title="Bound in time" glyph={<ClockGlyph />}>
                  <div className="mt-3">
                    <div className="flex justify-between text-[9px] font-semibold uppercase tracking-wider text-[var(--charcoal-muted)]">
                      <span>Valid from</span><span>Valid to</span>
                    </div>
                    <div className="mt-1 flex justify-between text-xs font-semibold text-[var(--charcoal)]">
                      <span>Aug 14, 2026</span><span>Present</span>
                    </div>
                    <div className="relative mt-3 h-1.5 rounded-full bg-[var(--paper-muted)]">
                      <div className="absolute inset-y-0 left-0 w-full rounded-full bg-[var(--purple)]/80" />
                      <span className="absolute right-0 top-1/2 h-3 w-3 -translate-y-1/2 rounded-full border-2 border-[var(--purple)] bg-white" />
                    </div>
                  </div>
                </Card>
              </div>
            </Row>

            {/* 03 Remember */}
            <Row n="03" title="Remember" body="The graph resolves current state, keeps every transition, flags contradictions, and hands back answers with the evidence still attached.">
              <div className="grid gap-2.5 md:grid-cols-3">
                <Card title="Knowledge graph" glyph={<GraphGlyph />}>
                  <MiniGraph />
                </Card>

                <Card title="State over time" glyph={<SwapGlyph />}>
                  <div className="mt-3 flex items-center justify-between text-xs">
                    <div>
                      <p className="font-semibold text-[var(--charcoal)]">Morgan</p>
                      <p className="font-mono text-[10px] text-[var(--charcoal-muted)]">Jul – Aug 5</p>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold text-[var(--purple)]">Priya</p>
                      <p className="font-mono text-[10px] text-[var(--charcoal-muted)]">Aug 5 – now</p>
                    </div>
                  </div>
                  <div className="relative mt-3 h-1.5 rounded-full bg-[var(--paper-muted)]">
                    <div className="absolute inset-y-0 left-0 w-1/2 rounded-l-full bg-[var(--charcoal-faint)]" />
                    <div className="absolute inset-y-0 right-0 w-1/2 rounded-r-full bg-[var(--purple)]" />
                    <span className="absolute left-1/2 top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white bg-[var(--purple)]" />
                  </div>
                </Card>

                <Card title="Contradictions & evidence" glyph={<ShieldGlyph />}>
                  <div className="mt-2 rounded-xl border border-amber-200 bg-amber-50/60 p-3">
                    <p className="text-[9px] font-semibold uppercase tracking-wider text-amber-700">Contradiction detected</p>
                    <p className="mt-1 text-[11px] text-[var(--charcoal-body)]">Slack says Priya owns it</p>
                    <p className="text-[11px] text-[var(--charcoal-body)]">Email says Morgan owns it</p>
                  </div>
                  <div className="mt-2 flex items-center gap-2">
                    <span className="rounded-md border border-[var(--paper-border)] bg-white px-2 py-0.5 text-[10px] text-[var(--charcoal-muted)]">2 sources</span>
                    <Image src="/brand/slack.svg" alt="" width={13} height={13} className="h-3 w-3 object-contain" />
                    <Image src="/brand/gmail.svg" alt="" width={13} height={13} className="h-3 w-3 object-contain" />
                  </div>
                </Card>
              </div>
            </Row>
          </div>

          {/* right rail — resolution pipeline */}
          <Reveal delay={0.1}>
            <div className="rounded-3xl border border-[var(--paper-border)] bg-[var(--paper)] p-6 shadow-[var(--shadow-subtle)] lg:sticky lg:top-24">
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--charcoal-muted)]">
                The resolution pipeline
              </p>
              <div className="mt-5 space-y-1">
                {PIPELINE.map((p, i) => (
                  <div key={p.n}>
                    <motion.div
                      initial={{ opacity: 0, x: -8 }}
                      whileInView={{ opacity: 1, x: 0 }}
                      viewport={{ once: true }}
                      transition={{ delay: i * 0.08, duration: 0.4 }}
                      className="flex items-center gap-3"
                    >
                      <span className="flex h-9 w-9 items-center justify-center rounded-full border border-[var(--paper-border)] bg-white text-[var(--purple)]">
                        {p.glyph}
                      </span>
                      <div>
                        <p className="font-mono text-[10px] text-[var(--charcoal-faint)]">{p.n}</p>
                        <p className="text-sm font-semibold text-[var(--charcoal)]">{p.label}</p>
                      </div>
                    </motion.div>
                    {i < PIPELINE.length - 1 && (
                      <div className="ml-[18px] my-1 h-5 w-px bg-[var(--paper-border-strong)]" />
                    )}
                  </div>
                ))}
              </div>
            </div>
          </Reveal>
        </div>

        <Reveal delay={0.05}>
          <p className="mt-8 flex items-center justify-center gap-2 text-sm text-[var(--charcoal-muted)]">
            <ShieldGlyph />
            Every answer is traceable to the original evidence.
          </p>
        </Reveal>
      </div>
    </section>
  );
}

function Row({ n, title, body, children }: { n: string; title: string; body: string; children: React.ReactNode }) {
  return (
    <Reveal>
      <div className="grid gap-4 rounded-2xl border border-[var(--paper-border)] bg-white/60 p-4 md:grid-cols-[240px_1fr] md:p-5 lg:gap-8">
        <div>
          <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-[var(--purple-soft)] font-mono text-xs font-bold text-[var(--purple)]">
            {n}
          </span>
          <p className="mt-2 text-xl font-semibold text-[var(--charcoal)]">{title}</p>
          <p className="mt-1.5 text-xs leading-relaxed text-[var(--charcoal-muted)]">{body}</p>
        </div>
        <div>{children}</div>
      </div>
    </Reveal>
  );
}

function Card({ title, glyph, children }: { title: string; glyph: React.ReactNode; children: React.ReactNode }) {
  return (
    <motion.div
      whileHover={{ y: -4 }}
      transition={{ type: "spring", stiffness: 350, damping: 22 }}
      className="rounded-2xl border border-[var(--paper-border)] bg-white p-4 shadow-[var(--shadow-subtle)]"
    >
      <div className="flex items-center gap-2 text-[var(--purple)]">
        {glyph}
        <span className="text-sm font-semibold text-[var(--charcoal)]">{title}</span>
      </div>
      {children}
    </motion.div>
  );
}

function Connector() {
  return (
    <div className="flex justify-center py-1" aria-hidden>
      <svg width="20" height="26" viewBox="0 0 20 26" fill="none">
        <path d="M10 0v18M4 13l6 6 6-6" stroke="var(--charcoal-faint)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </div>
  );
}

function Monogram({ initials }: { initials: string }) {
  return (
    <span className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-[var(--purple)] to-[#22d3ee] text-[10px] font-bold text-white">
      {initials}
    </span>
  );
}

function MiniGraph() {
  return (
    <svg viewBox="0 0 200 96" className="mt-2 w-full" role="img" aria-label="knowledge graph">
      <line x1="40" y1="48" x2="110" y2="48" stroke="var(--purple)" strokeWidth="2" />
      <line x1="110" y1="48" x2="175" y2="48" stroke="var(--charcoal-faint)" strokeWidth="1.5" />
      <line x1="110" y1="48" x2="150" y2="20" stroke="var(--charcoal-faint)" strokeWidth="1.5" />
      <line x1="110" y1="48" x2="150" y2="78" stroke="var(--charcoal-faint)" strokeWidth="1.5" />
      <circle cx="40" cy="48" r="9" fill="#fff" stroke="var(--purple)" strokeWidth="2" />
      <rect x="90" y="40" width="40" height="16" rx="8" fill="var(--purple-soft)" stroke="var(--purple)" />
      <text x="110" y="51" textAnchor="middle" fontSize="7" fontWeight="700" fill="var(--purple)">Acme</text>
      <circle cx="150" cy="20" r="6" fill="#fff" stroke="var(--charcoal-faint)" />
      <circle cx="150" cy="78" r="6" fill="#fff" stroke="var(--charcoal-faint)" />
      <circle cx="177" cy="48" r="6" fill="#fff" stroke="var(--charcoal-faint)" />
      <text x="40" y="72" textAnchor="middle" fontSize="7" fill="var(--charcoal-muted)">Priya</text>
    </svg>
  );
}

/* -- inline glyphs ---------------------------------------------------------- */
function base(children: React.ReactNode) {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      {children}
    </svg>
  );
}
function ChatGlyph() { return base(<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />); }
function DocGlyph() {
  return (
    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[var(--purple-soft)] text-[var(--purple)]">
      {base(<><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><path d="M14 2v6h6" /></>)}
    </span>
  );
}
function SparkGlyph() { return base(<path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z" />); }
function PersonGlyph() { return base(<><circle cx="12" cy="8" r="4" /><path d="M4 21a8 8 0 0 1 16 0" /></>); }
function ClockGlyph() { return base(<><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>); }
function BankGlyph() { return base(<><path d="M3 10l9-6 9 6" /><path d="M5 10v9M19 10v9M9 10v9M15 10v9M3 21h18" /></>); }
function GraphGlyph() { return base(<><circle cx="5" cy="6" r="2" /><circle cx="19" cy="6" r="2" /><circle cx="12" cy="18" r="2" /><path d="M6.5 7.2L11 16M17.5 7.2L13 16" /></>); }
function SwapGlyph() { return base(<><path d="M4 7h13l-3-3M20 17H7l3 3" /></>); }
function ShieldGlyph() { return base(<path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6z" />); }
