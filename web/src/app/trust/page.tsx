import { TopNav } from "@/components/ui/TopNav";
import { Footer, CTA } from "@/components/ui/Footer";
import {
  TrustSection,
  TimelineSection,
  ConflictSection,
  BenchmarkPlaceholderSection,
  SecuritySection,
} from "@/components/marketing/SupportSections";
import { AnimatedBackground } from "@/components/ui/AnimatedBackground";

export const metadata = {
  title: "Trust, Provenance & Governance — Continuum",
  description: "Cryptographic provenance chains, temporal state models, first-class contradiction resolution, and enterprise sovereignty.",
};

export default function TrustPage() {
  return (
    <div data-theme="marketing" className="min-h-screen bg-[var(--paper)] relative">
      <AnimatedBackground variant="marketing" />
      <div className="relative z-10">
        <TopNav />
        <main className="pt-6">
          <TrustSection />
          <TimelineSection />
          <ConflictSection />
          <BenchmarkPlaceholderSection />
          <SecuritySection />
        </main>
        <CTA
          title={"Stop searching for the thread.\nAsk your company's memory."}
          primaryHref="/demo"
          primaryLabel="Run Interactive Demo"
          secondaryHref="/graph"
          secondaryLabel="View Graph Explorer"
        />
        <Footer />
      </div>
    </div>
  );
}
