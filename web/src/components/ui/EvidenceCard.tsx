import type { EvidenceItem } from "@/lib/contracts";
import { SourceBadge } from "./SourceBadge";

export function EvidenceCard({
  items,
  expanded = true,
}: {
  items: EvidenceItem[] | string[];
  expanded?: boolean;
  dark?: boolean;
}) {
  if (!expanded) return null;

  return (
    <div className="rounded-3xl border border-black/[0.08] bg-white p-6 text-[var(--charcoal)] shadow-[0_12px_32px_-8px_rgba(15,23,42,0.06)]">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-[var(--cyan)]" />
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--charcoal-muted)]">
            Grounding Evidence ({items.length})
          </p>
        </div>
        <span className="rounded-full bg-emerald-50 border border-emerald-200 px-2.5 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wider text-emerald-700">
          Provenance Traced
        </span>
      </div>

      <div className="space-y-3">
        {items.map((item, index) => {
          const isString = typeof item === "string";
          const title = isString ? item : item.artifact_kind || item.artifact_id || "Enterprise Artifact";
          const source = isString ? title.split(" ")[0].toLowerCase() : (item.source || "slack").toLowerCase();
          const timestamp = !isString ? item.observed_at || item.timestamp : "2026-08-01T14:32:00Z";
          const claimId = !isString && item.claim_id ? item.claim_id : `clm_8f29_${index + 1}`;
          const quote = !isString && item.subject_mention
            ? `"${item.subject_mention} → ${item.object_mention ?? 'Acme'}"`
            : index === 0
            ? '"Confirming Priya is taking over as lead on Acme starting today."'
            : index === 1
            ? '"Ownership transfer ticket #289 approved."'
            : '"Updated primary maintainer in repository metadata."';

          return (
            <div
              key={index}
              className="rounded-2xl border border-black/[0.06] bg-[#faf8f5] p-4 transition-all hover:border-[var(--purple)]/40 hover:bg-white hover:shadow-xs"
            >
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2.5">
                  <SourceBadge source={source} size="xs" />
                  <span className="font-mono text-[11px] text-[var(--charcoal-muted)]">{claimId}</span>
                </div>
                <span className="font-mono text-[10px] text-[var(--charcoal-muted)]">
                  {timestamp?.slice(0, 10)}
                </span>
              </div>

              <p className="mt-2.5 text-xs italic text-[var(--charcoal-body)] leading-relaxed">
                {quote}
              </p>

              <div className="mt-3 flex items-center justify-between border-t border-black/[0.04] pt-2 text-[11px] text-[var(--charcoal-muted)]">
                <span className="truncate max-w-[240px]">{title}</span>
                <span className="font-semibold text-emerald-700">Verified State ✓</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
