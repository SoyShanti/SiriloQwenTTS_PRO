import { create } from "zustand";

interface AppState {
  language: string;
  modelVersion: string;
  gpuAvailable: boolean;
  modelLoaded: boolean;
  currentModel: string | null;

  setLanguage: (language: string) => void;
  setModelVersion: (modelVersion: string) => void;
  setGpuStatus: (available: boolean, loaded: boolean, current: string | null) => void;
}

export const useAppStore = create<AppState>((set) => ({
  language: "Spanish",
  modelVersion: "1.7B",
  gpuAvailable: false,
  modelLoaded: false,
  currentModel: null,

  setLanguage: (language) => set({ language }),
  setModelVersion: (modelVersion) => set({ modelVersion }),
  setGpuStatus: (gpuAvailable, modelLoaded, currentModel) =>
    set({ gpuAvailable, modelLoaded, currentModel }),
}));
