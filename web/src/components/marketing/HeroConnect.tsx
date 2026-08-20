"use client";

import Image from "next/image";
import Link from "next/link";
import { motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import { LogoMark } from "@/components/ui/LogoMark";
import { easeOut } from "@/components/ui/motion";

/* ── Node data ─────────────────────────────────────────────────────────────
 * Sources scatter in from the left; surfaces fan out to the right. `y` is the
 * vertical position as a % of the diagram height. Connection lines are drawn to
 * the measured DOM position of each node so they always plug in exactly. */

type Node = {
  name: string;
  sub: string;
  color: string;
  y: number;
  icon?: string;
  glyph?: React.ReactNode;
};

const SOURCES: Node[] = [
  { name: "Slack", sub: "Conversations", color: "#36C5F0", y: 8, icon: "/brand/slack.svg" },
  { name: "Gmail", sub: "Emails", color: "#EA4335", y: 22, icon: "/brand/gmail.svg" },
  { name: "Drive", sub: "Documents", color: "#FBBC05", y: 36, icon: "/brand/drive.svg" },
  { name: "Linear", sub: "Issues", color: "#8B8FF0", y: 50, icon: "/brand/linear.svg" },
  { name: "GitHub", sub: "Code & PRs", color: "#C9D1D9", y: 64, icon: "/brand/github.svg" },
  { name: "Notion", sub: "Notes", color: "#E5E7EB", y: 78, icon: "/brand/notion.svg" },
  {
    name: "Any API",
    sub: "And more",
    color: "#818CF8",
    y: 92,
    glyph: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
        <path d="M8 7l-5 5 5 5M16 7l5 5-5 5M13 4l-2 16" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
];

const SURFACES: Node[] = [
  {
    name: "Query API", sub: "Ask anything", color: "#A78BFA", y: 15,
    glyph: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
        <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="1.7" />
        <path d="M20 20l-3.5-3.5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    name: "Knowledge Graph", sub: "Explore connections", color: "#22D3EE", y: 32.5,
    glyph: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
        <circle cx="5" cy="6" r="2.2" stroke="currentColor" strokeWidth="1.6" />
        <circle cx="19" cy="6" r="2.2" stroke="currentColor" strokeWidth="1.6" />
        <circle cx="12" cy="18" r="2.2" stroke="currentColor" strokeWidth="1.6" />
        <path d="M6.8 7.4L11 16M17.2 7.4L13 16" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      </svg>
    ),
  },
  { name: "Slack Bot", sub: "Answers in context", color: "#36C5F0", y: 50, icon: "/brand/slack.svg" },
  {
    name: "MCP", sub: "For agents & copilots", color: "#34D399", y: 67.5,
    glyph: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
        <path d="M5 8l3 3-3 3M11 14h5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
        <rect x="2.5" y="4.5" width="19" height="15" rx="2.5" stroke="currentColor" strokeWidth="1.5" />
      </svg>
    ),
  },
  {
    name: "Your App", sub: "Build on top", color: "#C4B5FD", y: 85,
    glyph: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
        <rect x="4" y="4" width="7" height="7" rx="1.5" stroke="currentColor" strokeWidth="1.6" />
        <rect x="13" y="4" width="7" height="7" rx="1.5" stroke="currentColor" strokeWidth="1.6" />
        <rect x="4" y="13" width="7" height="7" rx="1.5" stroke="currentColor" strokeWidth="1.6" />
        <rect x="13" y="13" width="7" height="7" rx="1.5" stroke="currentColor" strokeWidth="1.6" />
      </svg>
    ),
  },
];

type Port = { x: number; y: number };
type Geom = { w: number; h: number; src: Port[]; surf: Port[] };

function NodeCard({
  node,
  side,
  innerRef,
}: {
  node: Node;
  side: "left" | "right";
  innerRef?: (el: HTMLDivElement | null) => void;
}) {
  const isLeft = side === "left";
  const style: React.CSSProperties = {
    top: `${node.y}%`,
    flexDirection: isLeft ? "row" : "row-reverse",
    ...(isLeft ? { left: 0 } : { right: 0 }),
  };
  return (
    <div ref={innerRef} className="absolute flex -translate-y-1/2 items-center gap-3" style={style}>
      <span
        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-white/10"
        style={{ background: node.icon ? "#fff" : "rgba(255,255,255,0.05)", color: node.color }}
      >
        {node.icon ? (
          <Image src={node.icon} alt="" width={20} height={20} className="h-5 w-5 object-contain" />
        ) : (
          node.glyph
        )}
      </span>
      <span className={isLeft ? "text-left" : "text-right"}>
        <span className="block text-sm font-semibold leading-tight text-white">{node.name}</span>
        <span className="block text-xs leading-tight text-white/45">{node.sub}</span>
      </span>
    </div>
  );
}

export function HeroConnect() {
  const diagramRef = useRef<HTMLDivElement>(null);
  const srcRefs = useRef<(HTMLDivElement | null)[]>([]);
  const surfRefs = useRef<(HTMLDivElement | null)[]>([]);
  const [geom, setGeom] = useState<Geom | null>(null);

  useEffect(() => {
    const measure = () => {
      const c = diagramRef.current;
      if (!c) return;
      const cr = c.getBoundingClientRect();
      if (cr.width === 0) return;
      // Small gap so the line/port sits a little away from the node label.
      const GAP = 18;
      const port = (el: HTMLDivElement | null, edge: "right" | "left"): Port => {
        if (!el) return { x: 0, y: 0 };
        const r = el.getBoundingClientRect();
        const baseX = (edge === "right" ? r.right : r.left) - cr.left;
        // sources shift right (away from the left labels); surfaces shift left.
        return { x: edge === "right" ? baseX + GAP : baseX - GAP, y: r.top - cr.top + r.height / 2 };
      };
      setGeom({
        w: cr.width,
        h: cr.height,
        src: SOURCES.map((_, i) => port(srcRefs.current[i], "right")),
        surf: SURFACES.map((_, i) => port(surfRefs.current[i], "left")),
      });
    };
    measure();
    const ro = new ResizeObserver(measure);
    if (diagramRef.current) ro.observe(diagramRef.current);
    return () => ro.disconnect();
  }, []);

  const hubX = geom ? geom.w / 2 : 0;
  const hubY = geom ? geom.h / 2 : 0;

  return (
    <section className="relative overflow-hidden bg-[#0a0e1a] px-6 pb-24 pt-10">
      {/* ambient glows */}
      <div aria-hidden className="pointer-events-none absolute inset-0">
        <div className="absolute left-1/2 top-[38%] h-[520px] w-[820px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[radial-gradient(ellipse_at_center,rgba(99,102,241,0.22),transparent_60%)]" />
        <div className="absolute left-1/2 top-[38%] h-[300px] w-[1200px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[radial-gradient(ellipse_at_center,rgba(34,211,238,0.10),transparent_65%)]" />
      </div>

      <div className="relative mx-auto max-w-6xl">
        <div className="hidden items-center justify-between text-[11px] font-semibold uppercase tracking-[0.2em] text-white/40 lg:flex">
          <span>Scattered across your tools</span>
          <span>One memory. Everywhere.</span>
        </div>

        {/* ── Convergence diagram (lg+) ─────────────────────────────── */}
        <div ref={diagramRef} className="relative mt-6 hidden h-[600px] lg:block">
          <OrbGlow />

          {geom && (
            <svg
              aria-hidden
              className="absolute inset-0 z-[5]"
              width={geom.w}
              height={geom.h}
              viewBox={`0 0 ${geom.w} ${geom.h}`}
              style={{ filter: "drop-shadow(0 0 6px rgba(99,102,241,0.25))" }}
            >
              {geom.src.map((p, i) => {
                const n = SOURCES[i];
                const d = `M ${p.x} ${p.y} C ${p.x + (hubX - p.x) * 0.5} ${p.y}, ${hubX - 70} ${hubY}, ${hubX} ${hubY}`;
                return (
                  <g key={n.name}>
                    <motion.path
                      d={d}
                      fill="none"
                      stroke={n.color}
                      strokeWidth={1.8}
                      strokeLinecap="round"
                      initial={{ pathLength: 0, opacity: 0 }}
                      animate={{ pathLength: 1, opacity: 0.55 }}
                      transition={{ duration: 1.1, delay: 0.15 + i * 0.08, ease: easeOut }}
                    />
                    <path d={d} fill="none" stroke={n.color} strokeWidth={2.2} strokeLinecap="round" className="hero-flow" opacity={0.95} />
                    <circle cx={p.x} cy={p.y} r={4.5} fill={n.color} />
                  </g>
                );
              })}
              {geom.surf.map((p, i) => {
                const n = SURFACES[i];
                const d = `M ${hubX} ${hubY} C ${hubX + 70} ${hubY}, ${p.x - (p.x - hubX) * 0.5} ${p.y}, ${p.x} ${p.y}`;
                return (
                  <g key={n.name}>
                    <motion.path
                      d={d}
                      fill="none"
                      stroke={n.color}
                      strokeWidth={1.8}
                      strokeLinecap="round"
                      initial={{ pathLength: 0, opacity: 0 }}
                      animate={{ pathLength: 1, opacity: 0.55 }}
                      transition={{ duration: 1.1, delay: 0.45 + i * 0.08, ease: easeOut }}
                    />
                    <path d={d} fill="none" stroke={n.color} strokeWidth={2.2} strokeLinecap="round" className="hero-flow" opacity={0.95} />
                    <circle cx={p.x} cy={p.y} r={4.5} fill={n.color} />
                  </g>
                );
              })}
            </svg>
          )}

          {/* source column */}
          <div className="absolute inset-y-0 left-0 z-[5] w-[19%]">
            {SOURCES.map((n, i) => (
              <NodeCard key={n.name} node={n} side="left" innerRef={(el) => { srcRefs.current[i] = el; }} />
            ))}
          </div>

          {/* surface column */}
          <div className="absolute inset-y-0 right-0 z-[5] w-[19%]">
            {SURFACES.map((n, i) => (
              <NodeCard key={n.name} node={n} side="right" innerRef={(el) => { surfRefs.current[i] = el; }} />
            ))}
          </div>

          {/* center pill — on top of everything */}
          <div className="absolute left-1/2 top-1/2 z-20 -translate-x-1/2 -translate-y-1/2">
            <Pill />
          </div>
        </div>

        {/* ── Mobile hub ────────────────────────────────────────────── */}
        <div className="relative mt-10 flex justify-center lg:hidden">
          <OrbGlow compact />
          <div className="relative z-20">
            <Pill />
          </div>
        </div>

        {/* headline */}
        <motion.div
          className="relative z-10 mx-auto mt-8 max-w-3xl text-center lg:mt-4"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.6, ease: easeOut }}
        >
          <h1 className="font-serif text-4xl leading-[1.05] tracking-tight text-white md:text-6xl">
            Your company&apos;s memory,{" "}
            <span className="italic text-[#a5b4fc]">finally</span> connected.
          </h1>
          <p className="mx-auto mt-5 max-w-xl text-base leading-relaxed text-white/55 md:text-lg">
            Continuum turns the conversations, documents, and decisions scattered across your tools
            into one temporal, evidence-backed model of what&apos;s true right now — and what changed.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Link
              href="/workspace"
              className="group inline-flex items-center gap-2 rounded-full bg-white px-7 py-3.5 text-sm font-semibold text-[#0a0e1a] shadow-lg transition-all hover:scale-[1.03] active:scale-[0.99]"
            >
              <span>Create workspace</span>
              <span className="transition-transform duration-200 group-hover:translate-x-1" aria-hidden>→</span>
            </Link>
            <Link
              href="/redwood"
              className="group inline-flex items-center gap-2 rounded-full border border-white/25 bg-white/10 px-7 py-3.5 text-sm font-semibold text-white backdrop-blur-sm transition-all hover:border-white/50 hover:scale-[1.03] active:scale-[0.99]"
            >
              <span>Explore Redwood demo</span>
              <span className="transition-transform duration-200 group-hover:translate-x-1" aria-hidden>→</span>
            </Link>
            <Link
              href="#architecture"
              className="inline-flex items-center gap-1.5 px-2 py-3.5 text-sm font-medium text-white/60 transition-colors hover:text-white"
            >
              <span>How it works</span>
              <span aria-hidden>↓</span>
            </Link>
          </div>
        </motion.div>
      </div>
    </section>
  );
}

function OrbGlow({ compact = false }: { compact?: boolean }) {
  return (
    <div
      aria-hidden
      className={`pointer-events-none absolute left-1/2 top-1/2 z-0 -translate-x-1/2 -translate-y-1/2 rounded-full bg-[radial-gradient(circle,rgba(99,102,241,0.4),rgba(34,211,238,0.12)_45%,transparent_70%)] blur-2xl ${
        compact ? "h-[260px] w-[260px]" : "h-[440px] w-[440px]"
      }`}
    />
  );
}

function Pill() {
  return (
    <motion.div
      className="group flex items-center gap-3 rounded-2xl bg-white px-6 py-4 shadow-[0_24px_70px_-10px_rgba(99,102,241,0.55)] ring-1 ring-black/5"
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.7, delay: 0.35, ease: easeOut }}
    >
      <LogoMark size={34} priority />
      <div className="text-left">
        <span className="block text-xl font-semibold tracking-[-0.02em] text-[#0f172a]">Continuum</span>
        <span className="block text-xs text-[#64748b]">Canonical Company Memory</span>
      </div>
    </motion.div>
  );
}
