"""
Unified production endpoint with background jobs and SSE progress.
Dispatches to generate_tts / process_audiobook_json / process_podcast_script.
"""
import asyncio
import json
import time
from pathlib import Path
from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from api.deps import get_studio, BASE_PATH
from api.models import ProductionGenerateRequest, ProductionGenerateResponse
from api.services.job_manager import job_manager

router = APIRouter(prefix="/api/production", tags=["production"])


def _run_generation(job_id: str, req: ProductionGenerateRequest):
    """Runs in a thread. Delegates to the appropriate studio method."""
    studio = get_studio()
    output_dir = BASE_PATH / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        job_manager.update_progress(job_id, 0.05, "Loading model...")

        if req.format == "plain_text":
            studio.tts.load_model(req.model_version)
            job_manager.update_progress(job_id, 0.2, "Model loaded, generating audio...")

            voice = studio.voice_library.get_voice(req.voice_name) if req.voice_name else None
            ref_audio = voice["audio_path"] if voice else None
            ref_text = voice["transcript"] if voice else None

            job_manager.update_progress(job_id, 0.3, "Synthesizing speech...")

            output_path = str(output_dir / f"tts_{int(time.time())}.wav")
            audio, sr = studio.tts.generate(
                text=req.content,
                ref_audio_path=ref_audio,
                ref_text=ref_text,
                instruct=req.instruct,
                language=req.language,
                speaker=req.speaker,
                output_path=output_path,
            )
            job_manager.update_progress(job_id, 0.95, "Saving audio...")
            rel_path = Path(output_path).relative_to(BASE_PATH)
            audio_url = f"/{rel_path.as_posix()}"

        elif req.format == "audiobook_json":
            def progress_cb(progress, message):
                job_manager.update_progress(job_id, 0.1 + progress * 0.85, message)

            # Write content to temp JSON file
            tmp_json = output_dir / f"_audiobook_{int(time.time())}.json"
            with open(tmp_json, "w", encoding="utf-8") as f:
                f.write(req.content)

            result_path = studio.process_audiobook_json(
                json_path=str(tmp_json),
                model_version=req.model_version,
                voice_name=req.voice_name,
                speaker=req.speaker,
                language=req.language,
                progress_callback=progress_cb,
            )

            # Clean up temp file
            tmp_json.unlink(missing_ok=True)

            rel_path = Path(result_path).relative_to(BASE_PATH)
            audio_url = f"/{rel_path.as_posix()}"

        elif req.format == "podcast_script":
            if not req.speaker_voices:
                raise ValueError("speaker_voices is required for podcast format")

            def progress_cb(progress, message):
                job_manager.update_progress(job_id, 0.1 + progress * 0.85, message)

            # Write content to temp script file
            tmp_script = output_dir / f"_podcast_{int(time.time())}.txt"
            with open(tmp_script, "w", encoding="utf-8") as f:
                f.write(req.content)

            result_path = studio.process_podcast_script(
                script_path=str(tmp_script),
                speaker_voices=req.speaker_voices,
                model_version=req.model_version,
                language=req.language,
                progress_callback=progress_cb,
            )

            # Clean up temp file
            tmp_script.unlink(missing_ok=True)

            rel_path = Path(result_path).relative_to(BASE_PATH)
            audio_url = f"/{rel_path.as_posix()}"

        else:
            raise ValueError(f"Unknown format: {req.format}")

        job_manager.complete_job(job_id, audio_url)

    except Exception as e:
        job_manager.fail_job(job_id, str(e))


@router.post("/generate", response_model=ProductionGenerateResponse)
async def generate_production(req: ProductionGenerateRequest):
    """Start a background generation job. Returns job_id for SSE progress tracking."""
    job = job_manager.create_job()

    # Run generation in background thread (don't await — it runs asynchronously)
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, _run_generation, job.id, req)

    return ProductionGenerateResponse(job_id=job.id)


@router.get("/progress/{job_id}")
async def stream_progress(job_id: str):
    """SSE endpoint streaming progress events until job completes or fails."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    async def event_generator():
        async for data in job_manager.stream_progress(job_id):
            yield {"event": "progress", "data": json.dumps(data)}

    return EventSourceResponse(event_generator())
