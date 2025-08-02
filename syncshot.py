import os
import random
import subprocess
import numpy as np
from tqdm import tqdm
from PIL import Image
from moviepy import (
    ImageClip, VideoFileClip, concatenate_videoclips,
    AudioFileClip, CompositeVideoClip
)
from faster_whisper import WhisperModel

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

def transcribe_audio_to_ass(audio_path, ass_output_path="subtitles.ass", model_size="base"):
    """Transcribe audio to .ass subtitles using Faster-Whisper."""
    print("🚀 Loading Faster-Whisper model...")
    model = WhisperModel(model_size, compute_type="auto")  # Use GPU if available

    print(f"🎙️ Transcribing: {audio_path}")
    segments, _ = model.transcribe(audio_path, beam_size=5)

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

def burn_subtitles(video_path, ass_path, output_path_with_subs):
    """Burn .ass subtitles into video using ffmpeg with large center-aligned styling."""
    try:
        print("🔥 Burning subtitles into the video...")
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-vf", f"ass={ass_path}",
            "-c:a", "copy",
            output_path_with_subs
        ]
        subprocess.run(cmd, check=True)
        print(f"🎉 Subtitle-burned video saved to: {output_path_with_subs}")
    except Exception as e:
        print(f"💥 Failed to burn subtitles: {str(e)}")

def generate_video(audio_path, image_paths, output_path='output_video.mp4'):
    """Generate a video from an audio file and a set of images, then burn subtitles into it."""
    try:
        # Transcribe audio to subtitles
        ass_output = os.path.splitext(output_path)[0] + ".ass"
        transcribe_audio_to_ass(audio_path, ass_output)

        # Load audio
        audio = AudioFileClip(audio_path)
        audio_duration = audio.duration

        # Calculate duration per image
        num_images = len(image_paths)
        if num_images == 0:
            raise ValueError("No images provided.")
        image_duration = audio_duration / num_images

        clips = []
        for img_path in tqdm(image_paths, desc="🖼️ Processing Images"):
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

        # Write video without subtitles
        print("📽️ Writing raw video without subtitles...")
        video.write_videofile(
            output_path,
            codec='libx264',
            audio_codec='aac',
            fps=24,
            preset='medium',
            ffmpeg_params=['-crf', '23']
        )

        # Burn subtitles
        output_with_subs = os.path.splitext(output_path)[0] + "_subtitled.mp4"
        burn_subtitles(output_path, ass_output, output_with_subs)

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

def create_shorts(video_path, shorts_dir="shorts"):
    """Create vertical short clips (YouTube Shorts format) from the main video."""
    try:
        if not os.path.exists(shorts_dir):
            os.makedirs(shorts_dir)

        print("✂️ Creating Shorts...")
        clip = VideoFileClip(video_path)

        # Resize for vertical format (9:16 aspect ratio, typically 1080x1920)
        vertical_clip = clip.resized(height=1920, width=1080)

        # Define short segments in seconds (must be < 60 seconds for YouTube Shorts)
        shorts = [
            ("short1.mp4", 10, 25),
            ("short2.mp4", 30, 45),
            ("short3.mp4", 50, 65)
        ]

        for filename, start, end in shorts:
            short = vertical_clip.subclipped(start, end)
            short_path = os.path.join(shorts_dir, filename)
            print(f"🎬 Exporting {filename} ({start}s to {end}s)...")
            short.write_videofile(short_path, codec="libx264", audio_codec="aac", fps=30)

        print("✅ All shorts created successfully.")

    except Exception as e:
        print(f"💥 Failed to create shorts: {e}")

if __name__ == "__main__":
    audio_folder = "audio"
    audio_files = [
        os.path.join(audio_folder, fname)
        for fname in sorted(os.listdir(audio_folder))
        if fname.lower().endswith(".m4a")
    ]
    if not audio_files:
        raise FileNotFoundError("No .m4a files found in the audio folder.")
    audio_file = audio_files[0]

    image_folder = "images"
    image_files = [
        os.path.join(image_folder, fname)
        for fname in os.listdir(image_folder)
        if fname.lower().endswith((".jpg", ".jpeg", ".png"))
    ]

    if not image_files:
        raise FileNotFoundError("No image files found in the image folder.")

    random.shuffle(image_files)

    output_video = "output_video.mp4"
    generate_video(audio_file, image_files, output_video)
    print("🎥 Video generation complete. Now burning subtitles...")
    subtitled_video = "output_video_subtitled.mp4"
    create_shorts(subtitled_video)
