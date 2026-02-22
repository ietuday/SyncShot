package stages

import (
	"fmt"
	"path/filepath"

	"syncshotgo/internal/utils"
)

func RenderYouTubeVideo(
	log *utils.Logger,
	imagesDir string,
	audio string,
	output string,
	secondsPerImage float64,
	fps int,
) error {

	// 1) Build ABSOLUTE glob pattern: /abs/path/to/processed_images/*.jpg
	absImagesDir, err := filepath.Abs(imagesDir)
	if err != nil {
		return err
	}
	imagePattern := filepath.Join(absImagesDir, "*.jpg")

	// 2) Absolute paths for audio/output (handles spaces + unicode)
	audioAbs, err := filepath.Abs(audio)
	if err != nil {
		return err
	}
	outputAbs, err := filepath.Abs(output)
	if err != nil {
		return err
	}

	// 3) Full duration = audio duration (for progress %)
	totalSec, err := utils.ProbeDurationSeconds(audioAbs)
	if err != nil {
		log.Warn("ffprobe audio duration failed; progress may be inaccurate: " + err.Error())
		totalSec = 0
	}

	// 4) Keep each image on screen for secondsPerImage
	// ffmpeg expects rational, e.g. 1/3.500 means "1 image every 3.5 seconds"
	if secondsPerImage <= 0 {
		secondsPerImage = 3.5
	}
	imageRate := fmt.Sprintf("1/%.3f", secondsPerImage)

	args := []string{
		"-y",

		// Loop images forever
		"-stream_loop", "-1",

		// Image input (glob)
		"-framerate", imageRate,
		"-pattern_type", "glob",
		"-i", imagePattern,

		// Audio input
		"-i", audioAbs,

		// End when audio ends (=> full 18+ min video)
		"-shortest",

		// Encode
		"-c:v", "libx264",
		"-pix_fmt", "yuv420p",
		"-r", fmt.Sprintf("%d", max(1, fps)),
		"-c:a", "aac",
		"-b:a", "192k",
		"-vf", "scale=1920:1080",

		// Progress
		"-progress", "pipe:1",
		"-nostats",

		outputAbs,
	}

	log.Info("Rendering YouTube video from imagesDir: " + absImagesDir)
	log.Info("Image glob: " + imagePattern)

	return utils.RunFFmpegWithProgress(log, totalSec, args...)
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}
