import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Merges Tailwind CSS class names safely, resolving conflicts.
 * Used by all shadcn/ui components.
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Formats a numeric score (0–1) as a percentage string e.g. "87%"
 */
export function formatScore(score: number): string {
  return `${Math.round(score * 100)}%`;
}

/**
 * Returns a Tailwind text-color class based on score value (0–1).
 */
export function scoreColor(score: number): string {
  if (score >= 0.8) return "text-emerald-500";
  if (score >= 0.6) return "text-amber-500";
  return "text-red-500";
}

/**
 * Returns a Tailwind background-color class based on score value (0–1).
 */
export function scoreBg(score: number): string {
  if (score >= 0.8) return "bg-emerald-500/15";
  if (score >= 0.6) return "bg-amber-500/15";
  return "bg-red-500/15";
}
