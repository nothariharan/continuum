import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/** Merge Tailwind class names, resolving conflicts. Standard shadcn helper. */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
