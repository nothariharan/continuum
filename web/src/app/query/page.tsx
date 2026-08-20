import { TopNav } from "@/components/ui/TopNav";
import { Footer, CTA } from "@/components/ui/Footer";
import { GoldenPathConsole } from "@/components/product/GoldenPathConsole";
import { AnimatedBackground } from "@/components/ui/AnimatedBackground";

export const metadata = {
  title: "Live Query Console — Continuum",
  description: "Query company state, historical lineage, and grounding evidence in real time.",
};

export default function QueryPage() {
  return (
    <div className="min-h-screen bg-[var(--paper)] text-[var(--charcoal)] relative">
      <AnimatedBackground variant="marketing" />
      <div className="relative z-10">
        <TopNav />
        <main className="pt-6">
          <GoldenPathConsole />
        </main>
        <CTA
          title={"Ask once.\nKnow why with full evidence."}
          primaryHref="/demo"
          primaryLabel="Run Interactive Demo"
          secondaryHref="/graph"
          secondaryLabel="Explore Graph Topology"
        />
        <Footer />
      </div>
    </div>
  );
}
