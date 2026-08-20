import { TopNav } from "@/components/ui/TopNav";
import { Footer, CTA } from "@/components/ui/Footer";
import { ConnectorsSection } from "@/components/marketing/SupportSections";
import { AnimatedBackground } from "@/components/ui/AnimatedBackground";

export const metadata = {
  title: "Enterprise Connectors & Ecosystem — Continuum",
  description: "Seamlessly ingest, normalize, and reconcile information across Slack, Gmail, Linear, GitHub, Drive, Notion, Jira, and Teams.",
};

export default function ConnectorsPage() {
  return (
    <div data-theme="marketing" className="min-h-screen bg-[var(--paper)] relative">
      <AnimatedBackground variant="marketing" />
      <div className="relative z-10">
        <TopNav />
        <main className="pt-6">
          <ConnectorsSection />
        </main>
        <CTA
          title={"Connect the tools your team\nalready works with every day."}
          primaryHref="/demo"
          primaryLabel="Explore Live Integration"
          secondaryHref="/mcp"
          secondaryLabel="View MCP Agent API"
        />
        <Footer />
      </div>
    </div>
  );
}
