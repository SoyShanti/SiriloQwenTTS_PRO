import { apiFetch } from "./client";
import type { ContentDetectResult } from "@/lib/types";

export function detectContent(content: string) {
  return apiFetch<ContentDetectResult>("/content/detect", {
    method: "POST",
    body: JSON.stringify({ content }),
  });
}
