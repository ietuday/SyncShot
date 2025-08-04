import os
from moviepy import VideoFileClip

def create_shorts(video_path, shorts_dir="shorts"):
    if not os.path.exists(shorts_dir):
        os.makedirs(shorts_dir)

    clip = VideoFileClip(video_path)
    vertical_clip = clip.resized(height=1920, width=1080)

    shorts = [("short1.mp4", 10, 25), ("short2.mp4", 30, 45), ("short3.mp4", 50, 65)]
    for filename, start, end in shorts:
        short = vertical_clip.subclipped(start, end)
        short_path = os.path.join(shorts_dir, filename)
        short.write_videofile(short_path, codec="libx264", audio_codec="aac", fps=30)
