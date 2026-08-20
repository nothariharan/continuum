import Image from "next/image";

/**
 * LogoMark — the Continuum emblem. Spins one full turn on hover (of itself or
 * an ancestor with the `group` class). Pair with a text wordmark where needed.
 */
export function LogoMark({
  size = 34,
  className = "",
  priority = false,
}: {
  size?: number;
  className?: string;
  priority?: boolean;
}) {
  return (
    <Image
      src="/brand/continuum-mark.png"
      alt="Continuum"
      width={size}
      height={size}
      priority={priority}
      className={`logo-mark select-none ${className}`}
      style={{ height: size, width: size }}
    />
  );
}
