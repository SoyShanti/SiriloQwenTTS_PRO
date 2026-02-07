"""
System status and GPU management endpoints.
"""
import torch
from fastapi import APIRouter

from api.deps import get_studio
from api.models import SystemStatusResponse, SystemUnloadResponse

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/status", response_model=SystemStatusResponse)
def get_status():
    studio = get_studio()
    gpu_available = torch.cuda.is_available()
    model_loaded = studio.tts.model is not None
    current_model = studio.tts.current_model_name if model_loaded else None
    voice_count = len(studio.voice_library.list_voices())

    return SystemStatusResponse(
        gpu_available=gpu_available,
        model_loaded=model_loaded,
        current_model=current_model,
        voice_count=voice_count,
    )


@router.post("/unload", response_model=SystemUnloadResponse)
def unload_models():
    studio = get_studio()
    studio.tts.unload_model()
    if hasattr(studio, "asr") and studio.asr.model is not None:
        studio.asr.unload_model()
    torch.cuda.empty_cache()
    return SystemUnloadResponse(message="Models unloaded, GPU memory freed")
