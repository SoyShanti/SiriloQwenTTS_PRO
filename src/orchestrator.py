"""
Orquestador para procesamiento de Audiolibros y Podcasts
Maneja JSON de audiolibros y scripts de podcast
"""
import os
import re
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Generator
from dataclasses import dataclass
import soundfile as sf
import numpy as np

from .processor import AudioProcessor as AudioCleaner, ASREngine
from .tts_engine import TTSEngine, VoiceLibrary, AudioProcessor


@dataclass
class TextSegment:
    """Segmento de texto con metadata"""
    text: str
    speaker: str
    voice_ref: Optional[str] = None
    style: Optional[str] = None
    timestamp: Optional[str] = None


class AudiobookProcessor:
    """Procesa audiolibros desde JSON estructurado"""

    def __init__(
        self,
        tts_engine: TTSEngine,
        voice_library: VoiceLibrary,
        output_dir: str
    ):
        self.tts = tts_engine
        self.voices = voice_library
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def process_json(
        self,
        json_path: str,
        model_version: str = "1.7B",
        voice_name: Optional[str] = None,
        speaker: Optional[str] = None,
        language: str = "Spanish",
        progress_callback=None
    ) -> str:
        """
        Procesa un JSON de audiolibro

        Formato esperado:
        {
            "reading_version": "texto crudo...",
            "tts_version": "texto optimizado para TTS...",
            "metadata": {
                "chapter_name": "Ch01...",
                ...
            }
        }

        Args:
            json_path: Ruta al archivo JSON
            model_version: Versión del modelo TTS ("0.6B", "1.7B", etc.)
            voice_name: Nombre del perfil de voz a usar (opcional)

        Returns:
            Ruta al audio generado
        """
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Determinar el título/nombre del archivo
        metadata = data.get("metadata", {})
        chapter_name = metadata.get("chapter_name", "")
        if chapter_name:
            book_title = Path(chapter_name).stem
        else:
            book_title = Path(json_path).stem

        # Determinar el texto a sintetizar
        # Prioridad: tts_version > reading_version > content
        if "tts_version" in data and isinstance(data["tts_version"], str) and len(data["tts_version"]) > 100:
            # tts_version contiene el texto optimizado para TTS
            text_content = data["tts_version"]
        elif "reading_version" in data:
            # Usar reading_version como alternativa
            text_content = data["reading_version"]
        elif "content" in data:
            # Formato con segmentos individuales
            text_content = None
            segments = [
                TextSegment(
                    text=item.get("text", ""),
                    speaker=item.get("voice_ref", "narrator"),
                    voice_ref=item.get("voice_ref"),
                    style=item.get("style")
                )
                for item in data["content"]
            ]
        else:
            raise ValueError("JSON debe tener 'tts_version', 'reading_version' o 'content'")

        # Si tenemos texto completo, crear un solo segmento
        if text_content:
            segments = [TextSegment(text=text_content, speaker="narrator")]

        audio_proc = AudioProcessor()

        # Cargar modelo
        self.tts.load_model(model_version)

        # Obtener voz de referencia si se especifico
        ref_audio = None
        ref_text = None
        if voice_name:
            voice = self.voices.get_voice(voice_name)
            if voice:
                ref_audio = voice["audio_path"]
                ref_text = voice["transcript"]

        all_audio_segments = []
        total = len(segments)

        for i, segment in enumerate(segments):
            if progress_callback:
                progress_callback(i / total, f"Procesando segmento {i+1}/{total}")

            # Si el segmento tiene su propia voz, usarla
            seg_ref_audio = ref_audio
            seg_ref_text = ref_text

            if segment.voice_ref:
                voice = self.voices.get_voice(segment.voice_ref)
                if voice:
                    seg_ref_audio = voice["audio_path"]
                    seg_ref_text = voice["transcript"]

            # Generar audio con configuracion natural
            # El TTSEngine ahora maneja chunking, crossfade y normalizacion internamente
            audio, sr = self.tts.generate(
                text=segment.text,
                ref_audio_path=seg_ref_audio,
                ref_text=seg_ref_text,
                instruct=segment.style,
                speaker=speaker,
                language=language,
                use_natural_chunking=True,
                crossfade_ms=300,
                paragraph_pause_s=0.4,
                normalize_audio=False,  # Normalizaremos al final
                add_narration_style=True
            )

            all_audio_segments.append(audio)

        # Combinar segmentos con crossfade suave
        if len(all_audio_segments) == 1:
            final_audio = all_audio_segments[0]
        else:
            final_audio = all_audio_segments[0]
            for i in range(1, len(all_audio_segments)):
                # Pausa entre segmentos principales (capitulos/secciones)
                pause = audio_proc.add_silence(0.5, self.tts.sample_rate)
                final_audio = np.concatenate([final_audio, pause])
                # Crossfade con el siguiente segmento
                final_audio = audio_proc.crossfade_smooth(
                    final_audio, all_audio_segments[i],
                    300, self.tts.sample_rate
                )

        # Normalizacion dinamica final
        final_audio = audio_proc.dynamic_normalize(final_audio, self.tts.sample_rate)

        # Guardar
        output_path = self.output_dir / f"{book_title.replace(' ', '_')}.wav"
        sf.write(str(output_path), final_audio, self.tts.sample_rate, format='WAV', subtype='PCM_16')

        if progress_callback:
            progress_callback(1.0, "Completado")

        return str(output_path)


class PodcastProcessor:
    """Procesa scripts de podcast con múltiples locutores"""

    # Regex para detectar [HH:MM] Speaker: Message
    PATTERN = r"\[(\d{1,2}:\d{2})\]\s*(\w+):\s*(.+)"

    def __init__(
        self,
        tts_engine: TTSEngine,
        voice_library: VoiceLibrary,
        output_dir: str
    ):
        self.tts = tts_engine
        self.voices = voice_library
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.speaker_map: Dict[str, str] = {}  # speaker -> voice_name

    def parse_script(self, script_text: str) -> List[TextSegment]:
        """Parsea script de podcast"""
        segments = []

        for line in script_text.strip().split('\n'):
            line = line.strip()
            if not line:
                continue

            match = re.match(self.PATTERN, line)
            if match:
                timestamp, speaker, text = match.groups()

                # Detectar estilo por puntuación
                style = self._detect_style(text)

                segments.append(TextSegment(
                    text=text,
                    speaker=speaker,
                    timestamp=timestamp,
                    style=style
                ))
            else:
                # Línea sin formato timestamp, agregar como continuación
                if segments:
                    segments[-1].text += " " + line

        return segments

    def _detect_style(self, text: str) -> str:
        """Detecta estilo basado en puntuación y palabras clave"""
        text_lower = text.lower()

        if "?" in text:
            return "con tono inquisitivo"
        elif "!" in text:
            return "con entusiasmo"
        elif "jaja" in text_lower or "jeje" in text_lower:
            return "con tono divertido"
        else:
            return "con tono conversacional"

    def assign_voice(self, speaker: str, voice_name: str):
        """Asigna una voz de la librería a un speaker"""
        self.speaker_map[speaker] = voice_name

    def get_unassigned_speakers(self, segments: List[TextSegment]) -> List[str]:
        """Retorna speakers sin voz asignada"""
        speakers = set(seg.speaker for seg in segments)
        return [s for s in speakers if s not in self.speaker_map]

    def process_script(
        self,
        script_path: str,
        tts_version: str = "1.7B",
        language: str = "Spanish",
        progress_callback=None,
        crossfade_ms: int = 250,
        turn_pause_s: float = 0.35
    ) -> str:
        """
        Procesa script de podcast con audio natural

        Args:
            script_path: Ruta al script
            tts_version: Version del modelo TTS
            language: Idioma
            progress_callback: Callback de progreso
            crossfade_ms: Crossfade entre segmentos (ms)
            turn_pause_s: Pausa entre turnos de habla (segundos)

        Returns:
            Ruta al audio generado
        """
        from .tts_engine import ALL_SPEAKERS

        audio_proc = AudioProcessor()

        with open(script_path, 'r', encoding='utf-8') as f:
            script_text = f.read()

        segments = self.parse_script(script_text)

        # Verificar voces asignadas
        unassigned = self.get_unassigned_speakers(segments)
        if unassigned:
            raise ValueError(f"Speakers sin voz asignada: {unassigned}")

        # Cargar modelo
        self.tts.load_model(tts_version)

        all_audio_segments = []
        total = len(segments)
        prev_speaker = None

        for i, segment in enumerate(segments):
            if progress_callback:
                progress_callback(i / total, f"[{segment.speaker}] {i+1}/{total}")

            # Obtener voz asignada
            voice_name = self.speaker_map.get(segment.speaker)

            # Determinar si es voz clonada o speaker Qwen
            ref_audio = None
            ref_text = None
            qwen_speaker = None

            if voice_name:
                if voice_name.lower() in [s.lower() for s in ALL_SPEAKERS]:
                    qwen_speaker = voice_name.lower()
                else:
                    voice = self.voices.get_voice(voice_name)
                    if voice:
                        ref_audio = voice["audio_path"]
                        ref_text = voice["transcript"]

            # Generar con configuracion natural
            audio, sr = self.tts.generate(
                text=segment.text,
                ref_audio_path=ref_audio,
                ref_text=ref_text,
                speaker=qwen_speaker,
                instruct=segment.style,
                language=language,
                use_natural_chunking=True,
                crossfade_ms=200,  # Crossfade interno mas corto
                normalize_audio=False,  # Normalizaremos al final
                add_narration_style=True
            )

            # Detectar cambio de speaker para pausas
            is_speaker_change = prev_speaker is not None and prev_speaker != segment.speaker
            prev_speaker = segment.speaker

            all_audio_segments.append({
                'audio': audio,
                'is_speaker_change': is_speaker_change
            })

        # Combinar segmentos con crossfade y pausas naturales
        if len(all_audio_segments) == 1:
            final_audio = all_audio_segments[0]['audio']
        else:
            final_audio = all_audio_segments[0]['audio']

            for i in range(1, len(all_audio_segments)):
                curr = all_audio_segments[i]

                # Pausa antes del segmento si hay cambio de speaker
                if curr['is_speaker_change']:
                    pause = audio_proc.add_silence(turn_pause_s, self.tts.sample_rate)
                    final_audio = np.concatenate([final_audio, pause])

                # Aplicar crossfade
                final_audio = audio_proc.crossfade_smooth(
                    final_audio, curr['audio'],
                    crossfade_ms, self.tts.sample_rate
                )

        # Normalizar volumen final
        final_audio = audio_proc.dynamic_normalize(final_audio, self.tts.sample_rate)

        # Guardar
        script_name = Path(script_path).stem
        output_path = self.output_dir / f"{script_name}_podcast.wav"
        sf.write(str(output_path), final_audio, self.tts.sample_rate, format='WAV', subtype='PCM_16')

        if progress_callback:
            progress_callback(1.0, "Completado")

        return str(output_path)


class VoiceStudio:
    """
    Interfaz unificada para todas las operaciones de voz
    """

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)

        # Inicializar componentes
        self.audio_cleaner = AudioCleaner()
        self.asr = ASREngine()
        self.tts = TTSEngine()
        self.voice_library = VoiceLibrary(str(self.base_path / "voice_library"))

        # Procesadores
        self.audiobook = AudiobookProcessor(
            self.tts,
            self.voice_library,
            str(self.base_path / "output")
        )
        self.podcast = PodcastProcessor(
            self.tts,
            self.voice_library,
            str(self.base_path / "output")
        )

    def create_voice_profile(
        self,
        name: str,
        audio_path: str,
        language: str = "Spanish",
        auto_transcribe: bool = True,
        style_tags: List[str] = None
    ) -> Dict:
        """
        Crea perfil de voz desde audio de referencia

        Pipeline completo:
        1. Limpiar audio
        2. Transcribir con ASR
        3. Guardar en librería
        """
        # Limpiar audio
        clean_path = self.audio_cleaner.clean_audio(audio_path)

        # Recortar si es muy largo
        duration = self.audio_cleaner.get_audio_duration(clean_path)
        if duration > 30:
            clean_path = self.audio_cleaner.trim_audio(clean_path, 30)

        # Transcribir
        transcript = ""
        if auto_transcribe:
            self.asr.load_model()
            transcript = self.asr.transcribe(clean_path, language.lower())
            self.asr.unload_model()  # Liberar VRAM

        # Guardar en librería
        profile = self.voice_library.add_voice(
            name=name,
            audio_path=clean_path,
            transcript=transcript,
            language=language,
            style_tags=style_tags
        )

        return profile

    def generate_speech(
        self,
        text: str,
        voice_name: Optional[str] = None,
        model_version: str = "1.7B",
        instruct: Optional[str] = None,
        output_path: Optional[str] = None
    ) -> Tuple[np.ndarray, int]:
        """Genera voz con opciones simplificadas"""

        voice = self.voice_library.get_voice(voice_name) if voice_name else None

        self.tts.load_model(model_version)

        return self.tts.generate(
            text=text,
            ref_audio_path=voice["audio_path"] if voice else None,
            ref_text=voice["transcript"] if voice else None,
            instruct=instruct,
            output_path=output_path
        )

    def process_audiobook_json(
        self,
        json_path: str,
        model_version: str = "1.7B",
        voice_name: Optional[str] = None,
        speaker: Optional[str] = None,
        language: str = "Spanish",
        progress_callback=None
    ) -> str:
        """Procesa audiolibro desde JSON"""
        return self.audiobook.process_json(
            json_path, model_version, voice_name, speaker, language, progress_callback
        )

    def process_podcast_script(
        self,
        script_path: str,
        speaker_voices: Dict[str, str],
        model_version: str = "1.7B",
        language: str = "Spanish",
        progress_callback=None
    ) -> str:
        """
        Procesa podcast con mapeo de voces

        Args:
            script_path: Ruta al script .txt
            speaker_voices: Diccionario {speaker_name: voice_profile_name}
            model_version: Versión del modelo TTS
            language: Idioma para la sintesis
        """
        # Asignar voces
        for speaker, voice in speaker_voices.items():
            self.podcast.assign_voice(speaker, voice)

        return self.podcast.process_script(script_path, model_version, language, progress_callback)
