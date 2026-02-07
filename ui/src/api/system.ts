import { apiFetch } from "./client";
import type { SystemStatus } from "@/lib/types";

export function fetchStatus() {
  return apiFetch<SystemStatus>("/system/status");
}

export function unloadModels() {
  return apiFetch<{ message: string }>("/system/unload", { method: "POST" });
}
