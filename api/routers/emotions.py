"""
Endpoints for emotions, styles, modalities, text analysis, and instruct building.
Read-only, no GPU required.
"""
from fastapi import APIRouter

from src.emotions import (
    EMOTIONS, SPEAKING_STYLES, PACE, INTENSITY, PRESETS, MODALITIES,
    INTENSITY_LEVELS,
    build_instruct, analyze_text, list_modalities,
)
from api.models import (
    EmotionsResponse, BuildInstructRequest, BuildInstructResponse,
    AnalyzeTextRequest, AnalyzeTextResponse,
)

router = APIRouter(prefix="/api/emotions", tags=["emotions"])


@router.get("", response_model=EmotionsResponse)
def get_emotions():
    presets = [
        {"name": name, "description": data["description"], "instruct": data["instruct"]}
        for name, data in PRESETS.items()
    ]
    return EmotionsResponse(
        emotions=list(EMOTIONS.keys()),
        emotion_details=EMOTIONS,
        styles=list(SPEAKING_STYLES.keys()),
        paces=list(PACE.keys()),
        intensities=list(INTENSITY.keys()),
        intensity_levels=INTENSITY_LEVELS,
        presets=presets,
        modalities=list_modalities(),
    )


@router.post("/build-instruct", response_model=BuildInstructResponse)
def build_instruct_endpoint(req: BuildInstructRequest):
    instruct = build_instruct(
        emotion=req.emotion,
        style=req.style,
        pace=req.pace,
        intensity=req.intensity,
        emotion_level=req.emotion_level,
        custom=req.custom,
        add_variation=req.add_variation,
    )
    return BuildInstructResponse(instruct=instruct)


@router.post("/analyze", response_model=AnalyzeTextResponse)
def analyze_text_endpoint(req: AnalyzeTextRequest):
    """Analyze text and return detected emotion with English prompt for Qwen3-TTS."""
    result = analyze_text(req.text, req.language)
    return AnalyzeTextResponse(**result)
