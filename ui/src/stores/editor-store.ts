import { create } from "zustand";
import type { ContentFormat } from "@/lib/types";

interface EditorState {
  content: string;
  format: ContentFormat;
  formatLabel: string;
  formatColor: string;
  formatDescription: string;
  detectedSpeakers: string[];
  fileName: string;

  setContent: (content: string) => void;
  setFormat: (format: ContentFormat, label: string, description: string, color: string, speakers: string[]) => void;
  setFileName: (name: string) => void;
  reset: () => void;
}

export const useEditorStore = create<EditorState>((set) => ({
  content: "",
  format: "plain_text",
  formatLabel: "Texto plano",
  formatColor: "#4A90D9",
  formatDescription: "",
  detectedSpeakers: [],
  fileName: "",

  setContent: (content) => set({ content }),
  setFormat: (format, label, description, color, speakers) =>
    set({ format, formatLabel: label, formatDescription: description, formatColor: color, detectedSpeakers: speakers }),
  setFileName: (fileName) => set({ fileName }),
  reset: () =>
    set({
      content: "",
      format: "plain_text",
      formatLabel: "Texto plano",
      formatColor: "#4A90D9",
      formatDescription: "",
      detectedSpeakers: [],
      fileName: "",
    }),
}));
