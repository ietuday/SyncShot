import os
import uuid
from tqdm import tqdm
from moviepy import ImageClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips
import subprocess

from .image_utils import resize_image
from .subtitle_utils import transcribe_audio_to_ass


def burn_subtitles(video_path, ass_path, output_path_with_subs, strict=True):
    print("🔥 Burning subtitles into the video...")
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vf", f"ass={ass_path}",
        "-c:a", "copy",
        output_path_with_subs
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0 or not os.path.exists(output_path_with_subs):
        msg = f"💥 FFmpeg failed:\n{result.stderr}"
        if strict:
            raise RuntimeError(msg)
        else:
            print(msg)
    else:
        print(f"🎉 Subtitle-burned video saved: {output_path_with_subs}")


def generate_video(audio_path, image_paths, output_path, subtitle_dir,
                   model_size="base", fps=24, preset="medium",
                   translate_subs=True):
    """
    Generate a video with audio + image slideshow, add translated subtitles.
    """
    audio, video, clips = None, None, []
    try:
        # unique subtitle file
        ass_output = os.path.join(subtitle_dir, f"subs_{uuid.uuid4().hex}.ass")

        # 🔑 Hindi → English subtitles
        transcribe_audio_to_ass(audio_path, ass_output, model_size, translate=translate_subs)

        # prepare audio & images
        audio = AudioFileClip(audio_path)
        image_duration = audio.duration / len(image_paths)

        for img_path in tqdm(image_paths, desc="🖼️ Processing Images"):
            img_array = resize_image(img_path)
            if img_array is not None:
                clips.append(ImageClip(img_array, duration=image_duration))

        if not clips:
            raise ValueError("No valid images to create video.")

        video = concatenate_videoclips(clips, method="compose")
        video = CompositeVideoClip([video])
        video.audio = audio
        video.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=fps, preset=preset)

        output_with_subs = os.path.splitext(output_path)[0] + "_subtitled.mp4"
        burn_subtitles(output_path, ass_output, output_with_subs)

        return output_with_subs

    finally:
        if audio: audio.close()
        if video: video.close()
        for clip in clips:
            clip.close()
