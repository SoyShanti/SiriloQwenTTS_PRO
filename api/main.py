"""
FastAPI application entry point.
CORS, routers, static file serving for /output.
"""
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.routers import emotions, tts, content, voices, production, system

BASE_PATH = Path(__file__).resolve().parent.parent

app = FastAPI(
    title="SiriloQwenTTS PRO",
    description="Professional TTS API powered by Qwen3-TTS",
    version="2.0.0",
)

# CORS — allow Vite dev server and any local origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(emotions.router)
app.include_router(tts.router)
app.include_router(content.router)
app.include_router(voices.router)
app.include_router(production.router)
app.include_router(system.router)

# Serve output/ directory as static files at /output
output_dir = BASE_PATH / "output"
output_dir.mkdir(parents=True, exist_ok=True)
app.mount("/output", StaticFiles(directory=str(output_dir)), name="output")
