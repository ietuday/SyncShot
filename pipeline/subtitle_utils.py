import whisper
import os

def transcribe_audio_to_ass(audio_path, ass_output, model_size="base", translate=False):
    """
    Transcribe or translate audio into ASS subtitle format.
    - audio_path: path to input audio file
    - ass_output: path to output .ass subtitle file
    - model_size: whisper model size ("tiny", "base", "small", "medium", "large")
    - translate: if True, output subtitles in English (translate from Hindi)
    """
    model = whisper.load_model(model_size)
    task = "translate" if translate else "transcribe"

    print(f"🎙️ Running Whisper ({model_size}, task={task})...")
    result = model.transcribe(audio_path, task=task)

    # Write ASS subtitle file
    with open(ass_output, "w", encoding="utf-8") as f:
        f.write(_to_ass(result["segments"]))

    print(f"📝 Subtitles saved: {ass_output}")


def _to_ass(segments):
    """
    Convert Whisper segments into ASS subtitle format.
    """
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
    body = ""
    for seg in segments:
        start = _format_timestamp(seg["start"])
        end = _format_timestamp(seg["end"])
        text = seg["text"].replace("\n", " ")
        body += f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}\n"
    return header + body


def _format_timestamp(seconds: float) -> str:
    """Convert seconds to ASS timestamp (h:mm:ss.cs)."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds - int(seconds)) * 100)  # centiseconds
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"
