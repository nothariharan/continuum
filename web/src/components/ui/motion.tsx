"use client";

import { motion, type HTMLMotionProps, type Variants } from "framer-motion";
import { type ReactNode } from "react";

export const easeOut = [0.22, 1, 0.36, 1] as const;

export const fadeUp: Variants = {
  hidden: { opacity: 0, y: 28 },
  visible: { opacity: 1, y: 0 },
};

export const fadeIn: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1 },
};

export const scaleIn: Variants = {
  hidden: { opacity: 0, scale: 0.92 },
  visible: { opacity: 1, scale: 1 },
};

export const stagger = (delay = 0.08): Variants => ({
  hidden: {},
  visible: {
    transition: { staggerChildren: delay, delayChildren: 0.05 },
  },
});

export function Reveal({
  children,
  className,
  delay = 0,
  y = 28,
  ...props
}: HTMLMotionProps<"div"> & { delay?: number; y?: number }) {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.65, delay, ease: easeOut }}
      {...props}
    >
      {children}
    </motion.div>
  );
}

export function Stagger({
  children,
  className,
  delay = 0.08,
}: {
  children: ReactNode;
  className?: string;
  delay?: number;
}) {
  return (
    <motion.div
      className={className}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, margin: "-60px" }}
      variants={stagger(delay)}
    >
      {children}
    </motion.div>
  );
}

export function StaggerItem({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <motion.div className={className} variants={fadeUp} transition={{ duration: 0.55, ease: easeOut }}>
      {children}
    </motion.div>
  );
}

export function FlowDot({ className }: { className?: string }) {
  return (
    <motion.span
      className={`inline-block h-2 w-2 rounded-full bg-[var(--purple)] ${className ?? ""}`}
      animate={{ y: [0, 6, 0], opacity: [0.4, 1, 0.4] }}
      transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }}
    />
  );
}

export function AnimatedArrow() {
  return (
    <motion.span
      className="inline-flex text-[var(--purple)]"
      animate={{ y: [0, 4, 0] }}
      transition={{ duration: 1.2, repeat: Infinity, ease: "easeInOut" }}
    >
      ↓
    </motion.span>
  );
}

export function PulseRing({ className }: { className?: string }) {
  return (
    <motion.div
      className={`pointer-events-none absolute inset-0 rounded-full border border-[var(--purple)]/30 ${className ?? ""}`}
      animate={{ scale: [1, 1.06, 1], opacity: [0.35, 0.12, 0.35] }}
      transition={{ duration: 3.5, repeat: Infinity, ease: "easeInOut" }}
    />
  );
}
