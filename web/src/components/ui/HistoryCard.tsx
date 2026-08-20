import type { HistoryRow } from "@/lib/contracts";

export function HistoryCard({
  rows,
}: {
  rows: HistoryRow[] | { from: string; to: string; date?: string; reason?: string }[];
  dark?: boolean;
}) {
  return (
    <div className="rounded-3xl border border-black/[0.08] bg-white p-6 text-[var(--charcoal)] shadow-[0_12px_32px_-8px_rgba(15,23,42,0.06)]">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-[var(--purple)]" />
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--charcoal-muted)]">
            Historical State Lineage
          </p>
        </div>
        <span className="rounded-full bg-slate-100 px-2.5 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wider text-slate-700">
          Immutable Claims
        </span>
      </div>

      <div className="space-y-3">
        {rows.map((row, index) => {
          if ("from" in row) {
            return (
              <div
                key={index}
                className="flex items-center justify-between rounded-2xl border border-black/[0.06] bg-[#faf8f5] p-4 text-sm hover:bg-white hover:border-[var(--purple)]/30 transition-all"
              >
                <div className="flex items-center gap-3">
                  <span className="font-semibold text-[var(--charcoal)]">{row.from}</span>
                  <span className="text-[var(--purple)] font-bold">→</span>
                  <span className="font-semibold text-emerald-700">{row.to}</span>
                </div>
                <div className="text-right">
                  <p className="font-mono text-xs text-[var(--charcoal-muted)]">
                    {row.date ?? "Aug 01, 2026"}
                  </p>
                  {row.reason && (
                    <p className="text-[11px] text-[var(--charcoal-muted)]">
                      {row.reason}
                    </p>
                  )}
                </div>
              </div>
            );
          }

          return (
            <div
              key={index}
              className="flex items-center justify-between rounded-2xl border border-black/[0.06] bg-[#faf8f5] p-4 text-sm"
            >
              <div>
                <p className="font-semibold text-[var(--charcoal)]">{row.subject_name}</p>
                <p className="text-[11px] text-[var(--charcoal-muted)]">
                  Subject ID: {row.subject_id}
                </p>
              </div>
              <div className="text-right font-mono text-xs text-[var(--charcoal-muted)]">
                {row.valid_from ?? "Jul 18"} {row.valid_to ? `→ ${row.valid_to}` : "→ Present"}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function StateTimeline({
  events,
}: {
  events: { date: string; label: string; detail?: string; active?: boolean }[];
  dark?: boolean;
}) {
  return (
    <div className="relative border-l-2 border-[var(--purple)]/30 pl-7 space-y-6">
      {events.map((event, index) => (
        <div key={index} className="relative group">
          <span
            className={`absolute -left-[35px] top-1.5 h-3.5 w-3.5 rounded-full border-2 transition-all ${
              event.active
                ? "border-[var(--purple)] bg-[var(--purple)] ring-4 ring-[var(--purple)]/20"
                : "border-slate-300 bg-white"
            }`}
          />
          <div>
            <span className="font-mono text-xs font-semibold uppercase tracking-wider text-[var(--purple)]">
              {event.date}
            </span>
            <p className="mt-0.5 text-base font-medium text-[var(--charcoal)]">
              {event.label}
            </p>
            {event.detail && (
              <p className="mt-1 text-xs text-[var(--charcoal-muted)] leading-relaxed">
                {event.detail}
              </p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
