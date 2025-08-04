import os
from tqdm import tqdm
from moviepy import ImageClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips

from config import SUBTITLE_DIR
from .image_utils import resize_image
from .subtitle_utils import transcribe_audio_to_ass
from .subtitle_utils import transcribe_audio_to_ass
import subprocess

def burn_subtitles(video_path, ass_path, output_path_with_subs):
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

def generate_video(audio_path, image_paths, output_path, subtitle_dir, model_size="base"):
    try:
        ass_output = os.path.join(subtitle_dir, "output_subtitles.ass")
        transcribe_audio_to_ass(audio_path, ass_output, model_size)

        audio = AudioFileClip(audio_path)
        audio_duration = audio.duration
        image_duration = audio_duration / len(image_paths)

        clips = []
        for img_path in tqdm(image_paths, desc="🖼️ Processing Images"):
            img_array = resize_image(img_path)
            if img_array is not None:
                clip = ImageClip(img_array, duration=image_duration)
                clips.append(clip)

        video = concatenate_videoclips(clips, method="compose")
        video = CompositeVideoClip([video])
        video.audio = audio
        video.write_videofile(output_path, codec='libx264', audio_codec='aac', fps=24, preset='medium')

        output_with_subs = os.path.splitext(output_path)[0] + "_subtitled.mp4"
        burn_subtitles(output_path, ass_output, output_with_subs)
    finally:
        audio.close()
        video.close()
        for clip in clips:
            clip.close()
