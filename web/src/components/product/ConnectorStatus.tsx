"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import { fetchConnectors, isApiAvailable } from "@/lib/api";
import type { ConnectorsPayload, ConnectorState } from "@/lib/contracts";
import { Reveal } from "@/components/ui/motion";

/* Real connector state. When the API is live it shows the actual configured
 * connectors + indexed volume from HydraDB. When it's not, it clearly says
 * DEMO MODE — never fakes a "connected" status. */

const ICON: Record<string, string> = {
  slack: "/brand/slack.svg",
  gmail: "/brand/gmail.svg",
};

const DEMO: ConnectorsPayload = {
  mode: "demo",
  total_artifacts: 0,
  connectors: [
    { id: "slack", name: "Slack", status: "demo", artifacts: 0, configured: false },
    { id: "gmail", name: "Gmail", status: "demo", artifacts: 0, configured: false },
  ],
};

const STATUS_STYLE: Record<string, { dot: string; label: string; text: string }> = {
  connected: { dot: "bg-[var(--emerald)]", label: "Connected", text: "text-[var(--emerald)]" },
  demo: { dot: "bg-amber-500", label: "Demo data", text: "text-amber-600" },
  planned: { dot: "bg-[var(--charcoal-faint)]", label: "Not connected", text: "text-[var(--charcoal-muted)]" },
};

export function ConnectorStatus() {
  const [data, setData] = useState<ConnectorsPayload | null>(null);
  const [live, setLive] = useState<boolean | null>(null);

  useEffect(() => {
    isApiAvailable().then(async (ok) => {
      setLive(ok);
      if (ok) {
        try {
          setData(await fetchConnectors());
          return;
        } catch {
          /* fall through to demo */
        }
      }
      setData(DEMO);
    });
  }, []);

  const payload = data ?? DEMO;

  return (
    <section className="bg-[var(--paper)] px-6 pt-24">
      <div className="mx-auto max-w-5xl">
        <Reveal className="mb-6 flex flex-wrap items-end justify-between gap-3">
          <div>
            <span className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--charcoal-muted)]">
              Connected sources
            </span>
            <h2 className="mt-2 font-serif text-3xl text-[var(--charcoal)] md:text-4xl">
              Your workspace, indexed.
            </h2>
          </div>
          <span
            className={`inline-flex items-center gap-2 rounded-full border px-3.5 py-1.5 text-[11px] font-medium ${
              payload.mode === "live"
                ? "border-[var(--emerald-border)] bg-[var(--emerald-soft)] text-[var(--emerald)]"
                : "border-[var(--paper-border)] bg-white text-[var(--charcoal-muted)]"
            }`}
          >
            <span className={`h-1.5 w-1.5 rounded-full ${payload.mode === "live" ? "bg-[var(--emerald)]" : "bg-amber-500"}`} />
            {live === null ? "Connecting…" : payload.mode === "live" ? "LIVE · HydraDB" : "DEMO MODE"}
          </span>
        </Reveal>

        <div className="grid gap-4 sm:grid-cols-2">
          {payload.connectors.map((c) => (
            <ConnectorCard key={c.id} c={c} />
          ))}
        </div>
      </div>
    </section>
  );
}

function ConnectorCard({ c }: { c: ConnectorState }) {
  const s = STATUS_STYLE[c.status] ?? STATUS_STYLE.planned;
  return (
    <div className="rounded-3xl border border-[var(--paper-border)] bg-white p-6 shadow-[var(--shadow-subtle)]">
      <div className="flex items-center gap-3">
        {ICON[c.id] ? (
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-white ring-1 ring-black/5">
            <Image src={ICON[c.id]} alt="" width={22} height={22} className="h-[22px] w-[22px] object-contain" />
          </span>
        ) : null}
        <div>
          <p className="text-base font-semibold text-[var(--charcoal)]">{c.name}</p>
          <p className={`flex items-center gap-1.5 text-xs font-medium ${s.text}`}>
            <span className={`h-1.5 w-1.5 rounded-full ${s.dot}`} />
            {s.label}
          </p>
        </div>
      </div>

      <div className="mt-5 grid grid-cols-2 gap-4 border-t border-[var(--paper-border)] pt-4">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-wider text-[var(--charcoal-faint)]">Artifacts indexed</p>
          <p className="mt-1 font-mono text-lg font-semibold text-[var(--charcoal)]">{c.artifacts.toLocaleString()}</p>
        </div>
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-wider text-[var(--charcoal-faint)]">Credentials</p>
          <p className="mt-1 text-sm font-medium text-[var(--charcoal-body)]">{c.configured ? "Configured" : "Not set"}</p>
        </div>
      </div>
    </div>
  );
}
