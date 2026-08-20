"use client";

import { useState } from "react";
import Image from "next/image";
import { motion } from "framer-motion";
import { SourceBadge } from "@/components/ui/SourceBadge";
import { AnimatedArrow, Reveal, Stagger, StaggerItem } from "@/components/ui/motion";
import { CONNECTORS } from "@/data/demo-script";

/* -- MCP setup terminal ---------------------------------------------------- */
const MCP_TABS = [
  {
    id: "shell",
    label: "Start the server",
    file: "terminal",
    lang: "sh",
    code: `# prerequisite: the graph is running
$ make hydradb-up

# start Continuum's MCP server
$ uv run continuum-mcp
✓ Continuum MCP ready — 9 tools exposed`,
  },
  {
    id: "config",
    label: "Claude / Cursor config",
    file: "claude_desktop_config.json",
    lang: "json",
    code: `{
  "mcpServers": {
    "continuum": {
      "command": "uv",
      "args": ["run", "continuum-mcp"]
    }
  }
}`,
  },
  {
    id: "prompt",
    label: "Example prompt",
    file: "agent.txt",
    lang: "sh",
    code: `You: Who owns the Acme account now, and who had it before?

# Claude calls Continuum over MCP:
  get_current_state(account:acme)  -> Priya  (since Aug 5)
  get_history(account:acme)        -> Morgan -> Priya

✓ Priya owns Acme now. Previously Morgan.
  Grounded in Slack + Gmail.`,
  },
];

function CodeLine({ line, lang }: { line: string; lang: string }) {
  const isComment = line.trimStart().startsWith("#") || line.trimStart().startsWith("//");
  const isResult = line.trimStart().startsWith("# ->") || line.includes("->");
  const isPrompt = line.startsWith("$");
  const isOk = line.trimStart().startsWith("✓");
  let cls = "text-slate-200";
  if (isOk) cls = "text-emerald-400";
  else if (isResult && lang === "py") cls = "text-emerald-300/90";
  else if (isComment) cls = "text-slate-500";
  else if (isPrompt) cls = "text-sky-300";
  return <div className={cls}>{line || " "}</div>;
}

function McpTerminal() {
  const [tab, setTab] = useState("shell");
  const [copied, setCopied] = useState(false);
  const active = MCP_TABS.find((t) => t.id === tab) ?? MCP_TABS[0];

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(active.code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      /* clipboard unavailable */
    }
  };

  return (
    <div className="overflow-hidden rounded-2xl border border-white/10 bg-[#0b0f17] shadow-[0_30px_80px_-24px_rgba(15,23,42,0.5)]">
      {/* title bar */}
      <div className="flex items-center gap-3 border-b border-white/10 bg-[#0d1220] px-4 py-3">
        <div className="flex gap-1.5">
          <span className="h-3 w-3 rounded-full bg-[#ff5f57]" />
          <span className="h-3 w-3 rounded-full bg-[#febc2e]" />
          <span className="h-3 w-3 rounded-full bg-[#28c840]" />
        </div>
        <div className="ml-1 flex items-center gap-2">
          <Image src="/brand/hydradb.png" alt="HydraDB" width={78} height={14} className="h-3.5 w-auto object-contain opacity-90" />
          <span className="h-3 w-px bg-white/15" />
          <span className="font-mono text-[11px] text-white/50">{active.file}</span>
        </div>
        <button
          type="button"
          onClick={copy}
          className="ml-auto inline-flex items-center gap-1.5 rounded-md border border-white/15 bg-white/5 px-2.5 py-1 text-[11px] font-medium text-white/80 transition hover:bg-white/10"
        >
          {copied ? (
            <><span className="text-emerald-400">✓</span> Copied</>
          ) : (
            <><CopyGlyph /> Copy</>
          )}
        </button>
      </div>

      {/* tabs */}
      <div className="flex items-center gap-1 border-b border-white/10 bg-[#0b0f17] px-3 pt-2">
        {MCP_TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={`rounded-t-lg px-3 py-1.5 text-xs font-medium transition ${
              tab === t.id ? "bg-[#131a2b] text-white" : "text-white/45 hover:text-white/70"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* code */}
      <motion.pre
        key={tab}
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="overflow-x-auto px-5 py-4 font-mono text-[12.5px] leading-relaxed"
      >
        {active.code.split("\n").map((line, i) => (
          <CodeLine key={i} line={line} lang={active.lang} />
        ))}
        <span className="mt-1 inline-block h-3.5 w-2 animate-pulse bg-[var(--purple)]/80 align-middle" />
      </motion.pre>
    </div>
  );
}

function CopyGlyph() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <rect x="9" y="9" width="12" height="12" rx="2" />
      <path d="M5 15V5a2 2 0 0 1 2-2h10" />
    </svg>
  );
}

export function ConnectorsSection() {
  const connected = CONNECTORS.filter((c) => c.status === "connected");
  const planned = CONNECTORS.filter((c) => c.status === "planned");

  return (
    <section id="connectors" className="bg-[var(--paper)] px-6 py-28">
      <div className="mx-auto max-w-6xl">
        <Reveal>
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-[var(--purple)]" />
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--charcoal-muted)]">
              Enterprise Ecosystem
            </p>
          </div>
          <h2 className="mt-4 font-serif text-4xl text-[var(--charcoal)] md:text-6xl tracking-tight">
            Sources your company already uses.
          </h2>
          <p className="mt-4 text-base text-[var(--charcoal-muted)] max-w-xl leading-relaxed">
            Continuum bridges unstructured conversations, issue trackers, and codebases into one unified memory.
          </p>
        </Reveal>

        <div className="mt-16 grid gap-10 md:grid-cols-2">
          {/* Live Connected Sources */}
          <Reveal delay={0.05}>
            <div className="rounded-3xl border border-emerald-200 bg-emerald-50/50 p-8 shadow-xs">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-full bg-emerald-500 animate-pulse" />
                  <span className="text-xs font-semibold uppercase tracking-wider text-emerald-800">
                    Live Ingestion Active
                  </span>
                </div>
                <span className="font-mono text-[10px] text-emerald-700 bg-emerald-100/60 px-2 py-0.5 rounded-full">
                  Real-time bot loop
                </span>
              </div>

              <div className="flex flex-wrap gap-3">
                {connected.map((c) => (
                  <motion.div key={c.id} whileHover={{ scale: 1.04, y: -2 }}>
                    <SourceBadge source={c.name} status={c.status} size="lg" />
                  </motion.div>
                ))}
              </div>

              <p className="mt-6 text-xs text-[var(--charcoal-muted)] leading-relaxed">
                Slack messages, threads, mentions, and channel events are normalized and ingested directly into HydraDB.
              </p>
            </div>
          </Reveal>

          {/* Planned / Supported Sources */}
          <Reveal delay={0.1}>
            <div className="rounded-3xl border border-black/[0.08] bg-white p-8 shadow-xs">
              <div className="flex items-center justify-between mb-6">
                <span className="text-xs font-semibold uppercase tracking-wider text-[var(--charcoal-muted)]">
                  Connector Support & Extensibility
                </span>
                <span className="font-mono text-[10px] text-[var(--charcoal-muted)] bg-black/[0.04] px-2 py-0.5 rounded-full">
                  Normalized Schemas
                </span>
              </div>

              <div className="flex flex-wrap gap-2.5">
                {planned.map((c) => (
                  <motion.div key={c.id} whileHover={{ scale: 1.02 }}>
                    <SourceBadge source={c.name} status={c.status} size="md" />
                  </motion.div>
                ))}
              </div>

              <p className="mt-6 text-xs text-[var(--charcoal-muted)] leading-relaxed">
                Artifact normalization pipelines exist for Gmail, Linear, GitHub, Google Drive, Notion, Jira, and Teams.
              </p>
            </div>
          </Reveal>
        </div>

        <Reveal delay={0.15}>
          <div className="mt-8 flex items-center gap-2 rounded-2xl border border-black/[0.06] bg-[#f3efe6] px-5 py-3.5 text-xs text-[var(--charcoal-muted)]">
            <span className="font-semibold text-[var(--charcoal)]">Strict Truth in Advertising:</span>
            <span>
              Only sources marked <strong>Live</strong> reflect verified active ingestion in today&apos;s runtime. Other connectors communicate planned architectural compatibility.
            </span>
          </div>
        </Reveal>
      </div>
    </section>
  );
}

export function McpSection() {
  const [activeTool, setActiveTool] = useState<string>("get_current_state");

  const tools = [
    {
      name: "resolve_entity",
      desc: "Map fuzzy workplace mentions (@priya, priya-dev) to canonical IDs.",
      payload: '{ "mention": "@priya", "context": "slack:#leads" }',
      response: '{ "entity_id": "person:priya", "confidence": 0.98 }',
    },
    {
      name: "get_current_state",
      desc: "Query active owner, lead, or relationship for any entity.",
      payload: '{ "entity": "account:acme", "predicate": "OWNS" }',
      response: '{ "value": "Priya", "valid_from": "2026-08-01", "status": "definitive" }',
    },
    {
      name: "get_history",
      desc: "Retrieve immutable timeline of transitions and previous holders.",
      payload: '{ "entity": "account:acme", "predicate": "OWNS" }',
      response: '{ "lineage": [{ "from": "Morgan", "to": "Priya", "date": "2026-08-01" }] }',
    },
    {
      name: "get_conflicts",
      desc: "Detect contradictory claims and surface evidence for review.",
      payload: '{ "entity": "account:acme", "predicate": "OWNS" }',
      response: '{ "has_conflict": false, "competing_claims": [] }',
    },
    {
      name: "get_evidence",
      desc: "Return underlying source artifacts, timestamps, and hashes.",
      payload: '{ "entity": "account:acme", "claim_id": "clm_891a" }',
      response: '{ "source": "slack", "artifact_id": "art_slack_handoff_891", "hash": "sha256_e829fa" }',
    },
    {
      name: "get_dependencies",
      desc: "Traverse multi-hop dependencies across teams and services.",
      payload: '{ "service": "payments-service", "depth": 2 }',
      response: '{ "dependencies": ["auth-api", "postgres-core"], "maintainer": "Ravi" }',
    },
  ];

  const currentToolData = tools.find((t) => t.name === activeTool) ?? tools[1];

  return (
    <section id="mcp" className="border-y border-black/[0.06] bg-white px-6 py-28">
      <div className="mx-auto max-w-6xl">
        <Reveal>
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-[var(--purple)]" />
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--charcoal-muted)]">
              Agent Protocol
            </p>
          </div>
          <h2 className="mt-4 font-serif text-4xl text-[var(--charcoal)] md:text-6xl tracking-tight">
            Continuum is not trapped inside its UI.
          </h2>
          <p className="mt-4 text-base text-[var(--charcoal-muted)] max-w-2xl leading-relaxed">
            External AI agents connect to Continuum via the Model Context Protocol (MCP). Agents call
            the same state resolver, conflict detector, and evidence engine as Slack and the web application.
          </p>
        </Reveal>

        {/* Architecture Flow Line */}
        <Reveal delay={0.08} className="mt-12">
          <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-black/[0.08] bg-[var(--paper)] p-5 text-xs font-mono">
            {["Claude / Agent", "Continuum MCP", "Semantic tools", "Canonical company memory"].map(
              (step, idx, arr) => (
                <div key={step} className="flex items-center gap-3">
                  {step === "Canonical company memory" ? (
                    <span className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-[#0b0f17] px-3 py-2">
                      <span className="font-semibold text-white/80">{step}</span>
                      <span className="h-3.5 w-px bg-white/15" />
                      <Image src="/brand/hydradb.png" alt="HydraDB" width={64} height={12} className="h-3 w-auto object-contain" />
                    </span>
                  ) : (
                    <span className="rounded-xl border border-black/[0.08] bg-white px-3.5 py-2 font-semibold text-[var(--charcoal)] shadow-2xs">
                      {step}
                    </span>
                  )}
                  {idx < arr.length - 1 && <span className="font-bold text-[var(--purple)]">→</span>}
                </div>
              ),
            )}
          </div>
        </Reveal>

        {/* Copy-paste setup terminal */}
        <div className="mt-12 grid items-start gap-8 lg:grid-cols-[1fr_1.2fr]">
          <Reveal>
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--charcoal-muted)]">
              Wire it up
            </p>
            <h3 className="mt-3 font-serif text-3xl leading-tight text-[var(--charcoal)]">
              Point any agent at Continuum <span className="italic">in one paste.</span>
            </h3>
            <p className="mt-3 text-sm leading-relaxed text-[var(--charcoal-muted)]">
              Register the Continuum MCP server with your client, or call the adapter directly. Either
              way, your agent gets deterministic, evidence-backed company state — the same layer Slack
              and the web app read.
            </p>
            <ul className="mt-5 space-y-2 text-sm text-[var(--charcoal-body)]">
              {["Same canonical state as every surface", "Deterministic — no hallucinated ownership", "Evidence + provenance on every answer"].map((f) => (
                <li key={f} className="flex items-center gap-2">
                  <span className="flex h-4 w-4 items-center justify-center rounded-full bg-[var(--emerald-soft)] text-[9px] font-bold text-[var(--emerald)]">✓</span>
                  {f}
                </li>
              ))}
            </ul>
          </Reveal>
          <Reveal delay={0.08}>
            <McpTerminal />
          </Reveal>
        </div>

        {/* Interactive MCP Tool Inspector (Light Developer Theme) */}
        <div className="mt-12 grid gap-8 lg:grid-cols-[1fr_1.4fr]">
          {/* Tool Selector List */}
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wider text-[var(--charcoal-muted)] mb-3">
              Semantic MCP Operations:
            </p>
            {tools.map((t) => (
              <button
                key={t.name}
                type="button"
                onClick={() => setActiveTool(t.name)}
                className={`w-full rounded-2xl border p-4 text-left transition-all ${
                  activeTool === t.name
                    ? "border-[var(--purple)] bg-[var(--purple-soft)] shadow-xs"
                    : "border-black/[0.08] bg-[#faf8f5] hover:border-black/20 hover:bg-white"
                }`}
              >
                <p className="font-mono text-xs font-semibold text-[var(--charcoal)]">{t.name}()</p>
                <p className="mt-1 text-xs text-[var(--charcoal-muted)]">{t.desc}</p>
              </button>
            ))}
          </div>

          {/* JSON-RPC Inspector Terminal (Light Raycast/Linear Theme) */}
          <div className="rounded-3xl border border-black/[0.08] bg-white p-6 shadow-[0_12px_32px_-8px_rgba(15,23,42,0.06)]">
            <div className="flex items-center justify-between border-b border-black/[0.06] pb-4">
              <div className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full bg-rose-400" />
                <span className="h-2.5 w-2.5 rounded-full bg-amber-400" />
                <span className="h-2.5 w-2.5 rounded-full bg-emerald-400" />
                <span className="ml-2 font-mono text-xs font-medium text-[var(--charcoal-muted)]">mcp-rpc-inspector.json</span>
              </div>
              <span className="rounded-full bg-emerald-50 border border-emerald-200 px-2 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wider text-emerald-700">
                JSON-RPC 2.0
              </span>
            </div>

            <div className="mt-5 space-y-4 font-mono text-xs">
              <div>
                <p className="text-[10px] uppercase font-bold tracking-wider text-[var(--purple)] mb-1.5">
                  {"// Agent Tool Request:"}
                </p>
                <div className="rounded-2xl border border-black/[0.06] bg-[#faf8f5] p-4 text-[var(--charcoal)]">
                  <span className="text-slate-500 font-semibold">{`POST /mcp/tools/${currentToolData.name}\n`}</span>
                  <span className="text-[var(--charcoal-body)]">{currentToolData.payload}</span>
                </div>
              </div>

              <div>
                <p className="text-[10px] uppercase font-bold tracking-wider text-emerald-700 mb-1.5">
                  {"// Continuum Deterministic State Response:"}
                </p>
                <div className="rounded-2xl border border-emerald-200/80 bg-emerald-50/50 p-4 text-emerald-950">
                  <span>{currentToolData.response}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export function TrustSection() {
  const steps = [
    {
      level: "01. Resolved State",
      title: "Priya owns Acme now.",
      meta: "Status: Definitive (0.98 confidence)",
    },
    {
      level: "02. Atomic Claim",
      title: "Claim clm_891a: Priya OWNS Acme",
      meta: "valid_from: 2026-08-01 · method: structured_extract",
    },
    {
      level: "03. Enterprise Source",
      title: "Slack Channel #leads",
      meta: "Message ID: 1722510000.004200",
    },
    {
      level: "04. Immutable Raw Artifact",
      title: "art_slack_handoff_891",
      meta: "SHA256: 8f29ea149... (Zero Mismatch Ingestion)",
    },
  ];

  return (
    <section id="trust" className="bg-[#faf8f5] px-6 py-28">
      <div className="mx-auto max-w-4xl text-center">
        <Reveal>
          <div className="inline-flex items-center gap-2 rounded-full bg-white border border-black/[0.08] px-3.5 py-1 text-xs font-semibold uppercase tracking-wider text-[var(--charcoal-muted)] shadow-2xs">
            Provenance & Verification
          </div>
          <h2 className="mt-4 font-serif text-4xl text-[var(--charcoal)] md:text-6xl tracking-tight">
            Answers you can verify.
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-base text-[var(--charcoal-muted)] leading-relaxed">
            Every answer can be traced back to the exact evidence that supports it — with cryptographic hashes and source metadata.
          </p>
        </Reveal>

        {/* Vertical Provenance Drill-Down */}
        <div className="mx-auto mt-16 max-w-lg space-y-4 text-left">
          {steps.map((s, index) => (
            <Reveal key={s.level} delay={index * 0.08}>
              <motion.div
                className="group rounded-2xl border border-black/[0.08] bg-white p-5 shadow-xs transition-all hover:border-[var(--purple)] hover:shadow-md"
                whileHover={{ x: 4 }}
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[10px] font-semibold uppercase tracking-wider text-[var(--purple)]">
                    {s.level}
                  </span>
                  <span className="text-[10px] text-[var(--charcoal-muted)] font-mono">Layer {index + 1}</span>
                </div>
                <p className="mt-2 text-base font-semibold text-[var(--charcoal)]">{s.title}</p>
                <p className="mt-1 font-mono text-xs text-[var(--charcoal-muted)]">{s.meta}</p>
              </motion.div>

              {index < steps.length - 1 && (
                <div className="flex justify-center py-1 text-[var(--purple)]">
                  <AnimatedArrow />
                </div>
              )}
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

export function TimelineSection() {
  const [selectedPeriod, setSelectedPeriod] = useState<"jul18" | "jul28" | "aug01" | "now">("now");

  const timelineData = {
    jul18: {
      date: "Jul 18, 2026",
      owner: "Morgan owns Acme",
      reason: "Initial account lead assignment recorded in Linear.",
      sources: ["Linear"],
    },
    jul28: {
      date: "Jul 28, 2026",
      owner: "Handoff Announced",
      reason: "Slack announcement: Morgan transitioning accounts ahead of sabbatical.",
      sources: ["Slack"],
    },
    aug01: {
      date: "Aug 01, 2026",
      owner: "Priya becomes owner",
      reason: "Official handoff completed and confirmed in Linear & Gmail.",
      sources: ["Linear", "Gmail"],
    },
    now: {
      date: "Present Day",
      owner: "Priya owns Acme",
      reason: "Active ownership state verified against all recent workplace activity.",
      sources: ["Slack", "Gmail", "Linear"],
    },
  };

  const current = timelineData[selectedPeriod];

  return (
    <section id="timeline" className="border-y border-black/[0.06] bg-white px-6 py-28">
      <div className="mx-auto max-w-5xl">
        <Reveal className="text-center">
          <span className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--charcoal-muted)]">
            Temporal State
          </span>
          <h2 className="mt-4 font-serif text-4xl text-[var(--charcoal)] md:text-6xl tracking-tight">
            State over time.
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-base text-[var(--charcoal-muted)] leading-relaxed">
            Continuum understands what used to be true, when it changed, and what is currently valid.
          </p>
        </Reveal>

        {/* Interactive Period Selector Bar */}
        <div className="mt-14 flex flex-wrap justify-center gap-3">
          {(
            [
              { id: "jul18", label: "Jul 18 (Initial)" },
              { id: "jul28", label: "Jul 28 (Announced)" },
              { id: "aug01", label: "Aug 01 (Handoff)" },
              { id: "now", label: "Now (Current)" },
            ] as const
          ).map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setSelectedPeriod(item.id)}
              className={`rounded-full border px-5 py-2 text-xs font-medium transition-all ${
                selectedPeriod === item.id
                  ? "border-[var(--charcoal)] bg-[var(--charcoal)] text-white shadow-xs"
                  : "border-black/[0.08] bg-[#faf8f5] text-[var(--charcoal-muted)] hover:border-black/20 hover:text-[var(--charcoal)]"
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>

        {/* Dynamic Timeline Card */}
        <div className="mx-auto mt-10 max-w-xl rounded-3xl border border-black/[0.08] bg-[#faf8f5] p-8 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="font-mono text-xs font-semibold uppercase tracking-wider text-[var(--purple)]">
              {current.date}
            </span>
            <span className="rounded-full bg-black/5 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-[var(--charcoal-muted)]">
              Historical Point in Time
            </span>
          </div>

          <p className="mt-4 text-2xl font-semibold text-[var(--charcoal)]">{current.owner}</p>
          <p className="mt-2 text-sm text-[var(--charcoal-muted)] leading-relaxed">{current.reason}</p>

          <div className="mt-6 flex flex-wrap items-center gap-2 border-t border-black/5 pt-4">
            <span className="text-[10px] uppercase tracking-wider font-semibold text-[var(--charcoal-muted)]">
              Supporting Sources:
            </span>
            {current.sources.map((s) => (
              <SourceBadge key={s} source={s} size="xs" />
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

export function ConflictSection() {
  return (
    <section id="conflict" className="bg-[var(--paper)] px-6 py-28">
      <div className="mx-auto max-w-5xl">
        <Reveal className="text-center">
          <span className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--charcoal-muted)]">
            First-Class Uncertainty
          </span>
          <h2 className="mt-4 font-serif text-4xl text-[var(--charcoal)] md:text-6xl tracking-tight">
            Uncertainty is first-class.
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-base text-[var(--charcoal-muted)] leading-relaxed">
            When workplace tools contain contradictory information, Continuum does not hallucinate a winner — it detects and surfaces the conflict.
          </p>
        </Reveal>

        {/* Contradicting Evidence Cards */}
        <div className="mt-16 grid gap-6 md:grid-cols-2">
          <Reveal delay={0.05}>
            <div className="rounded-3xl border border-black/[0.08] bg-white p-7 shadow-xs">
              <div className="flex items-center justify-between">
                <SourceBadge source="Slack" size="sm" />
                <span className="font-mono text-[10px] text-[var(--charcoal-muted)]">10:15 AM · #general</span>
              </div>
              <p className="mt-4 text-base font-semibold text-[var(--charcoal)]">
                &ldquo;Morgan is still managing the Acme account renewal.&rdquo;
              </p>
              <p className="mt-2 text-xs text-[var(--charcoal-muted)]">
                Observed in public general channel thread.
              </p>
            </div>
          </Reveal>

          <Reveal delay={0.1}>
            <div className="rounded-3xl border border-black/[0.08] bg-white p-7 shadow-xs">
              <div className="flex items-center justify-between">
                <SourceBadge source="Gmail" size="sm" />
                <span className="font-mono text-[10px] text-[var(--charcoal-muted)]">10:30 AM · client-memo</span>
              </div>
              <p className="mt-4 text-base font-semibold text-[var(--charcoal)]">
                &ldquo;Priya has officially taken over all Acme deliverables.&rdquo;
              </p>
              <p className="mt-2 text-xs text-[var(--charcoal-muted)]">
                Observed in signed client confirmation email.
              </p>
            </div>
          </Reveal>
        </div>

        {/* Continuum Conflict Resolver Output */}
        <Reveal delay={0.15}>
          <div className="mx-auto mt-8 max-w-2xl rounded-3xl border border-amber-200 bg-amber-50/70 p-8 text-center shadow-xs">
            <div className="inline-flex items-center gap-2 rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-900 border border-amber-200">
              <span>⚠️</span>
              <span>Evidence Conflict Detected</span>
            </div>
            <p className="mt-4 text-lg font-semibold text-amber-950">
              Continuum surfaces human review rather than inventing a hallucinated answer.
            </p>
            <p className="mt-2 text-xs text-amber-800 leading-relaxed">
              Confidence weighted by timestamp recency and formal channel authority (Gmail memo &gt; Slack chat).
            </p>
          </div>
        </Reveal>
      </div>
    </section>
  );
}

export function BenchmarkPlaceholderSection() {
  return (
    <section className="relative overflow-hidden bg-[#faf8f5] px-6 py-28 border-t border-black/[0.06] text-[var(--charcoal)]">
      <div className="relative mx-auto max-w-4xl text-center">
        <Reveal>
          <span className="inline-flex rounded-full border border-black/[0.08] bg-white px-3.5 py-1 text-xs font-semibold uppercase tracking-wider text-[var(--purple)] shadow-2xs">
            Enterprise Scale
          </span>
          <h2 className="mt-4 font-serif text-4xl text-[var(--charcoal)] md:text-6xl tracking-tight">
            Built for real company-scale context.
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-sm text-[var(--charcoal-muted)] leading-relaxed">
            Validated against the EnterpriseRAG-Bench 512,000+ document dataset spanning 9 enterprise systems.
          </p>
        </Reveal>

        <div className="mt-14 grid gap-6 sm:grid-cols-3">
          {[
            { metric: "512K+", label: "Enterprise Documents", note: "Multi-source corpus" },
            { metric: "< 5ms", label: "HydraDB Graph Latency", note: "p95 traversal speed" },
            { metric: "100%", label: "Traceable Provenance", note: "Every claim anchored to artifact" },
          ].map((item, idx) => (
            <Reveal key={item.label} delay={idx * 0.1}>
              <div className="rounded-3xl border border-black/[0.08] bg-white p-8 text-center shadow-xs">
                <p className="font-mono text-4xl font-semibold text-[var(--charcoal)] tracking-tight">{item.metric}</p>
                <p className="mt-2 text-sm font-semibold text-[var(--charcoal)]">{item.label}</p>
                <p className="mt-1 text-[11px] text-[var(--charcoal-muted)]">{item.note}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

export function SecuritySection() {
  const guarantees = [
    { title: "Controlled Deployment", desc: "Run fully self-hosted or in VPC with your own HydraDB instance." },
    { title: "Source Permissions Respected", desc: "Continuum enforces source-level access boundaries and document visibility." },
    { title: "Immutable Provenance Trail", desc: "Every state transition references an immutable artifact hash." },
    { title: "Bounded Semantic Access", desc: "Agent integrations interact strictly through verified MCP capabilities." },
    { title: "Zero Data Leakage to LLMs", desc: "Core state traversal happens inside the graph database, not in third-party prompts." },
    { title: "Explicit Integrations Only", desc: "No opaque web crawlers or unauthorized credential sharing." },
  ];

  return (
    <section className="bg-white px-6 py-28 border-t border-black/[0.06]">
      <div className="mx-auto max-w-5xl text-center">
        <Reveal>
          <span className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--charcoal-muted)]">
            Privacy & Governance
          </span>
          <h2 className="mt-4 font-serif text-4xl text-[var(--charcoal)] md:text-6xl text-balance tracking-tight">
            Your company&apos;s memory
            <br />
            <span className="italic">should remain yours.</span>
          </h2>
        </Reveal>

        <Stagger className="mt-16 grid gap-6 text-left sm:grid-cols-2 lg:grid-cols-3">
          {guarantees.map((item) => (
            <StaggerItem key={item.title}>
              <motion.div
                className="h-full rounded-3xl border border-black/[0.08] bg-[#faf8f5] p-6 transition-all hover:border-[var(--purple)]/40 hover:bg-white hover:shadow-xs"
                whileHover={{ y: -3 }}
              >
                <p className="text-base font-semibold text-[var(--charcoal)]">{item.title}</p>
                <p className="mt-2 text-xs leading-relaxed text-[var(--charcoal-muted)]">{item.desc}</p>
              </motion.div>
            </StaggerItem>
          ))}
        </Stagger>
      </div>
    </section>
  );
}
