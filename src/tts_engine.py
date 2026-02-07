"""
Motor TTS usando modelos Qwen3-TTS
Optimizado para narracion natural sin cortes bruscos
Soporta: CustomVoice, VoiceDesign, y clonacion de voz
"""
import os
import re
import torch
import soundfile as sf
import numpy as np
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any
from collections import OrderedDict


# Mapeo de modelos disponibles
MODELS = {
    "0.6B": "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
    "1.7B": "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
    "1.7B-VoiceDesign": "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
    "1.7B-Base": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
}

# Capacidades de cada modelo
MODEL_CAPABILITIES = {
    "0.6B": ["custom_voice"],
    "1.7B": ["custom_voice"],
    "1.7B-Base": ["voice_clone"],
    "1.7B-VoiceDesign": ["voice_design"],
}

# Speakers disponibles en CustomVoice
SPEAKERS = {
    "Spanish": ["ryan", "aiden", "serena", "vivian"],
    "Portuguese": ["ryan", "aiden", "serena", "vivian"],
    "English": ["ryan", "aiden", "dylan", "eric"],
    "Chinese": ["vivian", "serena", "uncle_fu"],
    "Japanese": ["ono_anna"],
    "Korean": ["sohee"],
}

ALL_SPEAKERS = ["aiden", "dylan", "eric", "ono_anna", "ryan", "serena", "sohee", "uncle_fu", "vivian"]

# Instruccion optimizada para narracion continua sin caidas de tono
NARRATION_INSTRUCT = "narrando de forma continua y fluida, manteniendo entonacion estable sin caidas abruptas al final de las frases, como un audiolibro profesional"


class AudioProcessor:
    """Utilidades para procesamiento de audio de alta calidad"""

    @staticmethod
    def crossfade_smooth(audio1: np.ndarray, audio2: np.ndarray,
                         fade_ms: int = 300, sample_rate: int = 24000) -> np.ndarray:
        """
        Crossfade suave sin clipping usando curvas de potencia constante

        Args:
            audio1: Primer audio
            audio2: Segundo audio
            fade_ms: Duracion del fade en ms (250-350 recomendado)
            sample_rate: Tasa de muestreo

        Returns:
            Audio combinado con crossfade suave
        """
        fade_samples = int(fade_ms * sample_rate / 1000)

        # Si los audios son muy cortos, concatenar directamente
        if len(audio1) < fade_samples or len(audio2) < fade_samples:
            return np.concatenate([audio1, audio2])

        # Curvas de potencia constante (equal power crossfade)
        # Esto evita el "dip" de volumen en el centro del fade
        t = np.linspace(0, np.pi / 2, fade_samples)
        fade_out = np.cos(t)  # De 1 a 0
        fade_in = np.sin(t)   # De 0 a 1

        # Aplicar fades con atenuacion correcta
        audio1_faded = audio1.copy()
        audio2_faded = audio2.copy()

        audio1_faded[-fade_samples:] = audio1[-fade_samples:] * fade_out
        audio2_faded[:fade_samples] = audio2[:fade_samples] * fade_in

        # Combinar: parte sin fade de audio1 + zona de crossfade + parte sin fade de audio2
        crossfade_zone = audio1_faded[-fade_samples:] + audio2_faded[:fade_samples]

        result = np.concatenate([
            audio1[:-fade_samples],
            crossfade_zone,
            audio2[fade_samples:]
        ])

        return result

    @staticmethod
    def normalize_peak(audio: np.ndarray, target_peak: float = 0.95) -> np.ndarray:
        """Normaliza por pico maximo"""
        peak = np.max(np.abs(audio))
        if peak > 0:
            return audio * (target_peak / peak)
        return audio

    @staticmethod
    def dynamic_normalize(audio: np.ndarray, sample_rate: int = 24000,
                         window_ms: int = 400, target_db: float = -6.0,
                         max_gain: float = 2.5, min_gain: float = 0.6) -> np.ndarray:
        """
        Normalizacion dinamica suave similar a dynaudnorm

        Args:
            audio: Array de audio
            sample_rate: Tasa de muestreo
            window_ms: Ventana de analisis en ms
            target_db: Nivel objetivo en dB
            max_gain: Ganancia maxima permitida
            min_gain: Ganancia minima permitida

        Returns:
            Audio normalizado dinamicamente
        """
        window_samples = int(window_ms * sample_rate / 1000)
        hop_samples = window_samples // 2  # 50% overlap para suavidad
        target_rms = 10 ** (target_db / 20)

        # Calcular envolvente de ganancia
        num_frames = (len(audio) - window_samples) // hop_samples + 1
        gains = np.ones(num_frames)

        for i in range(num_frames):
            start = i * hop_samples
            end = start + window_samples
            window = audio[start:end]
            rms = np.sqrt(np.mean(window ** 2))

            if rms > 0.001:  # Solo ajustar si hay señal
                gain = target_rms / rms
                gains[i] = np.clip(gain, min_gain, max_gain)

        # Suavizar curva de ganancia con filtro de media movil
        kernel_size = 5
        if len(gains) > kernel_size:
            kernel = np.ones(kernel_size) / kernel_size
            gains = np.convolve(gains, kernel, mode='same')

        # Interpolar ganancia a longitud del audio
        gain_interp = np.interp(
            np.arange(len(audio)),
            np.linspace(0, len(audio), len(gains)),
            gains
        )

        # Aplicar ganancia
        result = audio * gain_interp

        # Limitar a rango valido
        return np.clip(result, -1.0, 1.0)

    @staticmethod
    def add_silence(duration_s: float, sample_rate: int = 24000) -> np.ndarray:
        """Genera silencio de duracion especificada"""
        return np.zeros(int(duration_s * sample_rate))

    @staticmethod
    def trim_silence_end(audio: np.ndarray, threshold_db: float = -40,
                         sample_rate: int = 24000) -> np.ndarray:
        """Recorta silencio al final del audio"""
        threshold = 10 ** (threshold_db / 20)

        # Buscar desde el final donde hay señal
        end_idx = len(audio)
        window = int(0.01 * sample_rate)  # Ventana de 10ms

        for i in range(len(audio) - window, 0, -window):
            if np.max(np.abs(audio[i:i+window])) > threshold:
                end_idx = min(i + window * 2, len(audio))  # Dejar un poco de cola
                break

        return audio[:end_idx]


class TextSplitter:
    """
    Divide texto para TTS respetando estructura linguistica
    Con solapamiento de contexto para continuidad prosodica
    """

    # Patrones para segmentacion
    PARAGRAPH_SEP = re.compile(r'\n\s*\n')

    # Abreviaciones comunes que no terminan oracion
    ABBREVIATIONS = {'Dr', 'Sr', 'Sra', 'Srta', 'Prof', 'Ing', 'Lic', 'Jr', 'St',
                     'Mr', 'Mrs', 'Ms', 'vs', 'etc', 'Inc', 'Ltd', 'Corp', 'Ave'}

    @classmethod
    def split_sentences(cls, text: str) -> List[str]:
        """
        Divide texto en oraciones respetando abreviaciones
        """
        sentences = []
        current = ""

        # Tokenizar por espacios y puntuacion
        words = text.split()

        for i, word in enumerate(words):
            current += word + " "

            # Verificar si termina oracion
            if word.rstrip('.,!?;:') in cls.ABBREVIATIONS:
                continue  # No es fin de oracion

            if word.endswith(('.', '!', '?')):
                # Verificar que no sea abreviacion seguida de minuscula
                if i + 1 < len(words):
                    next_word = words[i + 1]
                    if next_word[0].isupper() or word.endswith(('!', '?')):
                        sentences.append(current.strip())
                        current = ""
                else:
                    sentences.append(current.strip())
                    current = ""

        if current.strip():
            sentences.append(current.strip())

        return sentences

    @classmethod
    def split_for_tts(cls, text: str, max_chars: int = 500,
                      overlap_words: int = 4) -> List[Dict[str, Any]]:
        """
        Divide texto para TTS con contexto de solapamiento

        Args:
            text: Texto completo
            max_chars: Maximo caracteres por chunk (Qwen soporta ~2000)
            overlap_words: Palabras de contexto del chunk anterior

        Returns:
            Lista de dicts con 'text', 'is_paragraph_end', 'context_prefix'
        """
        # Para textos muy largos, usar chunks mas grandes para reducir uniones
        if len(text) > 50000:
            max_chars = max(max_chars, 2000)
            overlap_words = max(overlap_words, 6)

        chunks = []

        # Dividir en parrafos
        paragraphs = cls.PARAGRAPH_SEP.split(text)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        previous_context = ""

        for para_idx, paragraph in enumerate(paragraphs):
            # Si el parrafo es corto, mantenerlo completo
            if len(paragraph) <= max_chars:
                chunks.append({
                    'text': paragraph,
                    'context_prefix': previous_context,
                    'is_paragraph_end': True
                })
                # Actualizar contexto: ultimas N palabras
                words = paragraph.split()
                previous_context = " ".join(words[-overlap_words:]) if len(words) > overlap_words else paragraph
                continue

            # Dividir parrafo largo en oraciones
            sentences = cls.split_sentences(paragraph)

            current_chunk = ""
            for sent_idx, sentence in enumerate(sentences):
                is_last = sent_idx == len(sentences) - 1

                if len(current_chunk) + len(sentence) + 1 <= max_chars:
                    current_chunk = (current_chunk + " " + sentence).strip()
                else:
                    # Guardar chunk actual
                    if current_chunk:
                        chunks.append({
                            'text': current_chunk,
                            'context_prefix': previous_context,
                            'is_paragraph_end': False
                        })
                        # Actualizar contexto
                        words = current_chunk.split()
                        previous_context = " ".join(words[-overlap_words:]) if len(words) > overlap_words else current_chunk

                    current_chunk = sentence

            # Ultimo chunk del parrafo
            if current_chunk:
                chunks.append({
                    'text': current_chunk,
                    'context_prefix': previous_context,
                    'is_paragraph_end': True
                })
                words = current_chunk.split()
                previous_context = " ".join(words[-overlap_words:]) if len(words) > overlap_words else current_chunk

        return chunks

    @classmethod
    def estimate_audio_duration(cls, text: str, chars_per_second: float = 14) -> float:
        """Estima duracion del audio en segundos"""
        return len(text) / chars_per_second


class LRUCache:
    """Cache LRU simple para voice clone prompts"""

    def __init__(self, max_size: int = 5):
        self.cache = OrderedDict()
        self.max_size = max_size

    def get(self, key: str):
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        return None

    def put(self, key: str, value):
        if key in self.cache:
            self.cache.move_to_end(key)
        else:
            if len(self.cache) >= self.max_size:
                self.cache.popitem(last=False)
        self.cache[key] = value

    def clear(self):
        self.cache.clear()


class TTSEngine:
    """Motor principal de sintesis de voz con Qwen3-TTS"""

    # Qwen3-TTS puede generar hasta ~10 minutos de audio continuo
    # ~14 caracteres/segundo = ~8400 caracteres para 10 min
    MAX_CHARS_NO_CHUNK = 6000  # Margen de seguridad

    def __init__(self, device: str = "cuda", dtype: torch.dtype = torch.bfloat16):
        self.device = device
        self.dtype = dtype
        self.current_model_name = None
        self.model = None
        self.sample_rate = 24000
        self._voice_clone_cache = LRUCache(max_size=5)
        self.audio_processor = AudioProcessor()
        self.text_splitter = TextSplitter()

    def load_model(self, model_version: str = "1.7B"):
        """Carga el modelo TTS especificado"""
        if self.current_model_name == model_version and self.model is not None:
            return

        self.unload_model()

        model_path = MODELS.get(model_version)
        if model_path is None:
            raise ValueError(f"Modelo no valido: {model_version}. Opciones: {list(MODELS.keys())}")

        print(f"Cargando TTS: {model_path}...")

        from qwen_tts import Qwen3TTSModel

        self.model = Qwen3TTSModel.from_pretrained(
            model_path,
            device_map=f"{self.device}:0" if self.device == "cuda" else self.device,
            dtype=self.dtype,
        )

        self.current_model_name = model_version
        print(f"TTS {model_version} cargado")

    def unload_model(self):
        """Libera memoria del modelo TTS"""
        if self.model is not None:
            del self.model
            self.model = None
        self.current_model_name = None
        self._voice_clone_cache.clear()
        torch.cuda.empty_cache()

    def generate(
        self,
        text: str,
        ref_audio_path: Optional[str] = None,
        ref_text: Optional[str] = None,
        instruct: Optional[str] = None,
        language: str = "Spanish",
        speaker: Optional[str] = None,
        output_path: Optional[str] = None,
        # Parametros de procesamiento
        use_natural_chunking: bool = True,
        crossfade_ms: int = 300,
        paragraph_pause_s: float = 0.4,
        normalize_audio: bool = True,
        add_narration_style: bool = True
    ) -> Tuple[np.ndarray, int]:
        """
        Genera audio desde texto con procesamiento natural

        Args:
            text: Texto a sintetizar
            ref_audio_path: Audio de referencia para clonacion
            ref_text: Transcripcion del audio de referencia
            instruct: Instruccion de estilo personalizada
            language: Idioma
            speaker: Speaker predefinido (para CustomVoice)
            output_path: Ruta de salida opcional
            use_natural_chunking: Dividir texto naturalmente
            crossfade_ms: Duracion del crossfade entre chunks
            paragraph_pause_s: Pausa entre parrafos
            normalize_audio: Aplicar normalizacion dinamica
            add_narration_style: Agregar estilo de narracion fluida

        Returns:
            Tuple (audio_array, sample_rate)
        """
        if self.model is None:
            self.load_model()

        # Preparar instruccion
        final_instruct = self._prepare_instruct(instruct, add_narration_style)

        # Determinar si necesitamos chunking
        text_length = len(text)

        if text_length <= self.MAX_CHARS_NO_CHUNK:
            # Texto corto: generar de una sola vez (mejor calidad)
            audio = self._generate_single(
                text, ref_audio_path, ref_text,
                final_instruct, language, speaker
            )
        else:
            # Texto largo: dividir con contexto de solapamiento
            audio = self._generate_chunked(
                text, ref_audio_path, ref_text,
                final_instruct, language, speaker,
                crossfade_ms, paragraph_pause_s
            )

        # Post-procesamiento
        audio = self.audio_processor.trim_silence_end(audio, sample_rate=self.sample_rate)

        if normalize_audio:
            audio = self.audio_processor.dynamic_normalize(audio, self.sample_rate)

        if output_path:
            sf.write(output_path, audio, self.sample_rate, format='WAV', subtype='PCM_16')

        return audio, self.sample_rate

    def _prepare_instruct(self, custom_instruct: Optional[str], add_narration: bool) -> str:
        """Prepara instruccion final consistente"""
        if custom_instruct:
            if add_narration:
                return f"{custom_instruct}, {NARRATION_INSTRUCT}"
            return custom_instruct
        elif add_narration:
            return NARRATION_INSTRUCT
        return ""

    def _generate_single(
        self, text: str, ref_audio_path: Optional[str], ref_text: Optional[str],
        instruct: str, language: str, speaker: Optional[str]
    ) -> np.ndarray:
        """Genera audio para texto corto (sin chunking)"""
        return self._generate_chunk(text, ref_audio_path, ref_text, instruct, language, speaker)

    def _generate_chunked(
        self, text: str, ref_audio_path: Optional[str], ref_text: Optional[str],
        instruct: str, language: str, speaker: Optional[str],
        crossfade_ms: int, paragraph_pause_s: float
    ) -> np.ndarray:
        """Genera audio para texto largo con chunking inteligente"""

        chunks = self.text_splitter.split_for_tts(text, max_chars=2000, overlap_words=5)

        if len(chunks) == 1:
            return self._generate_chunk(
                chunks[0]['text'], ref_audio_path, ref_text,
                instruct, language, speaker
            )

        all_segments = []

        for i, chunk_info in enumerate(chunks):
            chunk_text = chunk_info['text']
            context_prefix = chunk_info['context_prefix']
            is_para_end = chunk_info['is_paragraph_end']

            # Para chunks despues del primero, incluir contexto
            # Esto ayuda al modelo a mantener la prosodia
            if i > 0 and context_prefix:
                # Generamos con contexto pero luego recortamos
                full_text = f"{context_prefix} {chunk_text}"
                audio = self._generate_chunk(
                    full_text, ref_audio_path, ref_text,
                    instruct, language, speaker
                )
                # Estimar donde empieza el texto nuevo
                context_duration = self.text_splitter.estimate_audio_duration(context_prefix)
                context_samples = int(context_duration * self.sample_rate)
                # Recortar contexto (con pequeño margen para transicion)
                trim_start = max(0, context_samples - int(0.1 * self.sample_rate))
                audio = audio[trim_start:]
            else:
                audio = self._generate_chunk(
                    chunk_text, ref_audio_path, ref_text,
                    instruct, language, speaker
                )

            # Recortar silencios al final de cada chunk
            audio = self.audio_processor.trim_silence_end(audio, sample_rate=self.sample_rate)

            all_segments.append({
                'audio': audio,
                'is_paragraph_end': is_para_end
            })

        # Combinar segmentos
        return self._combine_segments(all_segments, crossfade_ms, paragraph_pause_s)

    def _combine_segments(
        self, segments: List[Dict],
        crossfade_ms: int,
        paragraph_pause_s: float
    ) -> np.ndarray:
        """Combina segmentos con crossfade y pausas naturales"""
        if not segments:
            return np.array([])

        if len(segments) == 1:
            return segments[0]['audio']

        result = segments[0]['audio']

        for i in range(1, len(segments)):
            prev_is_para_end = segments[i - 1]['is_paragraph_end']
            curr_audio = segments[i]['audio']

            # Aplicar crossfade suave
            result = self.audio_processor.crossfade_smooth(
                result, curr_audio, crossfade_ms, self.sample_rate
            )

            # Agregar pausa SOLO si es fin de parrafo
            if prev_is_para_end and paragraph_pause_s > 0:
                pause = self.audio_processor.add_silence(paragraph_pause_s, self.sample_rate)
                # Insertar pausa en el punto del crossfade
                insert_point = len(result) - len(curr_audio) + int(crossfade_ms * self.sample_rate / 1000)
                result = np.concatenate([
                    result[:insert_point],
                    pause,
                    result[insert_point:]
                ])

        return result

    def _generate_chunk(
        self, text: str, ref_audio_path: Optional[str], ref_text: Optional[str],
        instruct: str, language: str, speaker: Optional[str]
    ) -> np.ndarray:
        """Genera audio para un chunk individual"""
        current_caps = MODEL_CAPABILITIES.get(self.current_model_name, [])

        if ref_audio_path and ref_text:
            if "voice_clone" not in current_caps:
                print("Cambiando a modelo 1.7B-Base para clonacion...")
                self.load_model("1.7B-Base")
            return self._generate_clone(text, ref_audio_path, ref_text, language)

        elif "voice_design" in current_caps:
            return self._generate_voice_design(text, instruct, language)

        else:
            if "custom_voice" not in current_caps:
                print("Cambiando a modelo 1.7B para speakers predefinidos...")
                self.load_model("1.7B")
            return self._generate_custom_voice(text, speaker, instruct, language)

    def _generate_custom_voice(
        self, text: str, speaker: Optional[str],
        instruct: str, language: str
    ) -> np.ndarray:
        """Genera audio con speaker predefinido"""
        if not speaker:
            lang_speakers = SPEAKERS.get(language, SPEAKERS["English"])
            speaker = lang_speakers[0] if lang_speakers else "ryan"

        speaker = speaker.lower()
        if speaker not in ALL_SPEAKERS:
            print(f"Speaker '{speaker}' no valido, usando 'ryan'")
            speaker = "ryan"

        wavs, sr = self.model.generate_custom_voice(
            text=text,
            language=language,
            speaker=speaker,
            instruct=instruct or NARRATION_INSTRUCT,
        )

        self.sample_rate = sr
        return wavs[0] if isinstance(wavs, list) else wavs

    def _generate_voice_design(
        self, text: str, instruct: str, language: str
    ) -> np.ndarray:
        """Genera audio con VoiceDesign"""
        wavs, sr = self.model.generate_custom_voice(
            text=text,
            language=language,
            speaker="Ryan",
            instruct=instruct or "natural and clear, maintaining steady intonation",
        )

        self.sample_rate = sr
        return wavs[0] if isinstance(wavs, list) else wavs

    def _generate_clone(
        self, text: str, ref_audio_path: str,
        ref_text: str, language: str
    ) -> np.ndarray:
        """Genera audio clonando voz de referencia"""
        cache_key = f"{ref_audio_path}:{ref_text[:50]}"

        prompt_items = self._voice_clone_cache.get(cache_key)
        if prompt_items is None:
            print(f"Creando prompt de clonacion para: {Path(ref_audio_path).name}")
            prompt_items = self.model.create_voice_clone_prompt(
                ref_audio=ref_audio_path,
                ref_text=ref_text,
            )
            self._voice_clone_cache.put(cache_key, prompt_items)

        wavs, sr = self.model.generate_voice_clone(
            text=text,
            language=language,
            voice_clone_prompt=prompt_items,
        )

        self.sample_rate = sr
        return wavs[0] if isinstance(wavs, list) else wavs

    def get_speakers(self, language: str = None) -> List[str]:
        """Retorna speakers disponibles"""
        if language:
            return SPEAKERS.get(language, ALL_SPEAKERS)
        return ALL_SPEAKERS


class VoiceLibrary:
    """Gestion de voces de referencia y perfiles"""

    def __init__(self, library_path: str):
        self.library_path = Path(library_path)
        self.library_path.mkdir(parents=True, exist_ok=True)
        self.voices: Dict[str, Dict[str, Any]] = {}
        self._load_library()

    def _load_library(self):
        """Carga perfiles de voz existentes"""
        import json

        for json_file in self.library_path.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    profile = json.load(f)
                    self.voices[profile["name"]] = profile
            except Exception as e:
                print(f"Error cargando {json_file}: {e}")

    def add_voice(
        self, name: str, audio_path: str, transcript: str,
        language: str = "Spanish", style_tags: List[str] = None
    ) -> Dict[str, Any]:
        """Agrega una nueva voz a la libreria"""
        import json
        import shutil

        audio_dest = self.library_path / f"{name}.wav"
        shutil.copy2(audio_path, audio_dest)

        profile = {
            "name": name,
            "audio_path": str(audio_dest),
            "transcript": transcript,
            "language": language,
            "style_tags": style_tags or [],
        }

        json_path = self.library_path / f"{name}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(profile, f, ensure_ascii=False, indent=2)

        self.voices[name] = profile
        return profile

    def get_voice(self, name: str) -> Optional[Dict[str, Any]]:
        """Obtiene perfil de voz por nombre"""
        return self.voices.get(name)

    def list_voices(self) -> List[str]:
        """Lista nombres de voces disponibles"""
        return list(self.voices.keys())

    def remove_voice(self, name: str):
        """Elimina una voz de la libreria"""
        if name not in self.voices:
            return

        profile = self.voices[name]
        audio_path = Path(profile["audio_path"])
        json_path = self.library_path / f"{name}.json"

        if audio_path.exists():
            audio_path.unlink()
        if json_path.exists():
            json_path.unlink()

        del self.voices[name]
