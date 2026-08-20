import { TopNav } from "./TopNav";
import { Footer } from "./Footer";

export function AppShell({
  children,
  theme = "marketing",
}: {
  children: React.ReactNode;
  theme?: "marketing" | "product";
}) {
  return (
    <div data-theme={theme} className="min-h-screen bg-[var(--paper)]">
      <TopNav />
      <main>{children}</main>
      <Footer />
    </div>
  );
}
