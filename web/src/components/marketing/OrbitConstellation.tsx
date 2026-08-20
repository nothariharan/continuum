"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Reveal, PulseRing } from "@/components/ui/motion";

const INNER_RING_NODES = [
  {
    label: "People",
    icon: "👤",
    desc: "Founders, leads, code owners, assignees",
    meta: "person:priya · person:morgan · person:sarah",
  },
  {
    label: "Projects",
    icon: "⚡",
    desc: "Linear epics, repos, milestones",
    meta: "project:acme-infra · repo:continuum-core",
  },
  {
    label: "Documents",
    icon: "📄",
    desc: "Specs, handoff memos, architecture RFCs",
    meta: "doc:q3-handoff-rfc · spec:acme-sow",
  },
  {
    label: "Messages",
    icon: "💬",
    desc: "Slack announcements, email agreements",
    meta: "msg:slack_1722510000 · email:acme-transfer",
  },
];

const OUTER_RING_NODES = [
  {
    label: "Decisions",
    icon: "⚖️",
    desc: "Handoff approvals, tech choices",
    meta: "decision:acme-ownership-transfer",
  },
  {
    label: "Events",
    icon: "📅",
    desc: "Transitions, departures, rollouts",
    meta: "event:ownership-handoff-aug01",
  },
  {
    label: "Organizations",
    icon: "🏢",
    desc: "Clients, teams, vendors, subsidiaries",
    meta: "account:acme · org:engineering-core",
  },
];

export function OrbitConstellation() {
  const [isPaused, setIsPaused] = useState(false);
  const [activeNode, setActiveNode] = useState<{
    label: string;
    icon: string;
    desc: string;
    meta: string;
  } | null>(null);

  const innerRadius = 180;
  const outerRadius = 280;

  return (
    <section id="memory" className="relative overflow-hidden bg-[var(--paper)] px-6 py-28">
      <div className="mx-auto max-w-6xl">
        {/* Editorial Section Header */}
        <Reveal className="text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-black/[0.08] bg-white/80 px-3.5 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--charcoal-muted)]">
            Visual Thesis
          </div>
          <h2 className="mt-4 font-serif text-4xl text-[var(--charcoal)] md:text-6xl tracking-tight">
            Identity + Time + Evidence
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-base text-[var(--charcoal-muted)] leading-relaxed">
            A living graph connecting who did what, when it changed, and the original artifacts that prove it.
          </p>
        </Reveal>

        {/* Orbit System Container */}
        <div
          className="relative mx-auto mt-16 flex h-[640px] max-w-5xl items-center justify-center overflow-hidden rounded-3xl border border-black/[0.08] bg-white/90 p-6 shadow-sm backdrop-blur-xs"
          onMouseEnter={() => setIsPaused(true)}
          onMouseLeave={() => {
            setIsPaused(false);
            setActiveNode(null);
          }}
        >
          {/* Orbital Track 1 (Inner) */}
          <div
            className="absolute rounded-full border border-dashed border-[var(--purple)]/20 pointer-events-none"
            style={{ width: `${innerRadius * 2}px`, height: `${innerRadius * 2}px` }}
          />

          {/* Orbital Track 2 (Outer) */}
          <div
            className="absolute rounded-full border border-dashed border-[var(--cyan)]/25 pointer-events-none"
            style={{ width: `${outerRadius * 2}px`, height: `${outerRadius * 2}px` }}
          />

          <PulseRing />

          {/* Central Fixed Box: Continuum Company Memory Core */}
          <motion.div
            className="relative z-30 flex flex-col items-center justify-center rounded-3xl border-2 border-[var(--purple)] bg-white px-9 py-7 text-center shadow-[0_25px_70px_-15px_rgba(107,78,255,0.25)]"
            animate={{
              boxShadow: [
                "0 20px 60px -10px rgba(107, 78, 255, 0.18)",
                "0 30px 85px -10px rgba(107, 78, 255, 0.35)",
                "0 20px 60px -10px rgba(107, 78, 255, 0.18)",
              ],
            }}
            transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
          >
            <div className="flex h-11 w-11 items-center justify-center rounded-full bg-[var(--purple-soft)] text-[var(--purple)] font-bold text-xl">
              ∞
            </div>
            <p className="mt-2.5 text-[10px] font-bold uppercase tracking-[0.26em] text-[var(--purple)]">
              CONTINUUM
            </p>
            <p className="mt-1 text-base font-semibold text-[var(--charcoal)]">
              Company Memory Core
            </p>
            <span className="mt-2 rounded-full bg-emerald-500/10 px-2.5 py-0.5 font-mono text-[9px] font-semibold uppercase tracking-wider text-emerald-700">
              Resolved State Engine
            </span>
          </motion.div>

          {/* Rotating Inner Orbit Group */}
          <div
            className="absolute z-20 flex items-center justify-center pointer-events-none"
            style={{
              width: `${innerRadius * 2}px`,
              height: `${innerRadius * 2}px`,
              animation: `orbit-spin 32s linear infinite`,
              animationPlayState: isPaused ? "paused" : "running",
            }}
          >
            {INNER_RING_NODES.map((node, index) => {
              const angle = (index / INNER_RING_NODES.length) * Math.PI * 2;
              const x = Math.cos(angle) * innerRadius;
              const y = Math.sin(angle) * innerRadius;

              return (
                <div
                  key={node.label}
                  className="absolute pointer-events-auto"
                  style={{
                    left: `calc(50% + ${x}px)`,
                    top: `calc(50% + ${y}px)`,
                    transform: "translate(-50%, -50%)",
                  }}
                >
                  {/* Counter-rotation to keep the node card upright while revolving */}
                  <div
                    style={{
                      animation: `orbit-spin 32s linear infinite reverse`,
                      animationPlayState: isPaused ? "paused" : "running",
                    }}
                  >
                    <button
                      type="button"
                      onMouseEnter={() => setActiveNode(node)}
                      className={`group flex items-center gap-2.5 rounded-full border px-4 py-2 text-xs font-semibold shadow-xs transition-all ${
                        activeNode?.label === node.label
                          ? "border-[var(--purple)] bg-[var(--purple)] text-white shadow-lg scale-110"
                          : "border-black/[0.08] bg-white text-[var(--charcoal)] hover:border-[var(--purple)] hover:shadow-md"
                      }`}
                    >
                      <span className="text-sm">{node.icon}</span>
                      <span>{node.label}</span>
                    </button>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Rotating Outer Orbit Group */}
          <div
            className="absolute z-20 flex items-center justify-center pointer-events-none"
            style={{
              width: `${outerRadius * 2}px`,
              height: `${outerRadius * 2}px`,
              animation: `orbit-spin 48s linear infinite reverse`,
              animationPlayState: isPaused ? "paused" : "running",
            }}
          >
            {OUTER_RING_NODES.map((node, index) => {
              const angle = (index / OUTER_RING_NODES.length) * Math.PI * 2;
              const x = Math.cos(angle) * outerRadius;
              const y = Math.sin(angle) * outerRadius;

              return (
                <div
                  key={node.label}
                  className="absolute pointer-events-auto"
                  style={{
                    left: `calc(50% + ${x}px)`,
                    top: `calc(50% + ${y}px)`,
                    transform: "translate(-50%, -50%)",
                  }}
                >
                  {/* Counter-rotation to keep node card upright */}
                  <div
                    style={{
                      animation: `orbit-spin 48s linear infinite`,
                      animationPlayState: isPaused ? "paused" : "running",
                    }}
                  >
                    <button
                      type="button"
                      onMouseEnter={() => setActiveNode(node)}
                      className={`group flex items-center gap-2.5 rounded-full border px-4 py-2 text-xs font-semibold shadow-xs transition-all ${
                        activeNode?.label === node.label
                          ? "border-[var(--cyan)] bg-[#0284c7] text-white shadow-lg scale-110"
                          : "border-black/[0.08] bg-white text-[var(--charcoal)] hover:border-[var(--cyan)] hover:shadow-md"
                      }`}
                    >
                      <span className="text-sm">{node.icon}</span>
                      <span>{node.label}</span>
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Selected / Active Node Inspector Banner */}
        <div className="mt-8 text-center min-h-[64px]">
          <AnimatePresence mode="wait">
            {activeNode ? (
              <motion.div
                key={activeNode.label}
                initial={{ opacity: 0, y: 8, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -8, scale: 0.98 }}
                className="inline-flex flex-col sm:flex-row items-center gap-3 rounded-2xl bg-white border border-black/[0.08] px-6 py-3 shadow-md"
              >
                <div className="flex items-center gap-2">
                  <span className="text-lg">{activeNode.icon}</span>
                  <span className="font-semibold text-sm text-[var(--charcoal)]">
                    {activeNode.label}:
                  </span>
                </div>
                <span className="text-xs text-[var(--charcoal-muted)]">{activeNode.desc}</span>
                <span className="font-mono text-[11px] rounded-md bg-[#faf8f5] px-2 py-0.5 text-[var(--purple)]">
                  {activeNode.meta}
                </span>
              </motion.div>
            ) : (
              <p className="text-xs text-[var(--charcoal-muted)]">
                Hover over any revolving node to inspect Continuum&apos;s structured entity mapping.
              </p>
            )}
          </AnimatePresence>
        </div>
      </div>
    </section>
  );
}
