"use client";

import { motion } from "framer-motion";

export function AnimatedBackground({
  variant = "marketing",
}: {
  variant?: "marketing" | "product" | "graph";
} = {}) {
  return (
    <div
      data-bg-variant={variant}
      aria-hidden
      className="pointer-events-none fixed inset-0 overflow-hidden z-0"
    >
      {/* Subtle Billow-inspired ambient light glow clouds */}
      <motion.div
        className="absolute -top-40 -left-20 h-[650px] w-[650px] rounded-full bg-gradient-to-br from-indigo-300/15 via-purple-200/10 to-transparent blur-[120px]"
        animate={{
          x: [0, 60, -20, 0],
          y: [0, 40, 20, 0],
          scale: [1, 1.1, 0.95, 1],
        }}
        transition={{
          duration: 22,
          repeat: Infinity,
          ease: "easeInOut",
        }}
      />
      <motion.div
        className="absolute top-1/4 -right-24 h-[700px] w-[700px] rounded-full bg-gradient-to-bl from-sky-300/15 via-indigo-200/10 to-transparent blur-[140px]"
        animate={{
          x: [0, -50, 30, 0],
          y: [0, 60, -30, 0],
          scale: [1.05, 0.92, 1.08, 1.05],
        }}
        transition={{
          duration: 26,
          repeat: Infinity,
          ease: "easeInOut",
        }}
      />
      <motion.div
        className="absolute bottom-10 left-1/3 h-[550px] w-[550px] rounded-full bg-gradient-to-tr from-amber-200/12 via-violet-200/10 to-transparent blur-[130px]"
        animate={{
          x: [0, 35, -35, 0],
          y: [0, -40, 20, 0],
          scale: [0.95, 1.08, 0.95, 0.95],
        }}
        transition={{
          duration: 24,
          repeat: Infinity,
          ease: "easeInOut",
        }}
      />

      {/* Subtle clean stipple / dot matrix grid */}
      <div
        className="absolute inset-0 opacity-[0.035]"
        style={{
          backgroundImage: `radial-gradient(circle, #0f172a 1px, transparent 1px)`,
          backgroundSize: "28px 28px",
        }}
      />
    </div>
  );
}
