import { TopNav } from "@/components/ui/TopNav";
import { Footer } from "@/components/ui/Footer";
import { WorkspaceOnboarding } from "@/components/product/WorkspaceOnboarding";

export const metadata = {
  title: "Create your workspace — Continuum",
  description: "Continuum Cloud: connect Slack, Gmail, GitHub, Linear and Notion, and build one canonical company memory.",
};

export default function WorkspacePage() {
  return (
    <div data-theme="marketing" className="min-h-screen bg-[var(--paper)]">
      <TopNav />
      <main className="pt-6">
        <WorkspaceOnboarding />
      </main>
      <Footer />
    </div>
  );
}
