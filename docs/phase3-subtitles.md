# Phase 3.2 — subtitles (opt-in)

The cinematic renderer now supports **selectable** subtitles inside MP4 (MPEG-4 timed text / mov_text). Captions are not burned into the image. Default behavior stays unchanged with both settings empty.

Edit `cmd/syncshot/main.go` and add one of:

- Import a manually authored/transcribed subtitle file: `SubtitleMode: "import", SubtitleSRTPath: "./inputs/subtitles/captions.srt",`
- Transcribe speech automatically: `SubtitleMode: "whisper",` (requires the locally installed `whisper` executable, e.g. OpenAI Whisper's CLI, plus its models; the first invocation may download a model). Run the application with Internet access for initial model setup.

`SubtitleMode: ""` with a nonempty `SubtitleSRTPath` also selects import mode.

The project preserves the narration and original images, validates SRT time ranges/numbering, and embeds the captions as a selectable MP4 subtitle track. This requires `CinematicEnabled: true`. The SRT source may contain English, Hindi, or Marathi UTF-8 text; playback depends on the video player and fonts. YouTube can also accept an SRT as a separate caption upload.

**Limits:** Whisper transcription is not guaranteed accurate: manually review names, punctuation, languages, and timestamps. This release does not automatically translate captions or burn styles into the video. With disabled captions, Whisper is not required. No cloud API credentials are needed for the CLI workflow.
