"""
TTS model info and synchronous generation for short texts.
"""
import time
import soundfile as sf
from pathlib import Path
from fastapi import APIRouter, HTTPException

from src.tts_engine import MODELS, MODEL_CAPABILITIES, SPEAKERS, ALL_SPEAKERS
from api.deps import get_studio, BASE_PATH
from api.models import (
    ModelsResponse, SpeakersResponse,
    TTSGenerateRequest, TTSGenerateResponse,
)

router = APIRouter(prefix="/api/tts", tags=["tts"])


@router.get("/models", response_model=ModelsResponse)
def get_models():
    return ModelsResponse(models=MODELS, capabilities=MODEL_CAPABILITIES)


@router.get("/speakers", response_model=SpeakersResponse)
def get_speakers():
    return SpeakersResponse(speakers=SPEAKERS, all_speakers=ALL_SPEAKERS)


@router.post("/generate", response_model=TTSGenerateResponse)
def generate_tts(req: TTSGenerateRequest):
    """Synchronous TTS for short texts. For long texts use /api/production/generate."""
    studio = get_studio()

    output_dir = BASE_PATH / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = str(output_dir / f"tts_{int(time.time())}.wav")

    try:
        studio.tts.load_model(req.model_version)

        voice = studio.voice_library.get_voice(req.voice_name) if req.voice_name else None
        ref_audio = voice["audio_path"] if voice else None
        ref_text = voice["transcript"] if voice else None

        audio, sr = studio.tts.generate(
            text=req.text,
            ref_audio_path=ref_audio,
            ref_text=ref_text,
            instruct=req.instruct,
            language=req.language,
            speaker=req.speaker,
            output_path=output_path,
        )

        duration = len(audio) / sr
        rel_path = Path(output_path).relative_to(BASE_PATH)
        return TTSGenerateResponse(
            audio_url=f"/{rel_path.as_posix()}",
            duration_seconds=round(duration, 2),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
