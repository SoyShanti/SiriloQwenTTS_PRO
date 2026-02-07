"""
Pydantic schemas for all API request/response models.
"""
from pydantic import BaseModel, Field
from typing import Optional


# ── Emotions / Styles ──────────────────────────────────────────────

class EmotionsResponse(BaseModel):
    emotions: list[str]
    emotion_details: dict[str, dict[str, str]]  # {name: {low, mid, high}}
    styles: list[str]
    paces: list[str]
    intensities: list[str]
    intensity_levels: list[str]  # ["low", "mid", "high"]
    presets: list[dict]  # [{name, description, instruct}]
    modalities: list[dict]  # [{name, label, icon, description, instruct}]


class BuildInstructRequest(BaseModel):
    emotion: str = "neutral"
    style: str = "conversational"
    pace: str = "normal"
    intensity: str = "normal"
    emotion_level: str = "mid"
    custom: str = ""
    add_variation: bool = True


class BuildInstructResponse(BaseModel):
    instruct: str


class AnalyzeTextRequest(BaseModel):
    text: str
    language: str = "es"


class AnalyzeTextResponse(BaseModel):
    detected_emotion: str
    intensity_level: str
    intensity_score: float
    rhythm: str
    instruct: str
    confidence: float


# ── TTS Info ───────────────────────────────────────────────────────

class ModelsResponse(BaseModel):
    models: dict[str, str]
    capabilities: dict[str, list[str]]


class SpeakersResponse(BaseModel):
    speakers: dict[str, list[str]]
    all_speakers: list[str]


class TTSGenerateRequest(BaseModel):
    text: str
    voice_name: Optional[str] = None
    model_version: str = "1.7B"
    instruct: Optional[str] = None
    language: str = "Spanish"
    speaker: Optional[str] = None


class TTSGenerateResponse(BaseModel):
    audio_url: str
    duration_seconds: float


# ── Voices ─────────────────────────────────────────────────────────

class VoiceProfile(BaseModel):
    name: str
    audio_path: str
    transcript: str
    language: str
    style_tags: list[str]


class VoiceListResponse(BaseModel):
    qwen_speakers: list[str]
    cloned_voices: list[VoiceProfile]


class VoiceCreateResponse(BaseModel):
    profile: VoiceProfile
    message: str


# ── Content Detection ─────────────────────────────────────────────

class ContentDetectRequest(BaseModel):
    content: str


class ContentDetectResponse(BaseModel):
    format: str
    label: str
    description: str
    color: str
    speakers: list[str]


# ── Production ─────────────────────────────────────────────────────

class ProductionGenerateRequest(BaseModel):
    content: str
    format: str = "plain_text"
    voice_name: Optional[str] = None
    model_version: str = "1.7B"
    language: str = "Spanish"
    instruct: Optional[str] = None
    speaker: Optional[str] = None
    speaker_voices: Optional[dict[str, str]] = None


class ProductionGenerateResponse(BaseModel):
    job_id: str


class ProgressEvent(BaseModel):
    status: str
    progress: float
    message: str
    audio_url: Optional[str] = None
    error: Optional[str] = None


# ── System ─────────────────────────────────────────────────────────

class SystemStatusResponse(BaseModel):
    gpu_available: bool
    model_loaded: bool
    current_model: Optional[str] = None
    voice_count: int


class SystemUnloadResponse(BaseModel):
    message: str
