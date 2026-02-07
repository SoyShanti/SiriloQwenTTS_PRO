export const API_BASE = "/api";

export const LANGUAGES = ["Spanish", "English", "Portuguese", "Chinese", "Japanese", "Korean"];

export const FORMAT_COLORS: Record<string, string> = {
  plain_text: "#4A90D9",
  podcast_script: "#D94A8C",
  audiobook_json: "#4AD97A",
};

export const FORMAT_LABELS: Record<string, string> = {
  plain_text: "Texto plano",
  podcast_script: "Script de Podcast",
  audiobook_json: "Audiolibro JSON",
};

export const WORKFLOW_STEPS = [
  { id: "content", label: "Contenido", icon: "FileText" },
  { id: "voice", label: "Voz", icon: "Mic" },
  { id: "style", label: "Estilo", icon: "Palette" },
  { id: "generate", label: "Generar", icon: "Play" },
] as const;
