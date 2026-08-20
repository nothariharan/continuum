"use client";

import Image from "next/image";
import { cn } from "@/lib/utils";
import { useCallback, useEffect, useRef } from "react";

/* -----------------------------------------------------------------------------
 * Pixel canvas
 * Animated grid of pixels that ripples in from the center on hover and fades
 * out on leave. Colors are drawn from the card's brand palette.
 * -------------------------------------------------------------------------- */

type Pixel = {
  x: number;
  y: number;
  color: string;
  ctx: CanvasRenderingContext2D;
  speed: number;
  size: number;
  sizeStep: number;
  minSize: number;
  maxSizeInt: number;
  maxSize: number;
  delay: number;
  counter: number;
  counterStep: number;
  isIdle: boolean;
  isReverse: boolean;
  isShimmer: boolean;
  draw: () => void;
  appear: () => void;
  disappear: () => void;
  shimmer: () => void;
};

function createPixel(
  ctx: CanvasRenderingContext2D,
  canvas: HTMLCanvasElement,
  x: number,
  y: number,
  color: string,
  baseSpeed: number,
  delay: number
): Pixel {
  const rand = (min: number, max: number) => Math.random() * (max - min) + min;

  const p: Pixel = {
    x, y, color, ctx,
    speed: rand(0.1, 0.9) * baseSpeed,
    size: 0,
    sizeStep: Math.random() * 0.4,
    minSize: 0.5,
    maxSizeInt: 2,
    maxSize: rand(0.5, 2),
    delay,
    counter: 0,
    counterStep: Math.random() * 4 + (canvas.width + canvas.height) * 0.01,
    isIdle: false,
    isReverse: false,
    isShimmer: false,
    draw() {
      const offset = p.maxSizeInt * 0.5 - p.size * 0.5;
      ctx.fillStyle = p.color;
      ctx.fillRect(p.x + offset, p.y + offset, p.size, p.size);
    },
    appear() {
      p.isIdle = false;
      if (p.counter <= p.delay) {
        p.counter += p.counterStep;
        return;
      }
      if (p.size >= p.maxSize) p.isShimmer = true;
      if (p.isShimmer) p.shimmer();
      else p.size += p.sizeStep;
      p.draw();
    },
    disappear() {
      p.isShimmer = false;
      p.counter = 0;
      if (p.size <= 0) {
        p.isIdle = true;
        return;
      }
      p.size -= 0.1;
      p.draw();
    },
    shimmer() {
      if (p.size >= p.maxSize) p.isReverse = true;
      else if (p.size <= p.minSize) p.isReverse = false;
      if (p.isReverse) p.size -= p.speed;
      else p.size += p.speed;
    },
  };

  return p;
}

type PixelCanvasProps = {
  colors: string[];
  gap?: number;
  speed?: number;
};

function PixelCanvas({ colors, gap = 5, speed = 30 }: PixelCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const pixelsRef = useRef<Pixel[]>([]);
  const animationRef = useRef<number>(0);
  const lastFrameRef = useRef(performance.now());
  const reducedMotionRef = useRef(false);

  const init = useCallback(() => {
    const canvas = canvasRef.current;
    const wrap = wrapRef.current;
    if (!canvas || !wrap) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const { width, height } = wrap.getBoundingClientRect();
    const w = Math.floor(width);
    const h = Math.floor(height);
    canvas.width = w;
    canvas.height = h;
    canvas.style.width = `${w}px`;
    canvas.style.height = `${h}px`;

    const effectiveSpeed = reducedMotionRef.current ? 0 : Math.min(speed, 100) * 0.001;
    const pixels: Pixel[] = [];

    // Each pixel's delay is its distance from the canvas center, so the
    // animation ripples outward from the middle on hover.
    for (let x = 0; x < w; x += gap) {
      for (let y = 0; y < h; y += gap) {
        const color = colors[Math.floor(Math.random() * colors.length)];
        const dx = x - w / 2;
        const dy = y - h / 2;
        const delay = reducedMotionRef.current ? 0 : Math.sqrt(dx * dx + dy * dy);
        pixels.push(createPixel(ctx, canvas, x, y, color, effectiveSpeed, delay));
      }
    }

    pixelsRef.current = pixels;
  }, [colors, gap, speed]);

  const animate = useCallback((mode: "appear" | "disappear") => {
    cancelAnimationFrame(animationRef.current);
    const frameInterval = 1000 / 60;

    const loop = () => {
      animationRef.current = requestAnimationFrame(loop);

      const now = performance.now();
      const elapsed = now - lastFrameRef.current;
      if (elapsed < frameInterval) return;
      lastFrameRef.current = now - (elapsed % frameInterval);

      const canvas = canvasRef.current;
      const ctx = canvas?.getContext("2d");
      if (!canvas || !ctx) return;

      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const pixels = pixelsRef.current;
      for (const pixel of pixels) pixel[mode]();

      if (pixels.every((p) => p.isIdle)) {
        cancelAnimationFrame(animationRef.current);
      }
    };

    animationRef.current = requestAnimationFrame(loop);
  }, []);

  useEffect(() => {
    reducedMotionRef.current = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    init();

    const resizeObserver = new ResizeObserver(() => init());
    if (wrapRef.current) resizeObserver.observe(wrapRef.current);

    // Hover is tracked on the parent card, not the canvas, so that the canvas
    // itself never blocks pointer events on the logo above it.
    const card = wrapRef.current?.parentElement;
    const handleEnter = () => animate("appear");
    const handleLeave = () => animate("disappear");
    card?.addEventListener("mouseenter", handleEnter);
    card?.addEventListener("mouseleave", handleLeave);

    return () => {
      resizeObserver.disconnect();
      cancelAnimationFrame(animationRef.current);
      card?.removeEventListener("mouseenter", handleEnter);
      card?.removeEventListener("mouseleave", handleLeave);
    };
  }, [init, animate]);

  return (
    <div ref={wrapRef} className="absolute inset-0 overflow-hidden">
      <canvas ref={canvasRef} className="block" />
    </div>
  );
}

/* -----------------------------------------------------------------------------
 * Connector data
 * Each source Continuum can ingest. `icon` (optional) is an SVG in /public/brand
 * rendered as a mono-tinted mark; every card shows a wordmark. `brand` drives the
 * per-card hover tint; `pixelColors` feed the shimmer (brand + Continuum indigo).
 * -------------------------------------------------------------------------- */

const INDIGO = ["#6366f1", "#818cf8", "#4f46e5"];

type Connector = {
  name: string;
  icon?: string;
  brand: string;
  pixelColors: string[];
  row: number;
  col: number;
};

const CONNECTORS: Connector[] = [
  // Row 1
  { name: "Slack", icon: "/brand/slack.svg", brand: "#611F69", pixelColors: ["#2FBDEE", "#E9A929", ...INDIGO], row: 1, col: 1 },
  { name: "Gmail", icon: "/brand/gmail.svg", brand: "#EA4335", pixelColors: ["#EA4335", "#4285F4", ...INDIGO], row: 1, col: 2 },
  { name: "Linear", icon: "/brand/linear.svg", brand: "#5E6AD2", pixelColors: ["#5E6AD2", ...INDIGO], row: 1, col: 3 },
  { name: "GitHub", icon: "/brand/github.svg", brand: "#4b5563", pixelColors: ["#6b7280", ...INDIGO], row: 1, col: 4 },
  { name: "Drive", icon: "/brand/drive.svg", brand: "#1FA463", pixelColors: ["#1FA463", "#FFCF63", ...INDIGO], row: 1, col: 5 },

  // Middle sides (center block spans cols 2-4, rows 2-3)
  { name: "Notion", icon: "/brand/notion.svg", brand: "#111827", pixelColors: ["#6b7280", ...INDIGO], row: 2, col: 1 },
  { name: "Jira", icon: "/brand/jira.svg", brand: "#2684FF", pixelColors: ["#2684FF", ...INDIGO], row: 2, col: 5 },
  { name: "Confluence", icon: "/brand/confluence.svg", brand: "#2684FF", pixelColors: ["#2684FF", ...INDIGO], row: 3, col: 1 },
  { name: "Teams", icon: "/brand/teams.svg", brand: "#5059C9", pixelColors: ["#5059C9", ...INDIGO], row: 3, col: 5 },

  // Row 4
  { name: "Zoom", icon: "/brand/zoom.svg", brand: "#2D8CFF", pixelColors: ["#2D8CFF", ...INDIGO], row: 4, col: 1 },
  { name: "Asana", icon: "/brand/asana.svg", brand: "#F06A6A", pixelColors: ["#F06A6A", ...INDIGO], row: 4, col: 2 },
  { name: "Salesforce", icon: "/brand/salesforce.svg", brand: "#00A1E0", pixelColors: ["#00A1E0", ...INDIGO], row: 4, col: 3 },
  { name: "Dropbox", icon: "/brand/dropbox.svg", brand: "#0061FF", pixelColors: ["#0061FF", ...INDIGO], row: 4, col: 4 },
  { name: "Zendesk", icon: "/brand/zendesk.svg", brand: "#03363D", pixelColors: ["#03363D", ...INDIGO], row: 4, col: 5 },
];

/* -----------------------------------------------------------------------------
 * Connector card — pixel shimmer + wordmark. At rest the mark is muted; on hover
 * it lifts to full color with a brand-tinted glow.
 * -------------------------------------------------------------------------- */

function ConnectorCard({ connector }: { connector: Connector }) {
  const { name, icon, brand, pixelColors, row, col } = connector;

  return (
    <div
      className={cn(
        "group relative grid place-items-center overflow-hidden bg-[var(--surface)] cursor-pointer select-none isolate",
        "transition-shadow duration-300 hover:z-[2]",
        "[--brand:var(--brand-light)]",
        "hover:shadow-[0_8px_24px_-8px_color-mix(in_srgb,var(--brand)_25%,transparent),0_0_0_1px_color-mix(in_srgb,var(--brand)_40%,transparent)]"
      )}
      style={
        {
          "--brand-light": brand,
          gridRow: row,
          gridColumn: col,
        } as React.CSSProperties
      }
    >
      <PixelCanvas colors={pixelColors} gap={5} speed={32} />
      <div
        className={cn(
          "relative z-[1] flex items-center gap-2 transition-all duration-300 group-hover:scale-[1.06]",
          "opacity-55 grayscale group-hover:opacity-100 group-hover:grayscale-0"
        )}
      >
        {icon && (
          <Image src={icon} alt="" width={20} height={20} className="h-5 w-5 object-contain" />
        )}
        <span className="text-sm font-semibold tracking-tight text-muted-foreground transition-colors group-hover:text-[var(--brand)]">
          {name}
        </span>
      </div>
    </div>
  );
}

/* -----------------------------------------------------------------------------
 * Component — "Works with your entire stack". 14 connector cards arranged in a
 * 5-column grid with a centered message block. Pixel shimmer per card, tinted
 * in the source's brand color; the grid stays on the Continuum light theme.
 * -------------------------------------------------------------------------- */

export type ComponentProps = {
  /** Small pill label above the heading. */
  badge?: string;
  /** Main heading text. */
  heading?: string;
  /** Sub-copy under the heading. */
  subheading?: string;
};

export const Component = ({
  badge = "Connectors",
  heading = "Works with your entire stack",
  subheading = "Native Slack + Gmail today. Everything else flows in through the same API and MCP layer.",
}: ComponentProps = {}) => {
  return (
    <section className="w-full bg-background px-4 py-20 md:px-12 md:py-24">
      <div
        className="grid grid-cols-5 max-w-[1160px] mx-auto gap-px bg-border border border-border rounded-2xl overflow-hidden shadow-[var(--shadow-elevated)]"
        style={{ gridTemplateRows: "repeat(4, 104px)" }}
      >
        {CONNECTORS.map((connector) => (
          <ConnectorCard key={connector.name} connector={connector} />
        ))}

        <div
          className="flex flex-col items-center justify-center gap-4 bg-card px-6 text-center"
          style={{ gridColumn: "2 / span 3", gridRow: "2 / span 2" }}
        >
          <span className="inline-flex items-center px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] rounded-full bg-card border border-border text-muted-foreground shadow-sm">
            {badge}
          </span>
          <h2 className="font-serif text-3xl md:text-4xl text-foreground max-w-[460px] leading-tight tracking-tight">
            {heading}
          </h2>
          <p className="max-w-[420px] text-sm leading-relaxed text-muted-foreground">
            {subheading}
          </p>
        </div>
      </div>
    </section>
  );
};

export default Component;
