import { apiFetch } from "./client";
import type { EmotionsData, BuildInstructRequest, AnalyzeTextRequest, AnalyzeTextResponse } from "@/lib/types";

export function fetchEmotions() {
  return apiFetch<EmotionsData>("/emotions");
}

export function buildInstruct(req: BuildInstructRequest) {
  return apiFetch<{ instruct: string }>("/emotions/build-instruct", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export function analyzeText(req: AnalyzeTextRequest) {
  return apiFetch<AnalyzeTextResponse>("/emotions/analyze", {
    method: "POST",
    body: JSON.stringify(req),
  });
}
