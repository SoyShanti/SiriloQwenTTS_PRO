import { apiFetch, apiUpload } from "./client";
import type { VoiceListData } from "@/lib/types";

export function fetchVoices() {
  return apiFetch<VoiceListData>("/voices");
}

export function createVoice(formData: FormData) {
  return apiUpload<{ profile: VoiceListData; message: string }>("/voices", formData);
}

export function deleteVoice(name: string) {
  return apiFetch<{ message: string }>(`/voices/${encodeURIComponent(name)}`, {
    method: "DELETE",
  });
}
