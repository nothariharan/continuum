import { TopNav } from "@/components/ui/TopNav";
import { Footer, CTA } from "@/components/ui/Footer";
import { SlackAnswer, MemoryUpdateSection } from "@/components/marketing/SlackSection";
import { ConnectorStatus } from "@/components/product/ConnectorStatus";
import { AnimatedBackground } from "@/components/ui/AnimatedBackground";

export const metadata = {
  title: "Slack Live Integration & Memory Loop — Continuum",
  description: "Continuum in Slack channels: Structured Block Kit answers, real-time handoff event ingestion, and automatic memory updates.",
};

export default function SlackPage() {
  return (
    <div data-theme="marketing" className="min-h-screen bg-[var(--paper)] relative">
      <AnimatedBackground variant="marketing" />
      <div className="relative z-10">
        <TopNav />
        <main className="pt-6">
          <ConnectorStatus />
          <SlackAnswer />
          <MemoryUpdateSection />
        </main>
        <CTA
          title={"Stop searching for the thread.\nAsk your company's memory."}
          primaryHref="/demo"
          primaryLabel="Run Live Demo"
          secondaryHref="/query"
          secondaryLabel="Try Query Console"
        />
        <Footer />
      </div>
    </div>
  );
}
