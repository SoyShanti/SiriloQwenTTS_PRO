import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

export function parseVoiceName(raw: string): { label: string; isCloned: boolean } {
  const isCloned = raw.startsWith("[Clonada]") || raw.startsWith("[Clone]");
  const label = raw.replace(/^\[(Clonada|Clone|Qwen)\]\s*/, "");
  return { label, isCloned };
}
