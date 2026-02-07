"""
Deteccion automatica de formato de contenido para el Editor Universal.
Detecta si el contenido es texto plano, script de podcast, o JSON de audiolibro.
"""
import re
import json
from pathlib import Path
from typing import Dict, Tuple, Optional


# Mismo patron que PodcastProcessor.PATTERN
PODCAST_PATTERN = r"\[(\d{1,2}:\d{2})\]\s*(\w+):\s*(.+)"

# Claves que indican formato de audiolibro JSON
AUDIOBOOK_KEYS = {"tts_version", "reading_version", "content"}


def detect_format(content: str) -> str:
    """
    Detecta el formato del contenido textual.

    Args:
        content: Texto o JSON como string

    Returns:
        "audiobook_json" | "podcast_script" | "plain_text"
    """
    stripped = content.strip()

    if not stripped:
        return "plain_text"

    # Intentar parsear como JSON
    if stripped.startswith("{"):
        try:
            data = json.loads(stripped)
            if isinstance(data, dict) and AUDIOBOOK_KEYS & set(data.keys()):
                return "audiobook_json"
        except (json.JSONDecodeError, ValueError):
            pass

    # Verificar patron de podcast: al menos 2 lineas con formato [HH:MM] Speaker: text
    matches = re.findall(PODCAST_PATTERN, stripped)
    if len(matches) >= 2:
        return "podcast_script"

    return "plain_text"


def detect_from_file(file_path: str) -> Tuple[str, str]:
    """
    Detecta formato desde un archivo y retorna el contenido.

    Args:
        file_path: Ruta al archivo (.txt o .json)

    Returns:
        Tupla (formato_detectado, contenido_del_archivo)
    """
    path = Path(file_path)

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Si la extension es .json, intentar primero como audiobook
    if path.suffix.lower() == ".json":
        try:
            data = json.loads(content)
            if isinstance(data, dict) and AUDIOBOOK_KEYS & set(data.keys()):
                return "audiobook_json", content
        except (json.JSONDecodeError, ValueError):
            pass

    fmt = detect_format(content)
    return fmt, content


def get_format_info(format_type: str) -> Dict[str, str]:
    """
    Retorna informacion legible sobre el formato detectado.

    Args:
        format_type: "plain_text" | "podcast_script" | "audiobook_json"

    Returns:
        Dict con "label", "description", "color"
    """
    info = {
        "plain_text": {
            "label": "Texto plano",
            "description": "Texto libre para sintesis de voz directa. Se generara con una sola voz.",
            "color": "#4A90D9",
        },
        "podcast_script": {
            "label": "Script de Podcast",
            "description": "Script multilocutor detectado (formato [MM:SS] Speaker: texto). Asigna una voz a cada speaker.",
            "color": "#D94A8C",
        },
        "audiobook_json": {
            "label": "Audiolibro JSON",
            "description": "JSON estructurado de audiolibro. Se procesara con chunking y crossfade automatico.",
            "color": "#4AD97A",
        },
    }
    return info.get(format_type, info["plain_text"])


def extract_speakers(content: str) -> list:
    """
    Extrae la lista de speakers unicos de un script de podcast.

    Args:
        content: Texto del script

    Returns:
        Lista ordenada de nombres de speakers
    """
    matches = re.findall(PODCAST_PATTERN, content)
    speakers = sorted(set(m[1] for m in matches))
    return speakers
