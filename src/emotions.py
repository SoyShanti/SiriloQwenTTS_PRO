"""
Sistema inteligente de control de entonacion para Qwen3-TTS.
Usa prompts en INGLES (el modelo los entiende mejor) incluso para contenido en espanol/portugues.
Incluye emociones con 3 niveles de intensidad, modalidades "swipe", y analisis automatico de texto.
"""
import re
from typing import List, Tuple, Dict

# ── Emociones con 3 niveles de intensidad (prompts en ingles) ──

EMOTIONS = {
    "neutral":     {"low": "calm and neutral",      "mid": "matter-of-fact",        "high": "professional and detached"},
    "joy":         {"low": "cheerful",               "mid": "happy and upbeat",      "high": "ecstatic and energetic"},
    "sadness":     {"low": "melancholic",            "mid": "sad and reflective",    "high": "deeply sorrowful"},
    "anger":       {"low": "annoyed",                "mid": "angry and frustrated",  "high": "furious and intense"},
    "fear":        {"low": "nervous",                "mid": "anxious and worried",   "high": "terrified and panicked"},
    "surprise":    {"low": "surprised",              "mid": "amazed and astonished", "high": "shocked and stunned"},
    "disgust":     {"low": "displeased",             "mid": "disgusted",             "high": "revolted"},
    "excitement":  {"low": "enthusiastic",           "mid": "excited and lively",    "high": "thrilled and explosive"},
    "confidence":  {"low": "assured",                "mid": "confident and firm",    "high": "commanding and powerful"},
    "curiosity":   {"low": "inquisitive",            "mid": "curious and intrigued", "high": "fascinated and eager"},
    "tenderness":  {"low": "gentle",                 "mid": "warm and tender",       "high": "deeply loving and intimate"},
    "mystery":     {"low": "subtle and enigmatic",   "mid": "mysterious and intriguing", "high": "dark and suspenseful"},
    "drama":       {"low": "slightly dramatic",      "mid": "dramatic and expressive",   "high": "intensely theatrical"},
    "sarcasm":     {"low": "dry wit",                "mid": "sarcastic and ironic",  "high": "biting sarcasm"},
    "tiredness":   {"low": "slightly weary",         "mid": "tired and drained",     "high": "exhausted and fading"},
}

# ── Estilos de narracion (en ingles) ──

SPEAKING_STYLES = {
    "conversational": "warm, friendly and conversational tone",
    "narration":      "professional narrator voice, like an audiobook",
    "news":           "as a news anchor, clear and authoritative",
    "whisper":        "soft whisper with intimate delivery",
    "shout":          "loudly, shouting with force",
    "question":       "with rising intonation, questioning",
    "affirmation":    "with firm, decisive affirmation",
    "doubt":          "hesitant, with uncertainty",
    "reflective":     "thoughtful pace with contemplative pauses",
    "explanatory":    "as a teacher, clear and didactic",
    "intimate":       "intimate and close, soft delivery",
    "professional":   "professional and corporate tone",
    "playful":        "playful tone with light laughter undertones",
    "authoritative":  "loud, commanding voice with firm pauses",
    "friendly":       "warm and approachable, like talking to a friend",
}

# ── Ritmo (en ingles) ──

PACE = {
    "normal":   "",
    "fast":     "fast pace",
    "slow":     "slow pace",
    "dramatic": "with strategic pauses",
    "fluid":    "smooth and flowing without pauses",
}

# ── Volumen / Intensidad de voz (en ingles) ──

INTENSITY = {
    "normal":    "",
    "soft":      "softly, with delicate voice",
    "loud":      "loudly, with powerful voice",
    "whispered": "whispering",
    "projected": "projecting the voice clearly",
}

# ── Modalidades predefinidas (sistema "Swipe") ──

MODALITIES = {
    "narrator": {
        "label": "Narrador",
        "icon": "mic",
        "description": "Narrador profesional, ritmo estable",
        "instruct": "calm, professional narrator voice with moderate pace",
    },
    "theatrical": {
        "label": "Teatral",
        "icon": "drama",
        "description": "Dramatico y expresivo con variaciones de tono",
        "instruct": "dramatic and expressive with dynamic pitch changes",
    },
    "conversational": {
        "label": "Conversacional",
        "icon": "chat",
        "description": "Tono calido y amigable",
        "instruct": "warm, friendly and conversational tone",
    },
    "melancholic": {
        "label": "Melancolico",
        "icon": "cloud",
        "description": "Ritmo lento, tono suave y triste",
        "instruct": "slow pace, melancholic with soft delivery",
    },
    "passionate": {
        "label": "Apasionado",
        "icon": "flame",
        "description": "Energico con entonacion ascendente",
        "instruct": "energetic, passionate with rising intonation",
    },
    "whisper": {
        "label": "Susurrante",
        "icon": "ear",
        "description": "Susurro suave e intimo",
        "instruct": "soft whisper with intimate delivery",
    },
    "commanding": {
        "label": "Autoritario",
        "icon": "megaphone",
        "description": "Voz firme y comandante",
        "instruct": "loud, commanding voice with firm pauses",
    },
    "reflective": {
        "label": "Reflexivo",
        "icon": "brain",
        "description": "Ritmo pausado y contemplativo",
        "instruct": "thoughtful pace with contemplative pauses",
    },
    "playful": {
        "label": "Jugueton",
        "icon": "smile",
        "description": "Tono ligero y divertido",
        "instruct": "playful tone with light laughter undertones",
    },
    "suspense": {
        "label": "Suspenso",
        "icon": "eye",
        "description": "Tenso, con pausas estrategicas",
        "instruct": "tense, building suspense with strategic pauses",
    },
}

# ── Presets heredados (ahora con prompts en ingles) ──

PRESETS = {
    "dialogo_casual": {
        "description": "Conversacion informal entre amigos",
        "instruct": "warm, relaxed and natural, like chatting with a friend",
    },
    "entrevista": {
        "description": "Tono de entrevista profesional",
        "instruct": "professional yet friendly, like in an interview",
    },
    "historia_emocionante": {
        "description": "Narrando una historia con emocion",
        "instruct": "expressive storytelling with emotional variation, like a captivating tale",
    },
    "explicacion_clara": {
        "description": "Explicando un tema con claridad",
        "instruct": "clear and didactic, like a good teacher explaining",
    },
    "debate_apasionado": {
        "description": "Discusion con pasion",
        "instruct": "passionate and convicted, like defending an important position",
    },
    "comedia": {
        "description": "Tono comico y divertido",
        "instruct": "with comedic timing and funny tone, like a comedian",
    },
    "drama": {
        "description": "Escena dramatica intensa",
        "instruct": "with dramatic intensity and deep emotion",
    },
    "misterio": {
        "description": "Atmosfera de suspenso",
        "instruct": "mysterious tone with tension, building suspense",
    },
    "motivacional": {
        "description": "Discurso inspirador",
        "instruct": "motivational and inspiring energy, like a coach",
    },
    "meditacion": {
        "description": "Tono calmado y relajante",
        "instruct": "calm, slow and relaxing voice, like guiding a meditation",
    },
    "noticia_urgente": {
        "description": "Noticia de ultima hora",
        "instruct": "urgent and serious, like breaking news",
    },
    "cuento_infantil": {
        "description": "Historia para ninos",
        "instruct": "magical and expressive tone, like telling a fairy tale to children",
    },
    "confesion": {
        "description": "Momento intimo y personal",
        "instruct": "intimate and vulnerable tone, like sharing a secret",
    },
    "celebracion": {
        "description": "Momento de alegria",
        "instruct": "joyful and celebratory, like announcing great news",
    },
    "despedida": {
        "description": "Momento emotivo de despedida",
        "instruct": "nostalgic with contained emotion, like a meaningful farewell",
    },
}

# ── Analisis automatico de texto ──

EMOTION_KEYWORDS = {
    "joy": {
        "es": ["genial", "fantastico", "maravilloso", "increible", "jaja", "jeje", "risa", "divertido", "feliz", "alegria", "excelente"],
        "pt": ["otimo", "fantastico", "maravilhoso", "incrivel", "rsrs", "engracado", "alegre", "feliz", "excelente"],
    },
    "sadness": {
        "es": ["triste", "lamentable", "pena", "perdida", "despedida", "adios", "vacio", "soledad", "llanto", "dolor"],
        "pt": ["triste", "lamentavel", "perda", "despedida", "adeus", "vazio", "solidao", "choro", "dor"],
    },
    "anger": {
        "es": ["odio", "detesto", "inaceptable", "furioso", "exijo", "injusto", "rabia", "maldito", "basta"],
        "pt": ["odio", "detesto", "inaceptavel", "furioso", "exijo", "injusto", "raiva", "maldito", "basta"],
    },
    "fear": {
        "es": ["miedo", "terror", "panico", "horrible", "peligro", "asustado", "temblar", "amenaza"],
        "pt": ["medo", "terror", "panico", "horrivel", "perigo", "assustado", "tremer", "ameaca"],
    },
    "surprise": {
        "es": ["sorpresa", "increible", "imposible", "no puedo creer", "asombroso", "inesperado"],
        "pt": ["surpresa", "incrivel", "impossivel", "nao acredito", "espantoso", "inesperado"],
    },
    "curiosity": {
        "es": ["por que", "como", "interesante", "curioso", "me pregunto", "averiguar"],
        "pt": ["por que", "como", "interessante", "curioso", "me pergunto", "descobrir"],
    },
}

PUNCTUATION_CUES = {
    "!!":  {"emotion": "excitement", "intensity_boost": 0.4},
    "?!":  {"emotion": "surprise",   "intensity_boost": 0.3},
    "!":   {"emotion": "excitement", "intensity_boost": 0.2},
    "...": {"emotion": "sadness",    "intensity_boost": 0.1},
    "?":   {"emotion": "curiosity",  "intensity_boost": 0.1},
}


def analyze_text(text: str, language: str = "es") -> Dict:
    """
    Analiza texto y devuelve emocion detectada con prompt en ingles para Qwen3-TTS.

    Args:
        text: Texto a analizar (en espanol o portugues)
        language: "es" o "pt"

    Returns:
        Dict con detected_emotion, intensity, rhythm, instruct, confidence
    """
    lang = language[:2].lower()
    if lang not in ("es", "pt"):
        lang = "es"

    text_lower = text.lower()

    # 1. Scoring por palabras clave
    emotion_scores: Dict[str, float] = {}
    for emotion, kw_dict in EMOTION_KEYWORDS.items():
        score = 0.0
        for word in kw_dict.get(lang, []):
            if word in text_lower:
                score += 0.3
        emotion_scores[emotion] = score

    # 2. Scoring por puntuacion
    punct_boost_emotion = None
    for punct, cue in PUNCTUATION_CUES.items():
        count = text.count(punct)
        if count > 0:
            emo = cue["emotion"]
            boost = cue["intensity_boost"] * min(count, 3)
            emotion_scores[emo] = emotion_scores.get(emo, 0) + boost
            if punct_boost_emotion is None:
                punct_boost_emotion = emo

    # 3. Ritmo por longitud promedio de frases
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    avg_length = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)

    if avg_length < 8:
        rhythm = "fast pace"
    elif avg_length > 15:
        rhythm = "slow pace"
    else:
        rhythm = "moderate pace"

    # 4. Determinar emocion dominante
    dominant = max(emotion_scores, key=lambda k: emotion_scores[k]) if emotion_scores else "neutral"
    top_score = emotion_scores.get(dominant, 0.0)

    # Si ningun score supera umbral, neutral
    if top_score < 0.2:
        dominant = "neutral"
        top_score = 0.0

    # 5. Mapear a nivel de intensidad
    if top_score < 0.4:
        level = "low"
    elif top_score < 0.7:
        level = "mid"
    else:
        level = "high"

    # 6. Construir instruct en ingles
    if dominant in EMOTIONS:
        base_prompt = EMOTIONS[dominant][level]
    else:
        base_prompt = "calm and neutral"

    instruct = f"{base_prompt}, {rhythm}"

    confidence = min(0.95, max(0.2, top_score + 0.15))

    return {
        "detected_emotion": dominant,
        "intensity_level": level,
        "intensity_score": round(top_score, 2),
        "rhythm": rhythm,
        "instruct": instruct,
        "confidence": round(confidence, 2),
    }


# ── Funciones de construccion de instruct ──

def build_instruct(
    emotion: str = "neutral",
    style: str = "conversational",
    pace: str = "normal",
    intensity: str = "normal",
    emotion_level: str = "mid",
    custom: str = "",
    add_variation: bool = True,
) -> str:
    """
    Construye un prompt en ingles combinando parametros.
    Qwen3-TTS entiende mejor instrucciones en ingles.
    """
    parts = []

    # Emocion con nivel de intensidad
    if emotion != "neutral" and emotion in EMOTIONS:
        parts.append(EMOTIONS[emotion].get(emotion_level, EMOTIONS[emotion]["mid"]))

    # Estilo de habla
    if style in SPEAKING_STYLES:
        parts.append(SPEAKING_STYLES[style])

    # Ritmo
    if pace != "normal" and pace in PACE:
        parts.append(PACE[pace])

    # Volumen/intensidad
    if intensity != "normal" and intensity in INTENSITY:
        parts.append(INTENSITY[intensity])

    # Custom (puede ser en ingles o espanol)
    if custom:
        parts.append(custom)

    if parts:
        instruct = ", ".join(parts)
    else:
        instruct = "natural and expressive delivery"

    return instruct


def get_preset_instruct(preset_name: str) -> str:
    """Obtiene la instruccion de un preset predefinido"""
    if preset_name in PRESETS:
        return PRESETS[preset_name]["instruct"]
    return ""


def get_modality_instruct(modality_name: str) -> str:
    """Obtiene la instruccion de una modalidad"""
    if modality_name in MODALITIES:
        return MODALITIES[modality_name]["instruct"]
    return ""


def list_emotions() -> List[str]:
    return list(EMOTIONS.keys())


def list_styles() -> List[str]:
    return list(SPEAKING_STYLES.keys())


def list_presets() -> List[Tuple[str, str]]:
    return [(name, data["description"]) for name, data in PRESETS.items()]


def list_modalities() -> List[Dict]:
    return [
        {"name": name, "label": data["label"], "icon": data["icon"],
         "description": data["description"], "instruct": data["instruct"]}
        for name, data in MODALITIES.items()
    ]


# ── Exportar listas para UI ──

EMOTION_CHOICES = list(EMOTIONS.keys())
STYLE_CHOICES = list(SPEAKING_STYLES.keys())
PACE_CHOICES = list(PACE.keys())
INTENSITY_CHOICES = list(INTENSITY.keys())
PRESET_CHOICES = ["(custom)"] + list(PRESETS.keys())
MODALITY_CHOICES = list(MODALITIES.keys())
INTENSITY_LEVELS = ["low", "mid", "high"]
