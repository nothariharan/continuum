import { TopNav } from "@/components/ui/TopNav";
import { Footer, CTA } from "@/components/ui/Footer";
import { RedwoodWorkspace } from "@/components/product/RedwoodWorkspace";

export const metadata = {
  title: "Redwood Inference — Continuum",
  description: "Explore a real EnterpriseRAG-Bench synthetic enterprise workspace: 511,962 records across 9 sources. Ask anything and see Continuum search, resolve, and answer with evidence.",
};

export default function RedwoodPage() {
  return (
    <div data-theme="marketing" className="min-h-screen bg-[var(--paper)]">
      <TopNav />
      <main className="pt-6">
        <RedwoodWorkspace />
      </main>
      <CTA
        title={"One memory.\nEvery company system."}
        primaryHref="/graph"
        primaryLabel="Explore the graph"
        secondaryHref="/mcp"
        secondaryLabel="Use via MCP"
      />
      <Footer />
    </div>
  );
}
