// ── Emotions / Styles ──────────────────────────────────────

export interface EmotionsData {
  emotions: string[];
  emotion_details: Record<string, { low: string; mid: string; high: string }>;
  styles: string[];
  paces: string[];
  intensities: string[];
  intensity_levels: string[];  // ["low", "mid", "high"]
  presets: PresetItem[];
  modalities: ModalityItem[];
}

export interface PresetItem {
  name: string;
  description: string;
  instruct: string;
}

export interface ModalityItem {
  name: string;
  label: string;
  icon: string;
  description: string;
  instruct: string;
}

export interface BuildInstructRequest {
  emotion: string;
  style: string;
  pace: string;
  intensity: string;
  emotion_level: string;
  custom: string;
  add_variation: boolean;
}

export interface AnalyzeTextRequest {
  text: string;
  language: string;
}

export interface AnalyzeTextResponse {
  detected_emotion: string;
  intensity_level: string;
  intensity_score: number;
  rhythm: string;
  instruct: string;
  confidence: number;
}

// ── TTS ───────────────────────────────────────────────────

export interface ModelsData {
  models: Record<string, string>;
  capabilities: Record<string, string[]>;
}

export interface SpeakersData {
  speakers: Record<string, string[]>;
  all_speakers: string[];
}

// ── Voices ────────────────────────────────────────────────

export interface VoiceProfile {
  name: string;
  audio_path: string;
  transcript: string;
  language: string;
  style_tags: string[];
}

export interface VoiceListData {
  qwen_speakers: string[];
  cloned_voices: VoiceProfile[];
}

// ── Content Detection ─────────────────────────────────────

export type ContentFormat = "plain_text" | "podcast_script" | "audiobook_json";

export interface ContentDetectResult {
  format: ContentFormat;
  label: string;
  description: string;
  color: string;
  speakers: string[];
}

// ── Production ────────────────────────────────────────────

export interface ProductionRequest {
  content: string;
  format: ContentFormat;
  voice_name?: string;
  model_version: string;
  language: string;
  instruct?: string;
  speaker?: string;
  speaker_voices?: Record<string, string>;
}

export interface ProgressEvent {
  status: "pending" | "running" | "completed" | "failed";
  progress: number;
  message: string;
  audio_url?: string;
  error?: string;
}

// ── System ────────────────────────────────────────────────

export interface SystemStatus {
  gpu_available: boolean;
  model_loaded: boolean;
  current_model: string | null;
  voice_count: number;
}
