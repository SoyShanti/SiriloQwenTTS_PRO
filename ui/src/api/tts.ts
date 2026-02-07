import { apiFetch } from "./client";
import type { ModelsData, SpeakersData } from "@/lib/types";

export function fetchModels() {
  return apiFetch<ModelsData>("/tts/models");
}

export function fetchSpeakers() {
  return apiFetch<SpeakersData>("/tts/speakers");
}
