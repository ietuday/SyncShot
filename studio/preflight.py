import json
import subprocess
import sys
from pathlib import Path

AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def media_files(directory, extensions):
    return sorted(path for path in directory.iterdir()
                  if path.is_file() and path.suffix.lower() in extensions)


def main():
    audio_dir, images_dir = map(Path, sys.argv[1:])
    audio = media_files(audio_dir, AUDIO_EXTENSIONS)
    images = media_files(images_dir, IMAGE_EXTENSIONS)
    if len(audio) != 1 or not images:
        raise ValueError("Place exactly one narration and at least one image in the input folders.")
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0",
         "-show_entries", "stream=index:format=duration", "-of", "json", str(audio[0])],
        check=True, capture_output=True, text=True, timeout=15,
    )
    metadata = json.loads(probe.stdout)
    duration = float(metadata.get("format", {}).get("duration", 0))
    if not metadata.get("streams") or not 0 < duration < float("inf"):
        raise ValueError("Narration must contain an audio stream with a finite positive duration.")
    print(json.dumps({"audio": audio[0].name, "durationSeconds": duration, "images": len(images)}))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(error, file=sys.stderr)
        sys.exit(1)
