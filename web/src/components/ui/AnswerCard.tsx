import type { AnswerStatus } from "@/lib/contracts";
import { SourceBadge } from "./SourceBadge";

export function AnswerCard({
  answer,
  status,
  previous,
  effective,
  confidence,
  sources = [],
}: {
  answer: string;
  status?: AnswerStatus;
  previous?: string;
  effective?: string;
  confidence?: number;
  sources?: string[];
  dark?: boolean;
}) {
  const statusStyles: Record<AnswerStatus, { label: string; badge: string }> = {
    definitive: {
      label: "Resolved State",
      badge: "bg-emerald-50 text-emerald-700 border-emerald-200",
    },
    conflict: {
      label: "Conflict Detected",
      badge: "bg-amber-50 text-amber-800 border-amber-200",
    },
    review: {
      label: "Needs Review",
      badge: "bg-purple-50 text-purple-700 border-purple-200",
    },
    absent: {
      label: "No Evidence",
      badge: "bg-slate-50 text-slate-600 border-slate-200",
    },
    error: {
      label: "Error",
      badge: "bg-rose-50 text-rose-700 border-rose-200",
    },
  };

  const currentStatus = status ? statusStyles[status] ?? statusStyles.definitive : null;

  return (
    <div className="rounded-3xl border border-black/[0.08] bg-white p-7 text-[var(--charcoal)] shadow-[0_12px_32px_-8px_rgba(15,23,42,0.06)] transition-all">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-[var(--purple)]" />
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--charcoal-muted)]">
            Continuum State
          </p>
        </div>
        {currentStatus && (
          <span
            className={`rounded-full border px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${currentStatus.badge}`}
          >
            {currentStatus.label}
          </span>
        )}
      </div>

      <p className="text-2xl font-medium leading-snug tracking-tight text-[var(--charcoal)] text-balance">
        {answer}
      </p>

      {(previous || effective || confidence !== undefined) && (
        <dl className="mt-6 grid grid-cols-2 gap-4 border-t border-black/[0.06] pt-5 text-sm sm:grid-cols-3">
          {previous && (
            <div>
              <dt className="text-xs text-[var(--charcoal-muted)]">
                Previous Owner
              </dt>
              <dd className="mt-1 font-semibold text-[var(--charcoal)]">
                {previous}
              </dd>
            </div>
          )}
          {effective && (
            <div>
              <dt className="text-xs text-[var(--charcoal-muted)]">
                Effective Since
              </dt>
              <dd className="mt-1 font-semibold text-[var(--charcoal)]">
                {effective}
              </dd>
            </div>
          )}
          {confidence !== undefined && (
            <div>
              <dt className="text-xs text-[var(--charcoal-muted)]">
                Confidence
              </dt>
              <dd className="mt-1 font-semibold text-emerald-600">
                {Math.round(confidence * 100)}%
              </dd>
            </div>
          )}
        </dl>
      )}

      {sources.length > 0 && (
        <div className="mt-6 border-t border-black/[0.06] pt-4">
          <p className="text-xs font-semibold uppercase tracking-wider text-[var(--charcoal-muted)] mb-2">
            Grounded By Sources
          </p>
          <div className="flex flex-wrap items-center gap-2">
            {sources.map((s) => (
              <SourceBadge key={s} source={s} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
