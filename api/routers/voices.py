"""
Voice CRUD endpoints. Upload audio for cloning, list, delete.
"""
import shutil
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from src.tts_engine import ALL_SPEAKERS
from api.deps import get_studio, BASE_PATH
from api.models import VoiceProfile, VoiceListResponse, VoiceCreateResponse

router = APIRouter(prefix="/api/voices", tags=["voices"])


@router.get("", response_model=VoiceListResponse)
def list_voices():
    studio = get_studio()
    cloned = []
    for name in studio.voice_library.list_voices():
        profile = studio.voice_library.get_voice(name)
        if profile:
            cloned.append(VoiceProfile(
                name=profile["name"],
                audio_path=profile["audio_path"],
                transcript=profile.get("transcript", ""),
                language=profile.get("language", "Spanish"),
                style_tags=profile.get("style_tags", []),
            ))
    return VoiceListResponse(qwen_speakers=ALL_SPEAKERS, cloned_voices=cloned)


@router.post("", response_model=VoiceCreateResponse)
async def create_voice(
    name: str = Form(...),
    language: str = Form("Spanish"),
    auto_transcribe: bool = Form(True),
    transcript: str = Form(""),
    style_tags: str = Form(""),
    audio: UploadFile = File(...),
):
    """Create a cloned voice profile from uploaded audio."""
    studio = get_studio()

    # Check name not taken
    if studio.voice_library.get_voice(name):
        raise HTTPException(status_code=409, detail=f"Voice '{name}' already exists")

    # Save uploaded audio to temp location
    upload_dir = BASE_PATH / "voice_library"
    upload_dir.mkdir(parents=True, exist_ok=True)
    temp_path = upload_dir / f"_upload_{name}.wav"

    with open(temp_path, "wb") as f:
        content = await audio.read()
        f.write(content)

    try:
        tags = [t.strip() for t in style_tags.split(",") if t.strip()] if style_tags else []

        if auto_transcribe:
            profile = studio.create_voice_profile(
                name=name,
                audio_path=str(temp_path),
                language=language,
                auto_transcribe=True,
                style_tags=tags,
            )
        else:
            profile = studio.voice_library.add_voice(
                name=name,
                audio_path=str(temp_path),
                transcript=transcript,
                language=language,
                style_tags=tags,
            )

        return VoiceCreateResponse(
            profile=VoiceProfile(**profile),
            message=f"Voice '{name}' created successfully",
        )
    except Exception as e:
        # Clean up temp file on error
        if temp_path.exists():
            temp_path.unlink()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up temp upload file (the real file was copied by add_voice)
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)


@router.delete("/{name}")
def delete_voice(name: str):
    studio = get_studio()
    if not studio.voice_library.get_voice(name):
        raise HTTPException(status_code=404, detail=f"Voice '{name}' not found")
    studio.voice_library.remove_voice(name)
    return {"message": f"Voice '{name}' deleted"}
