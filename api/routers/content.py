"""
Content format detection endpoint.
Wraps src/format_detector.py. No GPU required.
"""
from fastapi import APIRouter

from src.format_detector import detect_format, get_format_info, extract_speakers
from api.models import ContentDetectRequest, ContentDetectResponse

router = APIRouter(prefix="/api/content", tags=["content"])


@router.post("/detect", response_model=ContentDetectResponse)
def detect_content_format(req: ContentDetectRequest):
    fmt = detect_format(req.content)
    info = get_format_info(fmt)

    speakers = []
    if fmt == "podcast_script":
        speakers = extract_speakers(req.content)

    return ContentDetectResponse(
        format=fmt,
        label=info["label"],
        description=info["description"],
        color=info["color"],
        speakers=speakers,
    )
