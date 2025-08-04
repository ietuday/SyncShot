import time
from faster_whisper import WhisperModel

def transcribe_audio_to_ass(audio_path, ass_output_path, model_size="base"):
    print("🚀 Loading Faster-Whisper model...")
    model = WhisperModel(model_size, compute_type="auto")

    print(f"🎙️ Transcribing: {audio_path}")
    t0 = time.time()
    segments, _ = model.transcribe(audio_path, beam_size=5)
    print(f"🧠 Transcription completed in {time.time() - t0:.2f}s")

    ass_header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, BackColour, OutlineColour, Bold, Italic, Underline, Alignment, MarginL, MarginR, MarginV, BorderStyle, Outline, Shadow, Encoding
Style: Default,Impact,110,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,5,50,50,60,1,5,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    def format_ass_time(seconds):
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        cs = int((seconds - int(seconds)) * 100)
        return f"{h:01}:{m:02}:{s:02}.{cs:02}"

    with open(ass_output_path, "w", encoding="utf-8") as f:
        f.write(ass_header)
        for segment in segments:
            start = format_ass_time(segment.start)
            end = format_ass_time(segment.end)
            text = segment.text.replace('\n', ' ').replace(',', ',\\N')
            f.write(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}\n")

    print(f"✅ ASS subtitle file generated: {ass_output_path}")
