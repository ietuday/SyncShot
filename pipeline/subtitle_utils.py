import logging
import os
from functools import lru_cache
import whisper

logger = logging.getLogger(__name__)

@lru_cache(maxsize=4)
def _get_model(model_size: str):
    logger.info("Loading Whisper model size=%s", model_size)
    return whisper.load_model(model_size)

def transcribe_audio_to_ass(
    audio_path: str,
    ass_output: str,
    model_size: str = "base",
    translate: bool = False,
    language: str | None = None,
    max_line_chars: int | None = None,
):
    """
    Transcribe or translate audio into ASS subtitle format.

    Args:
        audio_path: path to input audio file
        ass_output: path to output .ass subtitle file
        model_size: whisper model size ("tiny", "base", "small", "medium", "large")
        translate: if True, output subtitles in English
        language: optionally force language (e.g., "hi", "en")
        max_line_chars: optionally wrap long lines (very simple wrap)
    """
    if not os.path.isfile(audio_path):
        logger.error("Audio file not found: %s", audio_path)
        raise FileNotFoundError(audio_path)

    os.makedirs(os.path.dirname(ass_output) or ".", exist_ok=True)

    task = "translate" if translate else "transcribe"
    logger.info("Whisper start model=%s task=%s audio=%s", model_size, task, audio_path)

    try:
        model = _get_model(model_size)

        # You can pass language to reduce mis-detection if you know it
        kwargs = {"task": task}
        if language:
            kwargs["language"] = language

        result = model.transcribe(audio_path, **kwargs)

        segments = result.get("segments", [])
        logger.info("Whisper done segments=%d detected_lang=%s",
                    len(segments), result.get("language"))

        ass_text = _to_ass(segments, max_line_chars=max_line_chars)

        with open(ass_output, "w", encoding="utf-8") as f:
            f.write(ass_text)

        logger.info("ASS subtitles saved: %s", ass_output)

    except Exception:
        logger.exception("transcribe_audio_to_ass failed audio=%s output=%s", audio_path, ass_output)
        raise


def _to_ass(segments, max_line_chars: int | None = None) -> str:
    header = """[Script Info]
ScriptType: v4.00+
Collisions: Normal
PlayResX: 1920
PlayResY: 1080
Timer: 100.0000

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,48,&H00FFFFFF,&H00000000,0,0,0,0,100,100,0,0,1,3,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    for seg in segments:
        start = _format_timestamp(float(seg["start"]))
        end = _format_timestamp(float(seg["end"]))

        text = (seg.get("text") or "").replace("\n", " ").strip()
        text = _ass_escape(text)

        if max_line_chars and len(text) > max_line_chars:
            text = _wrap_simple(text, max_line_chars)

        lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")

    return header + "\n".join(lines) + ("\n" if lines else "")


def _ass_escape(text: str) -> str:
    """
    Escape ASS special chars:
    - { } are used for override tags
    - backslash can start control sequences
    """
    text = text.replace("\\", r"\\")
    text = text.replace("{", r"\{").replace("}", r"\}")
    return text


def _wrap_simple(text: str, max_len: int) -> str:
    """
    Very simple word-wrap by inserting '\\N' (ASS newline).
    """
    words = text.split()
    out, cur = [], ""
    for w in words:
        if not cur:
            cur = w
        elif len(cur) + 1 + len(w) <= max_len:
            cur += " " + w
        else:
            out.append(cur)
            cur = w
    if cur:
        out.append(cur)
    return r"\N".join(out)


def _format_timestamp(seconds: float) -> str:
    """
    Convert seconds to ASS timestamp: h:mm:ss.cs
    Use rounding to centiseconds to avoid floating errors.
    """
    if seconds < 0:
        seconds = 0.0

    total_cs = int(round(seconds * 100.0))  # centiseconds (rounded)
    h = total_cs // (3600 * 100)
    total_cs %= (3600 * 100)
    m = total_cs // (60 * 100)
    total_cs %= (60 * 100)
    s = total_cs // 100
    cs = total_cs % 100
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"
