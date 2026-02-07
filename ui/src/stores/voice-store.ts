import { create } from "zustand";
import type { VoiceProfile } from "@/lib/types";

interface VoiceState {
  selectedVoice: string;
  selectedSpeaker: string;
  speakerVoiceMap: Record<string, string>;
  qwenSpeakers: string[];
  clonedVoices: VoiceProfile[];

  setSelectedVoice: (voice: string) => void;
  setSelectedSpeaker: (speaker: string) => void;
  setSpeakerVoice: (speaker: string, voice: string) => void;
  setAvailableVoices: (qwen: string[], cloned: VoiceProfile[]) => void;
  reset: () => void;
}

export const useVoiceStore = create<VoiceState>((set) => ({
  selectedVoice: "",
  selectedSpeaker: "",
  speakerVoiceMap: {},
  qwenSpeakers: [],
  clonedVoices: [],

  setSelectedVoice: (selectedVoice) => set({ selectedVoice }),
  setSelectedSpeaker: (selectedSpeaker) => set({ selectedSpeaker }),
  setSpeakerVoice: (speaker, voice) =>
    set((s) => ({ speakerVoiceMap: { ...s.speakerVoiceMap, [speaker]: voice } })),
  setAvailableVoices: (qwenSpeakers, clonedVoices) => set({ qwenSpeakers, clonedVoices }),
  reset: () => set({ selectedVoice: "", selectedSpeaker: "", speakerVoiceMap: {} }),
}));
