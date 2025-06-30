import os
from moviepy import ImageClip, concatenate_videoclips, AudioFileClip, CompositeVideoClip
from PIL import Image
import numpy as np
from faster_whisper import WhisperModel
from tqdm import tqdm

def resize_image(image_path, target_size=(1920, 1080)):
    """Resize image to target size while maintaining aspect ratio and adding black padding."""
    try:
        img = Image.open(image_path)
        img_ratio = img.width / img.height
        target_ratio = target_size[0] / target_size[1]

        if img_ratio > target_ratio:
            new_height = target_size[1]
            new_width = int(new_height * img_ratio)
        else:
            new_width = target_size[0]
            new_height = int(new_width / img_ratio)

        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        new_img = Image.new('RGB', target_size, (0, 0, 0))
        offset = ((target_size[0] - new_width) // 2, (target_size[1] - new_height) // 2)
        new_img.paste(img, offset)

        return np.array(new_img)
    except Exception as e:
        print(f"❌ Error processing image {image_path}: {str(e)}")
        return None

def format_time(seconds):
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hrs:02}:{mins:02}:{secs:02},{millis:03}"

def transcribe_audio_to_srt(audio_path, srt_output_path="subtitles.srt", model_size="base"):
    """Transcribe audio to .srt subtitles using Faster-Whisper."""
    print("🚀 Loading Faster-Whisper model...")
    model = WhisperModel(model_size, compute_type="auto")  # auto = GPU if available

    print(f"🎙️ Transcribing: {audio_path}")
    segments, info = model.transcribe(audio_path, beam_size=5)

    with open(srt_output_path, "w", encoding="utf-8") as f:
        for i, segment in enumerate(tqdm(segments, desc="📝 Generating Subtitles"), start=1):
            start = segment.start
            end = segment.end
            text = segment.text.strip()
            f.write(f"{i}\n")
            f.write(f"{format_time(start)} --> {format_time(end)}\n")
            f.write(f"{text}\n\n")

    print(f"✅ SRT generated: {srt_output_path}")

def generate_video(audio_path, image_paths, output_path='output_video.mp4'):
    """Generate a video from an audio file and a set of images."""
    try:
        # Transcribe audio to subtitles before generating video
        srt_output = os.path.splitext(output_path)[0] + ".srt"
        transcribe_audio_to_srt(audio_path, srt_output)

        # Load audio
        audio = AudioFileClip(audio_path)
        audio_duration = audio.duration

        # Calculate duration per image
        num_images = len(image_paths)
        if num_images == 0:
            raise ValueError("No images provided.")
        image_duration = audio_duration / num_images

        clips = []
        for img_path in image_paths:
            if not os.path.exists(img_path):
                print(f"⚠️ Image not found: {img_path}")
                continue
            img_array = resize_image(img_path)
            if img_array is None:
                continue
            clip = ImageClip(img_array, duration=image_duration)
            clips.append(clip)

        if not clips:
            raise ValueError("No valid images found.")

        # Concatenate image clips
        video = concatenate_videoclips(clips, method="compose")
        if not isinstance(video, CompositeVideoClip):
            video = CompositeVideoClip([video])
        video.audio = audio

        # Write output video
        video.write_videofile(
            output_path,
            codec='libx264',
            audio_codec='aac',
            fps=24,
            preset='medium',
            ffmpeg_params=['-crf', '23']
        )

        print(f"🎥 Video generated: {output_path}")

    except Exception as e:
        print(f"💥 Error: {str(e)}")

    finally:
        if 'audio' in locals():
            audio.close()
        if 'video' in locals():
            video.close()
        if 'clips' in locals():
            for clip in clips:
                clip.close()

if __name__ == "__main__":
    audio_file = "audio/audio.wav"  # Your audio file path
    image_folder = "images"
    image_files = [
        os.path.join(image_folder, fname)
        for fname in sorted(os.listdir(image_folder))
        if fname.lower().endswith((".jpg", ".png"))
    ]
    output_video = "output_video.mp4"
    generate_video(audio_file, image_files, output_video)
