import { create } from "zustand";
import type { PresetItem, ModalityItem } from "@/lib/types";

interface StyleState {
  preset: string;
  emotion: string;
  emotionLevel: string;
  style: string;
  pace: string;
  intensity: string;
  customInstruct: string;
  computedInstruct: string;
  selectedModality: string | null;

  // Available options loaded from API
  emotions: string[];
  emotionDetails: Record<string, { low: string; mid: string; high: string }>;
  styles: string[];
  paces: string[];
  intensities: string[];
  intensityLevels: string[];
  presets: PresetItem[];
  modalities: ModalityItem[];

  setPreset: (preset: string) => void;
  setEmotion: (emotion: string) => void;
  setEmotionLevel: (level: string) => void;
  setStyle: (style: string) => void;
  setPace: (pace: string) => void;
  setIntensity: (intensity: string) => void;
  setCustomInstruct: (custom: string) => void;
  setComputedInstruct: (instruct: string) => void;
  setSelectedModality: (modality: string | null) => void;
  setOptions: (data: {
    emotions: string[];
    emotionDetails: Record<string, { low: string; mid: string; high: string }>;
    styles: string[];
    paces: string[];
    intensities: string[];
    intensityLevels: string[];
    presets: PresetItem[];
    modalities: ModalityItem[];
  }) => void;
  reset: () => void;
}

export const useStyleStore = create<StyleState>((set) => ({
  preset: "(custom)",
  emotion: "neutral",
  emotionLevel: "mid",
  style: "conversational",
  pace: "normal",
  intensity: "normal",
  customInstruct: "",
  computedInstruct: "",
  selectedModality: null,

  emotions: [],
  emotionDetails: {},
  styles: [],
  paces: [],
  intensities: [],
  intensityLevels: [],
  presets: [],
  modalities: [],

  setPreset: (preset) => set({ preset, selectedModality: null }),
  setEmotion: (emotion) => set({ emotion }),
  setEmotionLevel: (emotionLevel) => set({ emotionLevel }),
  setStyle: (style) => set({ style }),
  setPace: (pace) => set({ pace }),
  setIntensity: (intensity) => set({ intensity }),
  setCustomInstruct: (customInstruct) => set({ customInstruct }),
  setComputedInstruct: (computedInstruct) => set({ computedInstruct }),
  setSelectedModality: (modality) => set((state) => {
    if (modality) {
      const found = state.modalities.find((m) => m.name === modality);
      return {
        selectedModality: modality,
        preset: "(modality)",
        computedInstruct: found?.instruct ?? "",
      };
    }
    return { selectedModality: null };
  }),
  setOptions: (data) => set({
    emotions: data.emotions,
    emotionDetails: data.emotionDetails,
    styles: data.styles,
    paces: data.paces,
    intensities: data.intensities,
    intensityLevels: data.intensityLevels,
    presets: data.presets,
    modalities: data.modalities,
  }),
  reset: () =>
    set({
      preset: "(custom)",
      emotion: "neutral",
      emotionLevel: "mid",
      style: "conversational",
      pace: "normal",
      intensity: "normal",
      customInstruct: "",
      computedInstruct: "",
      selectedModality: null,
    }),
}));
