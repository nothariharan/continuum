import { TopNav } from "@/components/ui/TopNav";
import { Footer, CTA } from "@/components/ui/Footer";
import {
  HeroSection,
  ProblemSection,
  HowItWorksSection,
} from "@/components/marketing/HeroSections";
import { OrbitConstellation } from "@/components/marketing/OrbitConstellation";
import { FeatureExploreGrid } from "@/components/marketing/FeatureExploreGrid";
import { AnimatedBackground } from "@/components/ui/AnimatedBackground";

export default function HomePage() {
  return (
    <div data-theme="marketing" className="min-h-screen bg-[var(--paper)] relative">
      <AnimatedBackground variant="marketing" />
      <div className="relative z-10">
        <TopNav />
        <main>
          {/* Section 1: Hero & Animated Query Simulation */}
          <HeroSection />

          {/* Section 2: Fragmentation Problem */}
          <ProblemSection />

          {/* Section 3: Visual Thesis — Continuous Revolving Orbit Constellation */}
          <OrbitConstellation />

          {/* Section 4: How It Works — 3-Stage Transformation Pipeline */}
          <HowItWorksSection />

          {/* Section 5: Modular Feature Deep-Dive Explorer */}
          <FeatureExploreGrid />

          {/* Section 6: Editorial Closing CTA */}
          <CTA />
        </main>
        <Footer />
      </div>
    </div>
  );
}
