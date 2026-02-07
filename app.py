"""
SiriloQwenTTS Pro - UI
Sistema de sintesis de voz con Qwen3-TTS
"""
import os
import sys
import json
import tempfile
from pathlib import Path
from typing import Optional, Tuple, List, Dict

import gradio as gr
import numpy as np
import soundfile as sf
import torch

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent))

from src.orchestrator import VoiceStudio
from src.tts_engine import SPEAKERS, ALL_SPEAKERS
from src.emotions import (
    EMOTION_CHOICES, STYLE_CHOICES, PACE_CHOICES, INTENSITY_CHOICES,
    PRESET_CHOICES, PRESETS, build_instruct, get_preset_instruct
)
from src.format_detector import detect_format, detect_from_file, get_format_info, extract_speakers

# Configuracion
BASE_PATH = Path(__file__).parent
STUDIO: Optional[VoiceStudio] = None


def get_studio() -> VoiceStudio:
    """Singleton del VoiceStudio"""
    global STUDIO
    if STUDIO is None:
        STUDIO = VoiceStudio(str(BASE_PATH))
    return STUDIO


def unload_models() -> str:
    """Libera todos los modelos de la memoria GPU"""
    global STUDIO
    if STUDIO is not None:
        STUDIO.tts.unload_model()
        STUDIO.asr.unload_model()
    torch.cuda.empty_cache()
    return "Modelos descargados de la GPU. Memoria liberada."


def get_all_voices() -> List[str]:
    """Retorna todas las voces disponibles (Qwen + Clonadas)"""
    # Voces Qwen predefinidas
    qwen_voices = [f"[Qwen] {s}" for s in ALL_SPEAKERS]

    # Voces clonadas (solo si studio ya existe)
    cloned_voices = []
    try:
        studio = get_studio()
        cloned_voices = [f"[Clonada] {name}" for name in studio.voice_library.list_voices()]
    except Exception:
        pass

    return cloned_voices + qwen_voices


def get_voices_for_language(language: str, return_list: bool = False):
    """Retorna speakers predefinidos + voces clonadas para un idioma"""
    # Speakers predefinidos para el idioma
    predefined = SPEAKERS.get(language, ALL_SPEAKERS)
    predefined_labeled = [f"[Qwen] {s}" for s in predefined]

    # Voces clonadas del usuario (filtrar por idioma)
    cloned = []
    try:
        studio = get_studio()
        for name, profile in studio.voice_library.voices.items():
            if profile.get("language", "") == language:
                cloned.append(f"[Clonada] {name}")
    except Exception:
        pass

    # Combinar: primero clonadas, luego predefinidas
    all_voices = cloned + predefined_labeled

    if not all_voices:
        all_voices = ["(sin voces)"]

    if return_list:
        return all_voices

    return gr.update(choices=all_voices, value=all_voices[0] if all_voices else None)


def get_initial_voices():
    """Obtiene voces iniciales incluyendo clonadas"""
    # Voces Qwen para Spanish
    qwen = [f"[Qwen] {s}" for s in SPEAKERS.get("Spanish", ALL_SPEAKERS)]

    # Intentar cargar voces clonadas
    cloned = []
    try:
        studio = get_studio()
        for name, profile in studio.voice_library.voices.items():
            if profile.get("language", "") == "Spanish":
                cloned.append(f"[Clonada] {name}")
    except Exception:
        pass

    return cloned + qwen


def create_voice_profile(
    name: str,
    audio_file,
    language: str,
    auto_transcribe: bool,
    manual_transcript: str,
    style_tags: str
):
    """Crea un nuevo perfil de voz"""
    if not name or not audio_file:
        return "Error: Nombre y audio son requeridos", None

    studio = get_studio()

    try:
        tags = [t.strip() for t in style_tags.split(",") if t.strip()] if style_tags else None

        profile = studio.create_voice_profile(
            name=name,
            audio_path=audio_file,
            language=language,
            auto_transcribe=auto_transcribe and not manual_transcript,
            style_tags=tags
        )

        # Si hay transcripcion manual, actualizar
        if manual_transcript:
            profile["transcript"] = manual_transcript
            json_path = studio.voice_library.library_path / f"{name}.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(profile, f, ensure_ascii=False, indent=2)

        return f"Voz '{name}' creada exitosamente", json.dumps(profile, indent=2, ensure_ascii=False)

    except Exception as e:
        return f"Error: {str(e)}", None


def generate_tts(
    text: str,
    voice_name: str,
    model_version: str,
    instruct: str,
    language: str
):
    """Genera audio desde texto"""
    # Validacion de entradas
    if not text or not text.strip():
        return None, "Error: El texto no puede estar vacio"

    text = text.strip()
    if len(text) > 100000:
        return None, "Error: Texto demasiado largo (max 100,000 caracteres). Usa el procesador de audiolibros."

    studio = get_studio()

    try:
        # Parsear el tipo de voz
        cloned_voice = None
        speaker = None

        if voice_name and voice_name != "(sin voces)":
            if voice_name.startswith("[Clonada] "):
                cloned_voice = voice_name.replace("[Clonada] ", "")
            elif voice_name.startswith("[Qwen] "):
                speaker = voice_name.replace("[Qwen] ", "")
            else:
                speaker = voice_name

        # Cargar modelo
        studio.tts.load_model(model_version)

        # Obtener datos de voz clonada si aplica
        ref_audio = None
        ref_text = None
        if cloned_voice:
            voice_profile = studio.voice_library.get_voice(cloned_voice)
            if voice_profile:
                ref_audio = voice_profile["audio_path"]
                ref_text = voice_profile["transcript"]
            else:
                return None, f"Error: Voz clonada '{cloned_voice}' no encontrada en la libreria"

        # Generar audio
        audio, sr = studio.tts.generate(
            text=text,
            ref_audio_path=ref_audio,
            ref_text=ref_text,
            speaker=speaker,
            instruct=instruct if instruct else None,
            language=language
        )

        # Guardar temporalmente para reproducir
        (BASE_PATH / "output").mkdir(parents=True, exist_ok=True)
        output_path = str(BASE_PATH / "output" / "last_generation.wav")
        sf.write(output_path, audio, sr, format='WAV', subtype='PCM_16')

        return output_path, f"Generado: {len(audio)/sr:.1f}s de audio"

    except FileNotFoundError as e:
        return None, f"Error: Archivo no encontrado - {str(e)}"
    except RuntimeError as e:
        if "CUDA" in str(e) or "out of memory" in str(e):
            return None, f"Error de GPU (sin memoria): Intenta con un texto mas corto o libera la GPU. {str(e)}"
        return None, f"Error de ejecucion: {str(e)}"
    except Exception as e:
        return None, f"Error inesperado: {str(e)}"


def process_audiobook(json_file, model_version: str, voice_name: str, language: str, progress=gr.Progress()):
    """Procesa un audiolibro desde JSON"""
    if not json_file:
        return None, "Error: Archivo JSON requerido"

    studio = get_studio()

    try:
        def update_progress(value, message):
            progress(value, desc=message)

        # Parsear el tipo de voz
        cloned_voice = None
        speaker = None

        if voice_name and voice_name != "(sin voces)":
            if voice_name.startswith("[Clonada] "):
                cloned_voice = voice_name.replace("[Clonada] ", "")
            elif voice_name.startswith("[Qwen] "):
                speaker = voice_name.replace("[Qwen] ", "")
            else:
                speaker = voice_name

        output_path = studio.process_audiobook_json(
            json_file,
            model_version=model_version,
            voice_name=cloned_voice,
            speaker=speaker,
            language=language,
            progress_callback=update_progress
        )

        return output_path, f"Audiolibro generado: {output_path}"

    except Exception as e:
        return None, f"Error: {str(e)}"


# === Funciones del Editor Universal (Proyecto) ===

def on_content_change(text_content):
    """Detecta formato cuando el usuario escribe texto"""
    if not text_content or not text_content.strip():
        info = get_format_info("plain_text")
        return (
            f"**{info['label']}**",
            # plain_text panel visible, podcast panel hidden
            gr.update(visible=True),
            gr.update(visible=False),
            "",  # podcast info
        )

    fmt = detect_format(text_content)
    info = get_format_info(fmt)

    is_podcast = fmt == "podcast_script"
    is_plain_or_audiobook = not is_podcast

    # Extract speakers if podcast
    podcast_info_text = ""
    if is_podcast:
        speakers = extract_speakers(text_content)
        podcast_info_text = f"Detectados {len(speakers)} speakers: {', '.join(speakers)}"

    return (
        f"**{info['label']}** - {info['description']}",
        gr.update(visible=is_plain_or_audiobook),
        gr.update(visible=is_podcast),
        podcast_info_text,
    )


def on_file_upload(file_obj):
    """Detecta formato cuando el usuario sube un archivo"""
    if not file_obj:
        info = get_format_info("plain_text")
        return (
            "",  # text content
            f"**{info['label']}**",
            gr.update(visible=True),
            gr.update(visible=False),
            "",
        )

    try:
        fmt, content = detect_from_file(file_obj)
        info = get_format_info(fmt)

        is_podcast = fmt == "podcast_script"
        is_plain_or_audiobook = not is_podcast

        podcast_info_text = ""
        if is_podcast:
            speakers = extract_speakers(content)
            podcast_info_text = f"Detectados {len(speakers)} speakers: {', '.join(speakers)}"

        # For audiobook JSON, show a summary instead of raw JSON
        display_content = content
        if fmt == "audiobook_json":
            try:
                data = json.loads(content)
                preview_text = data.get("tts_version", data.get("reading_version", ""))
                if len(preview_text) > 500:
                    preview_text = preview_text[:500] + "..."
                display_content = f"[Audiolibro JSON cargado]\n\n{preview_text}"
            except (json.JSONDecodeError, ValueError):
                pass

        return (
            display_content,
            f"**{info['label']}** - {info['description']}",
            gr.update(visible=is_plain_or_audiobook),
            gr.update(visible=is_podcast),
            podcast_info_text,
        )

    except Exception as e:
        return (
            "",
            f"Error al leer archivo: {str(e)}",
            gr.update(visible=True),
            gr.update(visible=False),
            "",
        )


def update_podcast_speaker_dropdowns(text_content):
    """Actualiza dropdowns de speakers para podcast"""
    if not text_content:
        return [gr.update(visible=False)] * 6

    speakers = extract_speakers(text_content)
    all_voices = get_all_voices()

    updates = []
    for i in range(6):
        if i < len(speakers):
            updates.append(gr.update(
                visible=True,
                label=f"{speakers[i]}:",
                choices=all_voices,
                value=all_voices[0] if all_voices else None
            ))
        else:
            updates.append(gr.update(visible=False))

    return updates


def process_universal(
    text_content, file_obj, voice_name, model_version, language,
    preset, emotion, style, pace, intensity, custom_instruct,
    pv1, pv2, pv3, pv4, pv5, pv6,
    progress=gr.Progress()
):
    """
    Funcion unificada que despacha al procesador correcto segun formato.
    Reemplaza generate_tts, process_audiobook, y process_podcast_final.
    """
    # Determinar contenido y formato
    content = ""
    fmt = "plain_text"
    source_file = None

    if file_obj:
        fmt, content = detect_from_file(file_obj)
        source_file = file_obj
    elif text_content and text_content.strip():
        content = text_content.strip()
        fmt = detect_format(content)
    else:
        return None, "Error: Escribe texto o sube un archivo"

    # Construir instruccion de estilo
    if preset and preset != "(personalizado)" and preset in PRESETS:
        instruct = PRESETS[preset]["instruct"]
    else:
        instruct = build_instruct(
            emotion or "neutral",
            style or "conversacional",
            pace or "normal",
            intensity or "normal",
            custom_instruct or ""
        )

    studio = get_studio()
    info = get_format_info(fmt)

    try:
        if fmt == "plain_text":
            # Despachar a generate_tts
            progress(0.1, "Generando audio desde texto plano...")
            result_audio, result_status = generate_tts(
                content, voice_name, model_version, instruct, language
            )
            if result_audio:
                return result_audio, f"[{info['label']}] {result_status}"
            return None, result_status

        elif fmt == "audiobook_json":
            # Guardar contenido JSON a archivo temporal si vino de texto
            if not source_file:
                tmp = tempfile.NamedTemporaryFile(
                    mode='w', suffix='.json', delete=False, encoding='utf-8'
                )
                tmp.write(content)
                tmp.close()
                source_file = tmp.name

            progress(0.1, "Procesando audiolibro JSON...")
            result_audio, result_status = process_audiobook(
                source_file, model_version, voice_name, language, progress
            )
            if result_audio:
                return result_audio, f"[{info['label']}] {result_status}"
            return None, result_status

        elif fmt == "podcast_script":
            # Guardar script a archivo temporal si vino de texto
            if not source_file:
                tmp = tempfile.NamedTemporaryFile(
                    mode='w', suffix='.txt', delete=False, encoding='utf-8'
                )
                tmp.write(content)
                tmp.close()
                source_file = tmp.name

            # Obtener speakers y crear voice_map
            speakers = extract_speakers(content)
            voice_selections = [pv1, pv2, pv3, pv4, pv5, pv6]

            voice_map = {}
            for i, speaker in enumerate(speakers):
                if i < len(voice_selections) and voice_selections[i]:
                    voice = voice_selections[i]
                    if voice.startswith("[Clonada] "):
                        voice_map[speaker] = voice.replace("[Clonada] ", "")
                    elif voice.startswith("[Qwen] "):
                        voice_map[speaker] = voice.replace("[Qwen] ", "")
                    else:
                        voice_map[speaker] = voice

            missing = [s for s in speakers if s not in voice_map]
            if missing:
                return None, f"Error: Falta asignar voz a: {', '.join(missing)}"

            progress(0.1, "Procesando podcast...")

            def update_progress(value, message):
                progress(value, desc=message)

            output_path = studio.process_podcast_script(
                source_file,
                voice_map,
                model_version,
                language,
                progress_callback=update_progress
            )
            return output_path, f"[{info['label']}] Podcast generado: {output_path}"

    except Exception as e:
        return None, f"Error: {str(e)}"

    return None, "Error: Formato no reconocido"


CUSTOM_CSS = """
.main-title { text-align: center; margin-bottom: 1rem; }
.tab-content { padding: 1rem; }
.info-box { background: #f0f4f8; padding: 1rem; border-radius: 8px; margin-bottom: 1rem; }
.speaker-mapping { border: 1px solid #ddd; padding: 10px; border-radius: 8px; margin-top: 10px; }
.segment-controls { background: #f8f9fa; padding: 1rem; border-radius: 8px; margin: 0.5rem 0; }
.emotion-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.5rem; }

/* Editor Universal - Pasos numerados */
.step-header {
    background: linear-gradient(135deg, #4A52A8 0%, #6366f1 100%);
    color: white;
    padding: 0.5rem 1rem;
    border-radius: 8px 8px 0 0;
    font-weight: bold;
    font-size: 0.95rem;
}
.step-content {
    border: 1px solid #e2e8f0;
    border-top: none;
    border-radius: 0 0 8px 8px;
    padding: 1rem;
    margin-bottom: 1rem;
}

/* Badge de formato detectado */
.format-badge {
    padding: 0.4rem 0.8rem;
    border-radius: 20px;
    font-weight: 600;
    font-size: 0.9rem;
    background: #e2e8f0;
    display: inline-block;
}

/* Panel contextual */
.contextual-panel {
    background: #fafbfc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 1rem;
    transition: all 0.3s ease;
}

/* Boton principal de generar */
.generate-main-btn {
    background: linear-gradient(135deg, #4A52A8, #6366f1) !important;
    font-size: 1.1rem !important;
    padding: 0.8rem 2rem !important;
}
"""


def build_ui():
    """Construye la interfaz de Gradio"""

    with gr.Blocks(title="SiriloQwenTTS Pro") as app:

        gr.Markdown(
            """
            # SiriloQwenTTS Pro
            ### Sistema de sintesis de voz con Qwen3-TTS para RTX 3060
            """,
            elem_classes="main-title"
        )

        with gr.Tabs():

            # === TAB 1: Proyecto (Editor Universal) ===
            with gr.Tab("Proyecto", id="project"):
                gr.Markdown("### Editor Universal - Texto, Audiolibro o Podcast en un solo lugar")

                # Estado interno
                proj_detected_format = gr.State("plain_text")

                # --- PASO 1: Contenido ---
                gr.Markdown("#### PASO 1: Contenido", elem_classes="step-header")
                with gr.Group(elem_classes="step-content"):
                    with gr.Row():
                        proj_file = gr.File(
                            label="Subir archivo (.txt / .json)",
                            file_types=[".txt", ".json"],
                            scale=1
                        )
                        proj_text = gr.Textbox(
                            label="O escribe / pega tu contenido aqui",
                            placeholder="Texto plano, script de podcast ([MM:SS] Speaker: texto), o JSON de audiolibro...",
                            lines=6,
                            scale=2
                        )

                    with gr.Row():
                        proj_format_display = gr.Markdown(
                            value="**Texto plano** - Escribe o sube un archivo para detectar el formato automaticamente.",
                            elem_classes="format-badge"
                        )

                    with gr.Row():
                        proj_language = gr.Dropdown(
                            choices=["Spanish", "Portuguese", "English", "Chinese", "Japanese", "Korean"],
                            value="Spanish",
                            label="Idioma",
                            scale=1
                        )
                        proj_model = gr.Radio(
                            choices=["0.6B", "1.7B"],
                            value="1.7B",
                            label="Modelo TTS",
                            info="1.7B = mejor calidad, 0.6B = mas rapido",
                            scale=1
                        )

                # --- PASO 2: Voz (contextual) ---
                gr.Markdown("#### PASO 2: Voz", elem_classes="step-header")
                with gr.Group(elem_classes="step-content"):

                    # Panel para texto plano / audiolibro (voz unica)
                    with gr.Group(visible=True, elem_classes="contextual-panel") as proj_voice_single_panel:
                        proj_voice = gr.Dropdown(
                            choices=get_initial_voices(),
                            label="Voz",
                            allow_custom_value=True,
                            info="[Qwen] = voces del modelo, [Clonada] = voces creadas en 'Crear Voz'"
                        )

                    # Panel para podcast (multiples speakers)
                    with gr.Group(visible=False, elem_classes="contextual-panel") as proj_podcast_panel:
                        proj_podcast_info = gr.Textbox(
                            label="Speakers detectados",
                            interactive=False,
                            lines=1
                        )
                        gr.Markdown("**Asignar voz a cada speaker:**")
                        all_voice_choices = get_all_voices()
                        proj_spk1 = gr.Dropdown(choices=all_voice_choices, label="Speaker 1", visible=False)
                        proj_spk2 = gr.Dropdown(choices=all_voice_choices, label="Speaker 2", visible=False)
                        proj_spk3 = gr.Dropdown(choices=all_voice_choices, label="Speaker 3", visible=False)
                        proj_spk4 = gr.Dropdown(choices=all_voice_choices, label="Speaker 4", visible=False)
                        proj_spk5 = gr.Dropdown(choices=all_voice_choices, label="Speaker 5", visible=False)
                        proj_spk6 = gr.Dropdown(choices=all_voice_choices, label="Speaker 6", visible=False)

                proj_speaker_dropdowns = [proj_spk1, proj_spk2, proj_spk3, proj_spk4, proj_spk5, proj_spk6]

                # --- PASO 3: Estilo ---
                gr.Markdown("#### PASO 3: Estilo", elem_classes="step-header")
                with gr.Group(elem_classes="step-content"):
                    with gr.Row():
                        proj_preset = gr.Dropdown(
                            choices=PRESET_CHOICES,
                            value="(personalizado)",
                            label="Preset rapido",
                            scale=1
                        )
                    with gr.Row():
                        proj_emotion = gr.Dropdown(choices=EMOTION_CHOICES, value="neutral", label="Emocion")
                        proj_style = gr.Dropdown(choices=STYLE_CHOICES, value="conversacional", label="Estilo")
                        proj_pace = gr.Dropdown(choices=PACE_CHOICES, value="normal", label="Ritmo")
                        proj_intensity = gr.Dropdown(choices=INTENSITY_CHOICES, value="normal", label="Intensidad")
                    proj_custom_instruct = gr.Textbox(
                        label="Instruccion personalizada (opcional)",
                        placeholder="ej: con tono profesional y calmado"
                    )
                    proj_instruct_preview = gr.Textbox(
                        label="Instruccion resultante",
                        interactive=False
                    )

                # --- PASO 4: Generar ---
                gr.Markdown("#### PASO 4: Generar", elem_classes="step-header")
                with gr.Group(elem_classes="step-content"):
                    proj_generate_btn = gr.Button(
                        "Generar Audio",
                        variant="primary",
                        elem_classes="generate-main-btn"
                    )
                    with gr.Row():
                        proj_audio = gr.Audio(label="Audio generado", type="filepath")
                        proj_status = gr.Textbox(label="Estado", interactive=False)

                # === Conectar eventos del Proyecto ===

                # Deteccion de formato al escribir texto
                proj_text.change(
                    on_content_change,
                    inputs=[proj_text],
                    outputs=[
                        proj_format_display,
                        proj_voice_single_panel,
                        proj_podcast_panel,
                        proj_podcast_info,
                    ]
                )

                # Actualizar speaker dropdowns cuando cambia el texto (para podcast)
                proj_text.change(
                    update_podcast_speaker_dropdowns,
                    inputs=[proj_text],
                    outputs=proj_speaker_dropdowns
                )

                # Deteccion de formato al subir archivo
                proj_file.change(
                    on_file_upload,
                    inputs=[proj_file],
                    outputs=[
                        proj_text,
                        proj_format_display,
                        proj_voice_single_panel,
                        proj_podcast_panel,
                        proj_podcast_info,
                    ]
                )

                # Actualizar voces cuando cambia idioma
                proj_language.change(
                    get_voices_for_language,
                    inputs=[proj_language],
                    outputs=[proj_voice]
                )

                # Preview de instruccion
                def proj_update_instruct(preset, emotion, style_val, pace, intensity, custom):
                    if preset != "(personalizado)" and preset in PRESETS:
                        return PRESETS[preset]["instruct"]
                    return build_instruct(emotion, style_val, pace, intensity, custom)

                for ctrl in [proj_preset, proj_emotion, proj_style, proj_pace, proj_intensity, proj_custom_instruct]:
                    ctrl.change(
                        proj_update_instruct,
                        inputs=[proj_preset, proj_emotion, proj_style, proj_pace, proj_intensity, proj_custom_instruct],
                        outputs=[proj_instruct_preview]
                    )

                # Aplicar preset
                def proj_apply_preset(preset):
                    if preset == "(personalizado)":
                        return "neutral", "conversacional", "normal", "normal", ""
                    preset_configs = {
                        "dialogo_casual": ("neutral", "conversacional", "normal", "normal", ""),
                        "entrevista": ("serio", "profesional", "normal", "normal", ""),
                        "historia_emocionante": ("emocionado", "narracion", "normal", "normal", ""),
                        "explicacion_clara": ("neutral", "explicativo", "pausado", "normal", ""),
                        "debate_apasionado": ("enojado", "autoritario", "rapido", "fuerte", ""),
                        "comedia": ("alegre", "conversacional", "normal", "normal", "con timing comico"),
                        "drama": ("dramatico", "narracion", "pausado", "fuerte", ""),
                        "misterio": ("misterioso", "susurro", "lento", "suave", ""),
                        "motivacional": ("emocionado", "autoritario", "normal", "proyectado", ""),
                        "meditacion": ("neutral", "intimo", "lento", "suave", ""),
                        "noticia_urgente": ("serio", "noticia", "rapido", "proyectado", ""),
                        "cuento_infantil": ("alegre", "infantil", "normal", "normal", ""),
                        "confesion": ("triste", "intimo", "lento", "susurrado", ""),
                        "celebracion": ("emocionado", "conversacional", "rapido", "fuerte", ""),
                        "despedida": ("triste", "intimo", "pausado", "suave", ""),
                    }
                    if preset in preset_configs:
                        return preset_configs[preset]
                    return "neutral", "conversacional", "normal", "normal", ""

                proj_preset.change(
                    proj_apply_preset,
                    inputs=[proj_preset],
                    outputs=[proj_emotion, proj_style, proj_pace, proj_intensity, proj_custom_instruct]
                )

                # Boton principal: Generar
                proj_generate_btn.click(
                    process_universal,
                    inputs=[
                        proj_text, proj_file, proj_voice, proj_model, proj_language,
                        proj_preset, proj_emotion, proj_style, proj_pace, proj_intensity,
                        proj_custom_instruct,
                        proj_spk1, proj_spk2, proj_spk3, proj_spk4, proj_spk5, proj_spk6,
                    ],
                    outputs=[proj_audio, proj_status]
                )

            # === TAB 2: Crear Voz ===
            with gr.Tab("Crear Voz", id="create"):
                gr.Markdown("### Crear perfil de voz desde audio de referencia")

                with gr.Row():
                    with gr.Column(scale=1):
                        voice_name = gr.Textbox(
                            label="Nombre de la voz",
                            placeholder="ej: narrador_masculino",
                            info="Nombre unico para identificar esta voz. Usa solo letras, numeros y guiones bajos."
                        )
                        voice_audio = gr.Audio(
                            label="Audio de referencia (5-30s ideal)",
                            type="filepath"
                        )
                        voice_language = gr.Dropdown(
                            choices=["Spanish", "Portuguese", "English"],
                            value="Spanish",
                            label="Idioma",
                            info="Idioma del audio de referencia. Importante para la transcripcion automatica."
                        )
                        auto_transcribe = gr.Checkbox(
                            label="Transcribir automaticamente (ASR)",
                            value=True,
                            info="Usa Qwen3-ASR para transcribir el audio. Requiere VRAM adicional temporalmente."
                        )
                        manual_transcript = gr.Textbox(
                            label="Transcripcion manual (opcional)",
                            placeholder="Si lo completas, se usara en lugar del ASR",
                            lines=3,
                            info="Si conoces el texto exacto del audio, escribelo aqui para mejor precision."
                        )
                        style_tags = gr.Textbox(
                            label="Tags de estilo (separados por coma)",
                            placeholder="ej: profesional, calmado, masculino"
                        )
                        create_btn = gr.Button("Crear Perfil de Voz", variant="primary")

                    with gr.Column(scale=1):
                        create_status = gr.Textbox(label="Estado", interactive=False)
                        create_result = gr.Code(label="Perfil creado", language="json")

                create_btn.click(
                    create_voice_profile,
                    inputs=[voice_name, voice_audio, voice_language, auto_transcribe, manual_transcript, style_tags],
                    outputs=[create_status, create_result]
                )

            # === TAB 3: Director Studio ===
            with gr.Tab("Director Studio", id="director"):
                gr.Markdown("### Director Studio - Control Total de Entonacion")

                gr.Markdown(
                    """
                    **Control granular de cada mensaje:**
                    1. Sube el script y analiza
                    2. Asigna voces a los speakers
                    3. Selecciona emocion/estilo para cada mensaje
                    4. Genera segmentos individuales o todos a la vez
                    5. Escucha y ajusta hasta que suene natural
                    6. Une todos los audios en el archivo final
                    """,
                    elem_classes="info-box"
                )

                # Estado global para Director
                director_segments = gr.State([])
                director_voice_map = gr.State({})
                director_generated_audios = gr.State({})

                with gr.Row():
                    # Columna izquierda: configuracion
                    with gr.Column(scale=1):
                        director_script = gr.File(
                            label="Script del podcast (.txt)",
                            file_types=[".txt"]
                        )
                        director_analyze_btn = gr.Button("1. Analizar Script", variant="secondary")
                        director_info = gr.Textbox(label="Info", interactive=False, lines=2)

                        director_language = gr.Dropdown(
                            choices=["Spanish", "Portuguese", "English", "Chinese", "Japanese", "Korean"],
                            value="Spanish",
                            label="Idioma"
                        )

                        director_model = gr.Radio(
                            choices=["0.6B", "1.7B"],
                            value="1.7B",
                            label="Modelo base"
                        )

                        # Voces por speaker
                        gr.Markdown("**2. Asignar voces:**")
                        dir_speaker1 = gr.Dropdown(choices=get_all_voices(), label="Speaker 1", visible=False)
                        dir_speaker2 = gr.Dropdown(choices=get_all_voices(), label="Speaker 2", visible=False)
                        dir_speaker3 = gr.Dropdown(choices=get_all_voices(), label="Speaker 3", visible=False)
                        dir_speaker4 = gr.Dropdown(choices=get_all_voices(), label="Speaker 4", visible=False)
                        dir_voice_dropdowns = [dir_speaker1, dir_speaker2, dir_speaker3, dir_speaker4]

                        director_save_voices_btn = gr.Button("Guardar asignacion de voces", variant="secondary")

                    # Columna derecha: resultado final
                    with gr.Column(scale=1):
                        gr.Markdown("**Audio Final:**")
                        director_final_audio = gr.Audio(label="Podcast completo", type="filepath")
                        director_join_btn = gr.Button("6. Unir todos los audios", variant="primary")
                        director_status = gr.Textbox(label="Estado", interactive=False)

                # Seccion de edicion de segmentos
                gr.Markdown("---")
                gr.Markdown("### 3. Editar Segmentos")

                # Selector de segmento actual
                with gr.Row():
                    segment_selector = gr.Slider(
                        minimum=0, maximum=0, step=1, value=0,
                        label="Segmento #", interactive=True
                    )
                    segment_total = gr.Textbox(label="Total", value="0", interactive=False, scale=0)

                # Info del segmento actual
                with gr.Row():
                    with gr.Column(scale=2):
                        segment_speaker = gr.Textbox(label="Speaker", interactive=False)
                        segment_text = gr.Textbox(label="Texto", lines=3, interactive=False)

                    with gr.Column(scale=1):
                        segment_audio_preview = gr.Audio(label="Preview", type="filepath")

                # Controles de entonacion
                gr.Markdown("**4. Ajustar Entonacion:**")

                with gr.Row():
                    preset_selector = gr.Dropdown(
                        choices=PRESET_CHOICES,
                        value="(personalizado)",
                        label="Preset rapido",
                        scale=1
                    )

                with gr.Row():
                    emotion_selector = gr.Dropdown(
                        choices=EMOTION_CHOICES,
                        value="neutral",
                        label="Emocion"
                    )
                    style_selector = gr.Dropdown(
                        choices=STYLE_CHOICES,
                        value="conversacional",
                        label="Estilo"
                    )
                    pace_selector = gr.Dropdown(
                        choices=PACE_CHOICES,
                        value="normal",
                        label="Ritmo"
                    )
                    intensity_selector = gr.Dropdown(
                        choices=INTENSITY_CHOICES,
                        value="normal",
                        label="Intensidad"
                    )

                custom_instruct = gr.Textbox(
                    label="Instruccion personalizada (opcional)",
                    placeholder="ej: como si estuviera contando un secreto emocionante"
                )

                instruct_preview = gr.Textbox(
                    label="Instruccion resultante",
                    interactive=False
                )

                with gr.Row():
                    generate_segment_btn = gr.Button("5. Generar este segmento", variant="primary")
                    generate_all_btn = gr.Button("Generar TODOS los segmentos", variant="secondary")

                # Tabla de progreso
                gr.Markdown("**Progreso de segmentos:**")
                segments_table = gr.Dataframe(
                    headers=["#", "Speaker", "Texto (preview)", "Estado", "Emocion"],
                    label="Segmentos",
                    interactive=False
                )

                # === Funciones del Director ===

                def analyze_director_script(script_file):
                    """Analiza script y prepara segmentos"""
                    if not script_file:
                        return (
                            "Sube un script primero",
                            [], {},
                            gr.update(visible=False), gr.update(visible=False),
                            gr.update(visible=False), gr.update(visible=False),
                            gr.update(maximum=0, value=0), "0",
                            [], "", ""
                        )

                    studio = get_studio()

                    with open(script_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    parsed = studio.podcast.parse_script(content)
                    speakers = sorted(set(seg.speaker for seg in parsed))

                    # Convertir a lista serializable
                    segments_data = [
                        {
                            "index": i,
                            "speaker": seg.speaker,
                            "text": seg.text,
                            "timestamp": seg.timestamp,
                            "emotion": "neutral",
                            "style": "conversacional",
                            "pace": "normal",
                            "intensity": "normal",
                            "custom": "",
                            "generated": False
                        }
                        for i, seg in enumerate(parsed)
                    ]

                    info = f"Detectados {len(segments_data)} segmentos, {len(speakers)} speakers: {', '.join(speakers)}"

                    # Actualizar dropdowns de voces
                    all_voices = get_all_voices()
                    voice_updates = []
                    for i in range(4):
                        if i < len(speakers):
                            voice_updates.append(gr.update(
                                visible=True,
                                label=f"{speakers[i]}:",
                                choices=all_voices,
                                value=all_voices[0] if all_voices else None
                            ))
                        else:
                            voice_updates.append(gr.update(visible=False))

                    # Slider y tabla
                    max_seg = max(0, len(segments_data) - 1)
                    table_data = [
                        [s["index"], s["speaker"], s["text"][:40] + "...", "Pendiente", s["emotion"]]
                        for s in segments_data
                    ]

                    # Info del primer segmento
                    first_speaker = segments_data[0]["speaker"] if segments_data else ""
                    first_text = segments_data[0]["text"] if segments_data else ""

                    return (
                        info,
                        segments_data,
                        {},  # voice_map vacio
                        *voice_updates,
                        gr.update(maximum=max_seg, value=0),
                        str(len(segments_data)),
                        table_data,
                        first_speaker,
                        first_text
                    )

                def save_voice_assignment(segments, s1, s2, s3, s4):
                    """Guarda asignacion de voces"""
                    if not segments:
                        return {}, "No hay segmentos cargados"

                    speakers = sorted(set(s["speaker"] for s in segments))
                    voices = [s1, s2, s3, s4]

                    voice_map = {}
                    for i, speaker in enumerate(speakers):
                        if i < len(voices) and voices[i]:
                            voice = voices[i]
                            if voice.startswith("[Clonada] "):
                                voice_map[speaker] = {"type": "clone", "name": voice.replace("[Clonada] ", "")}
                            elif voice.startswith("[Qwen] "):
                                voice_map[speaker] = {"type": "qwen", "name": voice.replace("[Qwen] ", "")}
                            else:
                                voice_map[speaker] = {"type": "qwen", "name": voice}

                    return voice_map, f"Voces asignadas: {len(voice_map)} speakers"

                def update_segment_view(segments, seg_index):
                    """Actualiza vista del segmento seleccionado"""
                    if not segments or seg_index >= len(segments):
                        return "", "", "neutral", "conversacional", "normal", "normal", "", None

                    seg = segments[int(seg_index)]
                    return (
                        seg["speaker"],
                        seg["text"],
                        seg.get("emotion", "neutral"),
                        seg.get("style", "conversacional"),
                        seg.get("pace", "normal"),
                        seg.get("intensity", "normal"),
                        seg.get("custom", ""),
                        None  # Audio preview
                    )

                def update_instruct_preview(preset, emotion, style, pace, intensity, custom):
                    """Muestra preview de la instruccion"""
                    if preset != "(personalizado)" and preset in PRESETS:
                        return PRESETS[preset]["instruct"]
                    return build_instruct(emotion, style, pace, intensity, custom)

                def apply_preset(preset):
                    """Aplica un preset"""
                    if preset == "(personalizado)":
                        return "neutral", "conversacional", "normal", "normal", ""

                    # Presets tienen configuraciones predefinidas
                    preset_configs = {
                        "dialogo_casual": ("neutral", "conversacional", "normal", "normal", ""),
                        "entrevista": ("serio", "profesional", "normal", "normal", ""),
                        "historia_emocionante": ("emocionado", "narracion", "normal", "normal", ""),
                        "explicacion_clara": ("neutral", "explicativo", "pausado", "normal", ""),
                        "debate_apasionado": ("enojado", "autoritario", "rapido", "fuerte", ""),
                        "comedia": ("alegre", "conversacional", "normal", "normal", "con timing comico"),
                        "drama": ("dramatico", "narracion", "pausado", "fuerte", ""),
                        "misterio": ("misterioso", "susurro", "lento", "suave", ""),
                        "motivacional": ("emocionado", "autoritario", "normal", "proyectado", ""),
                        "meditacion": ("neutral", "intimo", "lento", "suave", ""),
                        "noticia_urgente": ("serio", "noticia", "rapido", "proyectado", ""),
                        "cuento_infantil": ("alegre", "infantil", "normal", "normal", ""),
                        "confesion": ("triste", "intimo", "lento", "susurrado", ""),
                        "celebracion": ("emocionado", "conversacional", "rapido", "fuerte", ""),
                        "despedida": ("triste", "intimo", "pausado", "suave", ""),
                    }

                    if preset in preset_configs:
                        return preset_configs[preset]
                    return "neutral", "conversacional", "normal", "normal", ""

                def generate_single_segment(
                    segments, voice_map, generated_audios, seg_index,
                    preset, emotion, style, pace, intensity, custom,
                    language, model_version
                ):
                    """Genera audio para un segmento"""
                    if not segments or not voice_map:
                        return segments, generated_audios, None, "Error: Configura voces primero", []

                    seg_index = int(seg_index)
                    if seg_index >= len(segments):
                        return segments, generated_audios, None, "Segmento invalido", []

                    seg = segments[seg_index]
                    speaker = seg["speaker"]

                    if speaker not in voice_map:
                        return segments, generated_audios, None, f"Error: Sin voz para {speaker}", []

                    studio = get_studio()
                    voice_info = voice_map[speaker]

                    # Construir instruccion
                    if preset != "(personalizado)" and preset in PRESETS:
                        instruct = PRESETS[preset]["instruct"]
                    else:
                        instruct = build_instruct(emotion, style, pace, intensity, custom)

                    try:
                        # Configurar segun tipo de voz
                        ref_audio = None
                        ref_text = None
                        qwen_speaker = None

                        if voice_info["type"] == "clone":
                            voice_profile = studio.voice_library.get_voice(voice_info["name"])
                            if voice_profile:
                                ref_audio = voice_profile["audio_path"]
                                ref_text = voice_profile["transcript"]
                        else:
                            qwen_speaker = voice_info["name"]

                        # Generar
                        studio.tts.load_model(model_version)
                        audio, sr = studio.tts.generate(
                            text=seg["text"],
                            ref_audio_path=ref_audio,
                            ref_text=ref_text,
                            speaker=qwen_speaker,
                            instruct=instruct,
                            language=language
                        )

                        # Guardar audio
                        output_dir = BASE_PATH / "output" / "director_segments"
                        output_dir.mkdir(parents=True, exist_ok=True)
                        output_path = str(output_dir / f"segment_{seg_index:03d}.wav")
                        sf.write(output_path, audio, sr, format='WAV', subtype='PCM_16')

                        # Actualizar estado
                        segments[seg_index]["emotion"] = emotion
                        segments[seg_index]["style"] = style
                        segments[seg_index]["pace"] = pace
                        segments[seg_index]["intensity"] = intensity
                        segments[seg_index]["custom"] = custom
                        segments[seg_index]["generated"] = True

                        generated_audios[seg_index] = output_path

                        # Actualizar tabla
                        table_data = [
                            [
                                s["index"],
                                s["speaker"],
                                s["text"][:40] + "...",
                                "Listo" if s["generated"] else "Pendiente",
                                s["emotion"]
                            ]
                            for s in segments
                        ]

                        return (
                            segments,
                            generated_audios,
                            output_path,
                            f"Segmento {seg_index} generado",
                            table_data
                        )

                    except Exception as e:
                        return segments, generated_audios, None, f"Error: {str(e)}", []

                def generate_all_segments(
                    segments, voice_map, generated_audios,
                    language, model_version, progress=gr.Progress()
                ):
                    """Genera todos los segmentos pendientes"""
                    if not segments or not voice_map:
                        return segments, generated_audios, "Error: Configura voces primero", []

                    studio = get_studio()
                    studio.tts.load_model(model_version)

                    output_dir = BASE_PATH / "output" / "director_segments"
                    output_dir.mkdir(parents=True, exist_ok=True)

                    total = len(segments)

                    for i, seg in enumerate(segments):
                        progress(i / total, f"Generando {i+1}/{total}...")

                        if seg["generated"]:
                            continue  # Ya generado

                        speaker = seg["speaker"]
                        if speaker not in voice_map:
                            continue

                        voice_info = voice_map[speaker]

                        # Construir instruccion
                        instruct = build_instruct(
                            seg.get("emotion", "neutral"),
                            seg.get("style", "conversacional"),
                            seg.get("pace", "normal"),
                            seg.get("intensity", "normal"),
                            seg.get("custom", "")
                        )

                        try:
                            ref_audio = None
                            ref_text = None
                            qwen_speaker = None

                            if voice_info["type"] == "clone":
                                voice_profile = studio.voice_library.get_voice(voice_info["name"])
                                if voice_profile:
                                    ref_audio = voice_profile["audio_path"]
                                    ref_text = voice_profile["transcript"]
                            else:
                                qwen_speaker = voice_info["name"]

                            audio, sr = studio.tts.generate(
                                text=seg["text"],
                                ref_audio_path=ref_audio,
                                ref_text=ref_text,
                                speaker=qwen_speaker,
                                instruct=instruct,
                                language=language
                            )

                            output_path = str(output_dir / f"segment_{i:03d}.wav")
                            sf.write(output_path, audio, sr, format='WAV', subtype='PCM_16')

                            segments[i]["generated"] = True
                            generated_audios[i] = output_path

                        except Exception as e:
                            print(f"Error en segmento {i}: {e}")

                    progress(1.0, "Completado")

                    # Actualizar tabla
                    table_data = [
                        [
                            s["index"],
                            s["speaker"],
                            s["text"][:40] + "...",
                            "Listo" if s["generated"] else "Pendiente",
                            s["emotion"]
                        ]
                        for s in segments
                    ]

                    generated_count = sum(1 for s in segments if s["generated"])
                    return (
                        segments,
                        generated_audios,
                        f"Generados {generated_count}/{total} segmentos",
                        table_data
                    )

                def join_all_audios(segments, generated_audios):
                    """Une todos los audios generados"""
                    if not generated_audios:
                        return None, "No hay audios generados"

                    # Ordenar por indice
                    sorted_indices = sorted(generated_audios.keys())

                    all_audio = []
                    sample_rate = 24000

                    for idx in sorted_indices:
                        audio_path = generated_audios[idx]
                        if os.path.exists(audio_path):
                            audio, sr = sf.read(audio_path)
                            sample_rate = sr
                            all_audio.append(audio)
                            # Pausa entre segmentos
                            pause = np.zeros(int(sr * 0.3))
                            all_audio.append(pause)

                    if not all_audio:
                        return None, "No se encontraron audios"

                    final_audio = np.concatenate(all_audio)

                    output_path = str(BASE_PATH / "output" / "director_final.wav")
                    sf.write(output_path, final_audio, sample_rate, format='WAV', subtype='PCM_16')

                    return output_path, f"Podcast unido: {len(sorted_indices)} segmentos, {len(final_audio)/sample_rate:.1f}s"

                # === Conectar eventos ===

                director_analyze_btn.click(
                    analyze_director_script,
                    inputs=[director_script],
                    outputs=[
                        director_info,
                        director_segments,
                        director_voice_map,
                        dir_speaker1, dir_speaker2, dir_speaker3, dir_speaker4,
                        segment_selector,
                        segment_total,
                        segments_table,
                        segment_speaker,
                        segment_text
                    ]
                )

                director_save_voices_btn.click(
                    save_voice_assignment,
                    inputs=[director_segments, dir_speaker1, dir_speaker2, dir_speaker3, dir_speaker4],
                    outputs=[director_voice_map, director_status]
                )

                segment_selector.change(
                    update_segment_view,
                    inputs=[director_segments, segment_selector],
                    outputs=[
                        segment_speaker, segment_text,
                        emotion_selector, style_selector, pace_selector, intensity_selector,
                        custom_instruct, segment_audio_preview
                    ]
                )

                # Actualizar preview de instruccion
                for control in [preset_selector, emotion_selector, style_selector, pace_selector, intensity_selector, custom_instruct]:
                    control.change(
                        update_instruct_preview,
                        inputs=[preset_selector, emotion_selector, style_selector, pace_selector, intensity_selector, custom_instruct],
                        outputs=[instruct_preview]
                    )

                preset_selector.change(
                    apply_preset,
                    inputs=[preset_selector],
                    outputs=[emotion_selector, style_selector, pace_selector, intensity_selector, custom_instruct]
                )

                generate_segment_btn.click(
                    generate_single_segment,
                    inputs=[
                        director_segments, director_voice_map, director_generated_audios,
                        segment_selector, preset_selector, emotion_selector, style_selector,
                        pace_selector, intensity_selector, custom_instruct,
                        director_language, director_model
                    ],
                    outputs=[
                        director_segments, director_generated_audios,
                        segment_audio_preview, director_status, segments_table
                    ]
                )

                generate_all_btn.click(
                    generate_all_segments,
                    inputs=[
                        director_segments, director_voice_map, director_generated_audios,
                        director_language, director_model
                    ],
                    outputs=[director_segments, director_generated_audios, director_status, segments_table]
                )

                director_join_btn.click(
                    join_all_audios,
                    inputs=[director_segments, director_generated_audios],
                    outputs=[director_final_audio, director_status]
                )

            # === TAB 4: Libreria ===
            with gr.Tab("Libreria de Voces", id="library"):
                gr.Markdown("### Voces disponibles")

                with gr.Row():
                    library_refresh = gr.Button("Actualizar lista")
                    gpu_cleanup_btn = gr.Button("Liberar memoria GPU", variant="stop")

                gpu_status = gr.Textbox(label="Estado GPU", interactive=False, visible=False)

                # Voces Qwen predefinidas
                gr.Markdown("#### Voces Qwen predefinidas")
                qwen_data = [[s, "Multilingue"] for s in ALL_SPEAKERS]
                gr.Dataframe(
                    value=qwen_data,
                    headers=["Speaker", "Idiomas"],
                    label="Speakers del modelo Qwen"
                )

                # Voces clonadas del usuario
                gr.Markdown("#### Voces clonadas (creadas por ti)")
                library_list = gr.Dataframe(
                    headers=["Nombre", "Idioma", "Tags", "Transcripcion"],
                    label="Tus voces clonadas"
                )

                def load_library():
                    studio = get_studio()
                    voices = studio.voice_library.voices
                    data = []
                    for name, profile in voices.items():
                        transcript = profile.get("transcript", "")
                        if len(transcript) > 80:
                            transcript = transcript[:80] + "..."
                        data.append([
                            name,
                            profile.get("language", ""),
                            ", ".join(profile.get("style_tags", [])),
                            transcript
                        ])
                    return data if data else [["(sin voces clonadas)", "", "", ""]]

                library_refresh.click(load_library, outputs=[library_list])

                def cleanup_gpu():
                    msg = unload_models()
                    return gr.update(value=msg, visible=True)

                gpu_cleanup_btn.click(cleanup_gpu, outputs=[gpu_status])

    return app


if __name__ == "__main__":
    app = build_ui()
    app.launch(
        server_name="0.0.0.0",
        server_port=None,
        share=False,
        inbrowser=True,
        theme=gr.themes.Soft(primary_hue="indigo", secondary_hue="slate"),
        css=CUSTOM_CSS
    )
