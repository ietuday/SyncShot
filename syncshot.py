import os
from moviepy import ImageClip, concatenate_videoclips, AudioFileClip, CompositeVideoClip
from PIL import Image
import numpy as np

def resize_image(image_path, target_size=(1920, 1080)):
    """Resize image to target size while maintaining aspect ratio and adding black padding."""
    try:
        img = Image.open(image_path)
        img_ratio = img.width / img.height
        target_ratio = target_size[0] / target_size[1]
        
        if img_ratio > target_ratio:
            # Image is wider than target, scale by height
            new_height = target_size[1]
            new_width = int(new_height * img_ratio)
        else:
            # Image is taller than target, scale by width
            new_width = target_size[0]
            new_height = int(new_width / img_ratio)
        
        # Resize image
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Create new blank image with target size and black background
        new_img = Image.new('RGB', target_size, (0, 0, 0))
        
        # Paste resized image in center
        offset = ((target_size[0] - new_width) // 2, (target_size[1] - new_height) // 2)
        new_img.paste(img, offset)
        
        return np.array(new_img)
    except Exception as e:
        print(f"Error processing image {image_path}: {str(e)}")
        return None

def generate_video(audio_path, image_paths, output_path='output_video.mp4'):
    """Generate a video from an audio file and a set of images."""
    try:
        # Load audio
        audio = AudioFileClip(audio_path)
        audio_duration = audio.duration
        
        # Calculate duration for each image
        num_images = len(image_paths)
        if num_images == 0:
            raise ValueError("No images provided.")
        image_duration = audio_duration / num_images
        
        # Process images
        clips = []
        for img_path in image_paths:
            if not os.path.exists(img_path):
                print(f"Image not found: {img_path}")
                continue
            # Resize image to 1920x1080
            img_array = resize_image(img_path)
            if img_array is None:
                continue
            # Create image clip with duration
            clip = ImageClip(img_array, duration=image_duration)
            clips.append(clip)
        
        if not clips:
            raise ValueError("No valid images found.")
        
        # Concatenate image clips
        video = concatenate_videoclips(clips, method="compose")
        
        # Ensure video is a CompositeVideoClip and set audio
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
        
        print(f"Video generated successfully: {output_path}")
        
    except Exception as e:
        print(f"Error generating video: {str(e)}")
        
    finally:
        # Close clips to free memory
        if 'audio' in locals():
            audio.close()
        if 'video' in locals():
            video.close()
        if 'clips' in locals():
            for clip in clips:
                clip.close()

if __name__ == "__main__":
    # Example usage
    audio_file = "audio/audio.mp3"  # Replace with your audio file path
    image_files = [
        "images/1.jpg",
        "images/2.jpg",
        "images/3.jpg",
        "images/4.jpg",
        "images/5.jpg",
        "images/6.jpg",
        "images/7.jpg",
        "images/8.jpg",
        "images/9.jpg",
        "images/10.jpg",
        "images/11.jpg",
        "images/12.jpg",
        "images/13.jpg",
        "images/14.jpg"
    ]
    output_video = "output_video.mp4"
    
    generate_video(audio_file, image_files, output_video)