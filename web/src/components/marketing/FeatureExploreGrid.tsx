"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Reveal, Stagger, StaggerItem } from "@/components/ui/motion";

const FEATURE_CARDS = [
  {
    href: "/query",
    tag: "Query Engine",
    title: "Ask once. Know why.",
    desc: "Ask questions in natural language. Inspect resolved state, historical ownership changes, and grounding citations.",
    badge: "Current / Lineage / Why",
    accent: "hover:border-[var(--purple)]",
  },
  {
    href: "/graph",
    tag: "Spatial Graph",
    title: "Knowledge Graph Explorer",
    desc: "Traverse canonical entities, people, code owners, and artifact links directly inside the HydraDB graph substrate.",
    badge: "Interactive Topology",
    accent: "hover:border-cyan-400",
  },
  {
    href: "/slack",
    tag: "Live Integration",
    title: "Slack Bot & Real-Time Loop",
    desc: "Interact with @continuum directly in Slack. Ingest workplace handoff events and watch memory evolve automatically.",
    badge: "Verified Connected",
    accent: "hover:border-emerald-500",
  },
  {
    href: "/mcp",
    tag: "Agent Interface",
    title: "Model Context Protocol (MCP)",
    desc: "Connect autonomous AI agents to Continuum semantic operations with deterministic state and zero hallucination.",
    badge: "6 Semantic Tools",
    accent: "hover:border-purple-400",
  },
  {
    href: "/connectors",
    tag: "Ecosystem",
    title: "Source Connectors",
    desc: "Normalize workplace data across Slack, Gmail, Linear, GitHub, Google Drive, Notion, Jira, and Teams.",
    badge: "Multi-Source Matrix",
    accent: "hover:border-blue-400",
  },
  {
    href: "/trust",
    tag: "Governance",
    title: "Trust, Provenance & Time",
    desc: "Every answer is anchored to SHA-256 artifact hashes. Detect contradictory evidence and query historical points in time.",
    badge: "Cryptographic Provenance",
    accent: "hover:border-amber-500",
  },
];

export function FeatureExploreGrid() {
  return (
    <section className="bg-white px-6 py-28 border-t border-black/[0.06]">
      <div className="mx-auto max-w-6xl">
        <Reveal className="text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-black/[0.08] bg-[#faf8f5] px-3.5 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--charcoal-muted)]">
            Explore Continuum
          </div>
          <h2 className="mt-4 font-serif text-4xl text-[var(--charcoal)] md:text-6xl tracking-tight">
            Dive deeper into the product.
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-base text-[var(--charcoal-muted)]">
            Explore dedicated interactive consoles for querying, spatial graph traversal, Slack live loops, and agent integrations.
          </p>
        </Reveal>

        <Stagger className="mt-16 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {FEATURE_CARDS.map((card) => (
            <StaggerItem key={card.title}>
              <Link href={card.href} className="group block h-full">
                <motion.div
                  className={`flex flex-col justify-between h-full rounded-3xl border border-black/[0.08] bg-[#faf8f5] p-8 transition-all group-hover:bg-white group-hover:shadow-md ${card.accent}`}
                  whileHover={{ y: -4 }}
                >
                  <div>
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs font-semibold uppercase tracking-wider text-[var(--purple)]">
                        {card.tag}
                      </span>
                      <span className="rounded-full bg-black/5 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-[var(--charcoal-muted)]">
                        {card.badge}
                      </span>
                    </div>

                    <h3 className="mt-4 text-xl font-semibold tracking-tight text-[var(--charcoal)] group-hover:text-[var(--purple)] transition-colors">
                      {card.title}
                    </h3>
                    <p className="mt-2.5 text-xs leading-relaxed text-[var(--charcoal-muted)]">
                      {card.desc}
                    </p>
                  </div>

                  <div className="mt-6 flex items-center gap-1.5 text-xs font-semibold text-[var(--charcoal)] group-hover:text-[var(--purple)]">
                    <span>Explore Surface</span>
                    <span className="transition-transform group-hover:translate-x-1">→</span>
                  </div>
                </motion.div>
              </Link>
            </StaggerItem>
          ))}
        </Stagger>
      </div>
    </section>
  );
}
