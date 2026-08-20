"use client";

import { motion } from "framer-motion";

/* A curated, meaningful knowledge graph that GROWS as context is added:
 *   step 0  empty (just the account)
 *   step 1  Slack evidence -> Morgan owns Acme
 *   step 2  Gmail evidence -> ownership transfers to Priya
 *   step 3  resolved: Priya current, Morgan past (lineage preserved)
 * Every element declares the step it appears at; increasing `step` animates the
 * new nodes/edges in. Positions are in a 440x320 viewBox. */

const VB_W = 440;
const VB_H = 320;

const NODES = {
  acme: { x: 220, y: 160, label: "Acme", type: "account", appearsAt: 0 },
  morgan: { x: 70, y: 80, label: "Morgan", type: "person", appearsAt: 1 },
  priya: { x: 370, y: 240, label: "Priya", type: "person", appearsAt: 2 },
} as const;

const SOURCES = {
  slack: { x: 70, y: 240, label: "Slack", icon: "/brand/slack.svg", appearsAt: 1 },
  gmail: { x: 370, y: 80, label: "Gmail", icon: "/brand/gmail.svg", appearsAt: 2 },
} as const;

const PURPLE = "#6366f1";
const FAINT = "#94a3b8";

function edgePath(a: { x: number; y: number }, b: { x: number; y: number }) {
  const mx = (a.x + b.x) / 2;
  const my = (a.y + b.y) / 2 - 18;
  return `M ${a.x} ${a.y} Q ${mx} ${my} ${b.x} ${b.y}`;
}

export function EmergingMemoryGraph({ step, className = "" }: { step: number; className?: string }) {
  const vis = (a: number) => step >= a;
  const priyaCurrent = step >= 2;

  return (
    <svg viewBox={`0 0 ${VB_W} ${VB_H}`} className={className} role="img" aria-label="Company memory graph">
      {/* ── edges ─────────────────────────────────────────── */}
      {/* Slack -> Morgan (evidence) */}
      <Edge from={SOURCES.slack} to={NODES.morgan} visible={vis(1)} dotted color={FAINT} />
      {/* Morgan -> Acme (owns) — becomes "past" once Priya takes over */}
      <Edge
        from={NODES.morgan}
        to={NODES.acme}
        visible={vis(1)}
        color={priyaCurrent ? FAINT : PURPLE}
        dashed={priyaCurrent}
        label={priyaCurrent ? "owned" : "owns"}
      />
      {/* Gmail -> Priya (evidence) */}
      <Edge from={SOURCES.gmail} to={NODES.priya} visible={vis(2)} dotted color={FAINT} />
      {/* Priya -> Acme (owns, current) */}
      <Edge from={NODES.priya} to={NODES.acme} visible={vis(2)} color={PURPLE} label="owns" />
      {/* flowing pulse along the live ownership edge */}
      {priyaCurrent && (
        <circle r="3.5" fill={PURPLE}>
          <animateMotion dur="2.4s" repeatCount="indefinite" path={edgePath(NODES.priya, NODES.acme)} />
        </circle>
      )}

      {/* ── source chips ──────────────────────────────────── */}
      {Object.entries(SOURCES).map(([key, s]) => (
        <SourceChip key={key} node={s} visible={vis(s.appearsAt)} />
      ))}

      {/* ── entity nodes ──────────────────────────────────── */}
      <EntityNode node={NODES.acme} visible color="#0f172a" />
      <EntityNode node={NODES.morgan} visible={vis(1)} color={priyaCurrent ? FAINT : PURPLE} muted={priyaCurrent} />
      <EntityNode node={NODES.priya} visible={vis(2)} color={PURPLE} current={priyaCurrent} />
    </svg>
  );
}

function Edge({
  from,
  to,
  visible,
  color,
  dotted = false,
  dashed = false,
  label,
}: {
  from: { x: number; y: number };
  to: { x: number; y: number };
  visible: boolean;
  color: string;
  dotted?: boolean;
  dashed?: boolean;
  label?: string;
}) {
  const d = edgePath(from, to);
  const mx = (from.x + to.x) / 2;
  const my = (from.y + to.y) / 2 - 20;
  return (
    <motion.g initial={false} animate={{ opacity: visible ? 1 : 0 }} transition={{ duration: 0.4 }}>
      <motion.path
        d={d}
        fill="none"
        stroke={color}
        strokeWidth={dotted ? 1.5 : 2}
        strokeLinecap="round"
        strokeDasharray={dotted ? "2 6" : dashed ? "6 5" : undefined}
        initial={false}
        animate={{ pathLength: visible ? 1 : 0 }}
        transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
      />
      {label && visible && (
        <text x={mx} y={my} textAnchor="middle" fontSize="10" fontWeight="600" fill={color}>
          {label}
        </text>
      )}
    </motion.g>
  );
}

function SourceChip({ node, visible }: { node: { x: number; y: number; label: string; icon: string }; visible: boolean }) {
  const w = 66;
  const h = 26;
  return (
    <motion.g
      initial={false}
      animate={{ opacity: visible ? 1 : 0, scale: visible ? 1 : 0.6 }}
      transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
      style={{ transformOrigin: `${node.x}px ${node.y}px` }}
    >
      <rect x={node.x - w / 2} y={node.y - h / 2} width={w} height={h} rx={13} fill="#ffffff" stroke="rgba(15,23,42,0.12)" />
      <image href={node.icon} x={node.x - w / 2 + 8} y={node.y - 8} width={16} height={16} />
      <text x={node.x + 6} y={node.y + 4} fontSize="11" fontWeight="600" fill="#334155">
        {node.label}
      </text>
    </motion.g>
  );
}

function EntityNode({
  node,
  visible,
  color,
  current = false,
  muted = false,
}: {
  node: { x: number; y: number; label: string };
  visible: boolean;
  color: string;
  current?: boolean;
  muted?: boolean;
}) {
  const r = 30;
  return (
    <motion.g
      initial={false}
      animate={{ opacity: visible ? 1 : 0, scale: visible ? 1 : 0.5 }}
      transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
      style={{ transformOrigin: `${node.x}px ${node.y}px` }}
    >
      {current && (
        <motion.circle
          cx={node.x}
          cy={node.y}
          r={r + 6}
          fill="none"
          stroke={PURPLE}
          strokeWidth={1.5}
          opacity={0.35}
          animate={{ r: [r + 4, r + 10, r + 4], opacity: [0.35, 0.1, 0.35] }}
          transition={{ duration: 2.4, repeat: Infinity, ease: "easeInOut" }}
        />
      )}
      <circle cx={node.x} cy={node.y} r={r} fill="#ffffff" stroke={color} strokeWidth={current ? 2.5 : 1.75} opacity={muted ? 0.7 : 1} />
      <text x={node.x} y={node.y - 2} textAnchor="middle" fontSize="12" fontWeight="700" fill={muted ? FAINT : "#0f172a"}>
        {node.label}
      </text>
      {current && (
        <text x={node.x} y={node.y + 12} textAnchor="middle" fontSize="8" fontWeight="700" fill={PURPLE} letterSpacing="0.5">
          NOW
        </text>
      )}
      {muted && (
        <text x={node.x} y={node.y + 12} textAnchor="middle" fontSize="8" fontWeight="600" fill={FAINT}>
          past
        </text>
      )}
    </motion.g>
  );
}
