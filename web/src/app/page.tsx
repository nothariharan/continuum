import { TopNav } from "@/components/ui/TopNav";
import { Footer, ClosingCTA } from "@/components/ui/Footer";
import { HowItWorksSection } from "@/components/marketing/HeroSections";
import { HeroConnect } from "@/components/marketing/HeroConnect";
import { ArchitectureFlow } from "@/components/marketing/ArchitectureFlow";
import { NoiseFilterSection } from "@/components/marketing/NoiseFilterSection";
import { Component as WorksWith } from "@/components/ui/pixel-logo-grid";

export default function HomePage() {
  return (
    <div data-theme="marketing" className="min-h-screen bg-[var(--paper)]">
      <TopNav overHeroOnTop />
      <main>
        {/* What it does — dark convergence hero */}
        <HeroConnect />

        {/* The architecture — the product */}
        <ArchitectureFlow />

        {/* How it works */}
        <HowItWorksSection />

        {/* How we filter the noise (funnel) */}
        <NoiseFilterSection />

        {/* Where Continuum plugs in (connectors) */}
        <WorksWith />

        {/* Connect your workplace + MCP over 1B+ docs */}
        <ClosingCTA />
      </main>
      <Footer />
    </div>
  );
}
