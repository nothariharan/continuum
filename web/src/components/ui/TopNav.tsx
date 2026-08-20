"use client";

import Link from "next/link";
import Image from "next/image";
import { motion, useScroll, useTransform } from "framer-motion";
import { useRef } from "react";

const navLinks = [
  { href: "/query", label: "Query" },
  { href: "/graph", label: "Graph" },
  { href: "/slack", label: "Slack" },
  { href: "/connectors", label: "Connectors" },
  { href: "/mcp", label: "MCP" },
  { href: "/trust", label: "Trust & Time" },
];

export function TopNav() {
  const ref = useRef<HTMLElement>(null);
  const { scrollY } = useScroll();
  const shadow = useTransform(
    scrollY,
    [0, 40],
    ["0 0 0 rgba(0,0,0,0)", "0 10px 30px -10px rgba(20,20,20,0.08)"],
  );
  const border = useTransform(
    scrollY,
    [0, 40],
    ["rgba(0,0,0,0.05)", "rgba(0,0,0,0.09)"],
  );

  return (
    <motion.header
      ref={ref}
      style={{ boxShadow: shadow, borderBottomColor: border }}
      className="sticky top-0 z-50 border-b bg-[var(--paper)]/85 backdrop-blur-md transition-colors"
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
    >
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-3 group">
          <div className="flex items-center gap-2">
            <Image
              src="/brand/continuum-logo.svg"
              alt="Continuum"
              width={140}
              height={30}
              priority
              className="text-[var(--charcoal)]"
            />
          </div>
        </Link>

        {/* Navigation Links */}
        <nav className="hidden items-center gap-7 text-xs font-medium uppercase tracking-wider text-[var(--charcoal-muted)] lg:flex">
          {navLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="transition-colors hover:text-[var(--charcoal)]"
            >
              {link.label}
            </Link>
          ))}
        </nav>

        {/* Right CTA Area */}
        <div className="flex items-center gap-3.5">
          <Link
            href="/graph?entity=account:acme"
            className="hidden text-xs font-medium text-[var(--charcoal-muted)] hover:text-[var(--charcoal)] sm:inline"
          >
            Graph Explorer
          </Link>
          <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
            <Link
              href="/demo?autoplay=1"
              className="inline-flex items-center gap-2 rounded-full bg-[var(--charcoal)] px-4 py-2 text-xs font-medium text-white transition hover:bg-black"
            >
              <span>Explore Demo</span>
              <span className="text-[10px] text-zinc-400">→</span>
            </Link>
          </motion.div>
        </div>
      </div>
    </motion.header>
  );
}
