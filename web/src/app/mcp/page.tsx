import { TopNav } from "@/components/ui/TopNav";
import { Footer, CTA } from "@/components/ui/Footer";
import { McpSection } from "@/components/marketing/SupportSections";
import { AnimatedBackground } from "@/components/ui/AnimatedBackground";

export const metadata = {
  title: "MCP Agent Interface — Continuum",
  description: "Model Context Protocol adapter: Equip external AI agents with deterministic state queries, history, and evidence retrieval.",
};

export default function McpPage() {
  return (
    <div data-theme="marketing" className="min-h-screen bg-[var(--paper)] relative">
      <AnimatedBackground variant="marketing" />
      <div className="relative z-10">
        <TopNav />
        <main className="pt-6">
          <McpSection />
        </main>
        <CTA
          title={"Equip your AI agents with\ngrounded company memory."}
          primaryHref="/demo"
          primaryLabel="See Agent Demo"
          secondaryHref="/graph"
          secondaryLabel="Inspect Graph Engine"
        />
        <Footer />
      </div>
    </div>
  );
}
