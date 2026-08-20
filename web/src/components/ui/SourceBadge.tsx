import Image from "next/image";
import type { ConnectorStatus } from "@/lib/contracts";

const SOURCE_ICON_MAP: Record<string, { src: string; alt: string; name: string }> = {
  slack: { src: "/brand/slack.svg", alt: "Slack", name: "Slack" },
  gmail: { src: "/brand/gmail.svg", alt: "Gmail", name: "Gmail" },
  linear: { src: "/brand/linear.svg", alt: "Linear", name: "Linear" },
  github: { src: "/brand/github.svg", alt: "GitHub", name: "GitHub" },
  drive: { src: "/brand/drive.svg", alt: "Google Drive", name: "Google Drive" },
  googledrive: { src: "/brand/drive.svg", alt: "Google Drive", name: "Google Drive" },
  notion: { src: "/brand/notion.svg", alt: "Notion", name: "Notion" },
  jira: { src: "/brand/jira.svg", alt: "Jira", name: "Jira" },
  confluence: { src: "/brand/confluence.svg", alt: "Confluence", name: "Confluence" },
  teams: { src: "/brand/teams.svg", alt: "Microsoft Teams", name: "Microsoft Teams" },
  microsoftteams: { src: "/brand/teams.svg", alt: "Microsoft Teams", name: "Microsoft Teams" },
};

export function SourceBadge({
  source,
  status,
  size = "md",
  showLabel = true,
}: {
  source: string;
  status?: ConnectorStatus;
  size?: "xs" | "sm" | "md" | "lg";
  dark?: boolean;
  showLabel?: boolean;
}) {
  const normalizedKey = source.toLowerCase().replace(/[^a-z0-9]/g, "");
  const iconMeta = SOURCE_ICON_MAP[normalizedKey] ?? {
    src: "/brand/continuum-logo.svg",
    alt: source,
    name: source,
  };

  const iconSizes = {
    xs: 12,
    sm: 14,
    md: 16,
    lg: 20,
  };

  const badgePaddings = {
    xs: "px-2.5 py-0.5 text-[10px]",
    sm: "px-3 py-1 text-xs",
    md: "px-3.5 py-1.5 text-xs",
    lg: "px-4 py-2 text-sm",
  };

  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full border border-black/[0.08] bg-white text-[var(--charcoal)] font-medium shadow-2xs transition-all hover:border-black/20 hover:shadow-xs ${badgePaddings[size]}`}
    >
      <Image
        src={iconMeta.src}
        alt={iconMeta.alt}
        width={iconSizes[size]}
        height={iconSizes[size]}
        className="shrink-0 object-contain"
      />
      {showLabel && <span>{iconMeta.name}</span>}
      {status === "connected" && (
        <span className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider text-emerald-700 bg-emerald-50 border border-emerald-200 px-1.5 py-0.2 rounded-full">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
          Live
        </span>
      )}
      {status === "planned" && (
        <span className="rounded-full bg-black/[0.04] px-1.5 py-0.2 text-[9px] font-semibold uppercase tracking-wider text-[var(--charcoal-muted)]">
          Soon
        </span>
      )}
    </span>
  );
}
