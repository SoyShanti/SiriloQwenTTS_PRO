"""
Script para descargar los modelos de Qwen3-TTS
Ejecutar una vez antes de usar la aplicación
"""
import os
import sys
from pathlib import Path

# Modelos a descargar
MODELS = [
    "Qwen/Qwen3-TTS-Tokenizer-12Hz",      # Codec de audio (requerido)
    "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",  # TTS principal con clonación
    "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",  # TTS ligero
    "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",  # TTS con diseño de voz
    "Qwen/Qwen3-ASR-1.7B",                    # Transcripción automática
]


def download_models():
    """Descarga todos los modelos necesarios"""
    from huggingface_hub import snapshot_download

    models_dir = Path(__file__).parent / "models"
    models_dir.mkdir(exist_ok=True)

    print("=" * 60)
    print("DESCARGA DE MODELOS QWEN3-TTS")
    print("=" * 60)
    print(f"\nDirectorio de modelos: {models_dir}")
    print(f"Modelos a descargar: {len(MODELS)}\n")

    for i, model_id in enumerate(MODELS, 1):
        model_name = model_id.split("/")[-1]
        local_path = models_dir / model_name

        print(f"\n[{i}/{len(MODELS)}] {model_id}")
        print("-" * 40)

        if local_path.exists() and any(local_path.iterdir()):
            print(f"  Ya existe en: {local_path}")
            continue

        try:
            print(f"  Descargando...")
            snapshot_download(
                repo_id=model_id,
                local_dir=str(local_path),
                local_dir_use_symlinks=False
            )
            print(f"  Completado: {local_path}")

        except Exception as e:
            print(f"  ERROR: {e}")
            print("  Puedes descargarlo manualmente desde:")
            print(f"  https://huggingface.co/{model_id}")

    print("\n" + "=" * 60)
    print("DESCARGA COMPLETADA")
    print("=" * 60)
    print("\nAhora puedes ejecutar: python app.py")


def check_models():
    """Verifica qué modelos están descargados"""
    models_dir = Path(__file__).parent / "models"

    print("\nEstado de modelos:")
    print("-" * 40)

    for model_id in MODELS:
        model_name = model_id.split("/")[-1]
        local_path = models_dir / model_name

        status = "OK" if (local_path.exists() and any(local_path.iterdir())) else "FALTA"
        print(f"  [{status}] {model_name}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        check_models()
    else:
        download_models()
