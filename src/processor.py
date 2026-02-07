"""
Módulo de procesamiento de audio y ASR usando Qwen3-ASR
Limpieza de audio, detección de voz y transcripción automática
"""
import os
import torch
import numpy as np
import librosa
import soundfile as sf
import noisereduce as nr
from pathlib import Path


class AudioProcessor:
    """Procesa y limpia audio de referencia para clonación de voz"""

    def __init__(self, sample_rate: int = 24000):
        self.sample_rate = sample_rate

    def clean_audio(self, input_path: str, output_path: str = None) -> str:
        """
        Limpia el audio usando spectral gating y normalización

        Args:
            input_path: Ruta al audio original
            output_path: Ruta de salida (opcional)

        Returns:
            Ruta al audio limpio
        """
        y, sr = librosa.load(input_path, sr=self.sample_rate)

        # Reducción de ruido estacionario
        y_clean = nr.reduce_noise(y=y, sr=sr, prop_decrease=0.8)

        # Voice Activity Detection - extraer partes con voz
        intervals = librosa.effects.split(y_clean, top_db=25)

        if len(intervals) > 0:
            y_clean = np.concatenate([y_clean[start:end] for start, end in intervals])

        # Normalización
        y_final = librosa.util.normalize(y_clean)

        if output_path is None:
            base = Path(input_path)
            # Siempre guardar como .wav (soundfile no soporta opus/ogg)
            output_path = str(base.parent / f"{base.stem}_clean.wav")

        sf.write(output_path, y_final, self.sample_rate, format='WAV', subtype='PCM_16')
        return output_path

    def get_audio_duration(self, audio_path: str) -> float:
        """Retorna duración del audio en segundos"""
        y, sr = librosa.load(audio_path, sr=None)
        return len(y) / sr

    def trim_audio(self, input_path: str, max_duration: float = 30.0) -> str:
        """
        Recorta audio a duración máxima (ideal 5-30s para clonación)
        """
        y, sr = librosa.load(input_path, sr=self.sample_rate)
        max_samples = int(max_duration * sr)

        if len(y) > max_samples:
            y = y[:max_samples]

        base = Path(input_path)
        output_path = str(base.parent / f"{base.stem}_trimmed.wav")
        sf.write(output_path, y, sr, format='WAV', subtype='PCM_16')
        return output_path


class ASREngine:
    """Motor de transcripción automática usando Qwen3-ASR-1.7B"""

    # Mapeo de idiomas
    LANGUAGE_MAP = {
        "spanish": "Spanish",
        "portuguese": "Portuguese",
        "english": "English",
        "Spanish": "Spanish",
        "Portuguese": "Portuguese",
        "English": "English",
    }

    def __init__(self, model_path: str = "Qwen/Qwen3-ASR-1.7B", device: str = "cuda"):
        self.device = device
        self.model_path = model_path
        self.model = None

    def load_model(self):
        """Carga el modelo ASR en memoria"""
        if self.model is not None:
            return

        print(f"Cargando ASR: {self.model_path}...")

        from qwen_asr import Qwen3ASRModel

        self.model = Qwen3ASRModel.from_pretrained(
            self.model_path,
            dtype=torch.bfloat16,
            device_map=f"{self.device}:0" if self.device == "cuda" else self.device,
            max_new_tokens=512,
        )

        print("ASR cargado")

    def transcribe(self, audio_path: str, language: str = "spanish") -> str:
        """
        Transcribe audio a texto

        Args:
            audio_path: Ruta al archivo de audio
            language: Idioma del audio (spanish, portuguese, english)

        Returns:
            Texto transcrito
        """
        self.load_model()

        # Mapear idioma al formato esperado
        lang = self.LANGUAGE_MAP.get(language, None)

        results = self.model.transcribe(
            audio=audio_path,
            language=lang,  # None para detección automática
        )

        if results and len(results) > 0:
            return results[0].text.strip()
        return ""

    def unload_model(self):
        """Libera memoria del modelo ASR"""
        if self.model is not None:
            del self.model
            self.model = None
            torch.cuda.empty_cache()
            print("ASR descargado de memoria")
