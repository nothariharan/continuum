"use client";

import Link from "next/link";
import { motion, useMotionValueEvent, useScroll } from "framer-motion";
import { useState } from "react";
import { LogoMark } from "@/components/ui/LogoMark";

const navLinks = [
  { href: "/slack", label: "Slack Setup" },
  { href: "/mcp", label: "Use via MCP" },
];

/**
 * TopNav. When `overHeroOnTop` is set, the bar is transparent with light text
 * while at the very top (over the dark hero), then switches to the light glass
 * treatment once the user scrolls.
 */
export function TopNav({ overHeroOnTop = false }: { overHeroOnTop?: boolean }) {
  const { scrollY } = useScroll();
  const [scrolled, setScrolled] = useState(false);

  useMotionValueEvent(scrollY, "change", (v) => {
    setScrolled(v > 40);
  });

  // "dark mode" styling applies only over the hero, before scrolling.
  const overHero = overHeroOnTop && !scrolled;

  return (
    <motion.header
      className={[
        "sticky top-0 z-50 border-b transition-colors duration-300",
        overHero
          ? "border-transparent bg-[#0a0e1a]"
          : "border-black/[0.08] bg-[var(--paper)]/85 shadow-[0_10px_30px_-10px_rgba(20,20,20,0.08)] backdrop-blur-md",
      ].join(" ")}
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
    >
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
        {/* Logo */}
        <Link href="/" className="group flex items-center gap-2.5">
          <LogoMark size={32} priority />
          <span
            className={[
              "text-[17px] font-semibold tracking-[-0.02em] transition-colors",
              overHero ? "text-white" : "text-[var(--charcoal)]",
            ].join(" ")}
          >
            Continuum
          </span>
        </Link>

        {/* Navigation Links */}
        <nav
          className={[
            "hidden items-center gap-7 text-xs font-medium uppercase tracking-wider transition-colors lg:flex",
            overHero ? "text-white/60" : "text-[var(--charcoal-muted)]",
          ].join(" ")}
        >
          {navLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={[
                "nav-underline transition-colors",
                overHero ? "hover:text-white" : "hover:text-[var(--charcoal)]",
              ].join(" ")}
            >
              {link.label}
            </Link>
          ))}
        </nav>

        {/* Right CTA Area */}
        <div className="flex items-center gap-3.5">
          <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
            <Link
              href="/workspace"
              className={[
                "group inline-flex items-center gap-2 rounded-full px-4 py-2 text-xs font-medium transition-colors",
                overHero
                  ? "bg-white text-[#0a0e1a] hover:bg-white/90"
                  : "bg-[var(--charcoal)] text-white hover:bg-black",
              ].join(" ")}
            >
              <span>Create workspace</span>
              <span
                className={[
                  "text-[10px] transition-transform duration-200 group-hover:translate-x-0.5",
                  overHero ? "text-[#0a0e1a]/50" : "text-zinc-400",
                ].join(" ")}
              >
                →
              </span>
            </Link>
          </motion.div>
        </div>
      </div>
    </motion.header>
  );
}
