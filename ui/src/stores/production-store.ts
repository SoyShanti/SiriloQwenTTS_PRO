import { create } from "zustand";

interface ProductionState {
  jobId: string;
  status: "idle" | "pending" | "running" | "completed" | "failed";
  progress: number;
  message: string;
  audioUrl: string;
  error: string;

  setJob: (jobId: string) => void;
  setProgress: (status: string, progress: number, message: string) => void;
  setCompleted: (audioUrl: string) => void;
  setFailed: (error: string) => void;
  reset: () => void;
}

export const useProductionStore = create<ProductionState>((set) => ({
  jobId: "",
  status: "idle",
  progress: 0,
  message: "",
  audioUrl: "",
  error: "",

  setJob: (jobId) => set({ jobId, status: "pending", progress: 0, message: "Iniciando...", audioUrl: "", error: "" }),
  setProgress: (status, progress, message) =>
    set({ status: status as ProductionState["status"], progress, message }),
  setCompleted: (audioUrl) => set({ status: "completed", progress: 1, message: "Completado", audioUrl }),
  setFailed: (error) => set({ status: "failed", message: error, error }),
  reset: () => set({ jobId: "", status: "idle", progress: 0, message: "", audioUrl: "", error: "" }),
}));
