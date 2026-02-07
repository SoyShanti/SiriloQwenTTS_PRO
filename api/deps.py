"""
Singleton dependency for VoiceStudio instance.
Same logic as app.py's get_studio() but for FastAPI.
"""
from pathlib import Path
from src.orchestrator import VoiceStudio

_studio: VoiceStudio | None = None
BASE_PATH = Path(__file__).resolve().parent.parent


def get_studio() -> VoiceStudio:
    """Returns singleton VoiceStudio instance."""
    global _studio
    if _studio is None:
        _studio = VoiceStudio(str(BASE_PATH))
    return _studio
