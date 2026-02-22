package stages

import (
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

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

	if secondsPerImage <= 0 {
		secondsPerImage = 3.5
	}
	if fps <= 0 {
		fps = 30
	}

	absImagesDir, err := filepath.Abs(imagesDir)
	if err != nil {
		return err
	}

	// Collect processed jpgs
	imgs, _ := filepath.Glob(filepath.Join(absImagesDir, "*.jpg"))
	if len(imgs) == 0 {
		return fmt.Errorf("no images found in %s", absImagesDir)
	}
	sort.Strings(imgs)

	// Build concat list file
	workDir := "./output/work"
	_ = os.MkdirAll(workDir, os.ModePerm)
	listPath := filepath.Join(workDir, "list.txt")

	f, err := os.Create(listPath)
	if err != nil {
		return err
	}
	defer f.Close()

	for _, img := range imgs {
		abs, _ := filepath.Abs(img)
		abs = strings.ReplaceAll(abs, "'", "'\\''")
		fmt.Fprintf(f, "file '%s'\n", abs)
		fmt.Fprintf(f, "duration %.3f\n", secondsPerImage)
	}
	// Last file repeated (concat requirement)
	lastAbs, _ := filepath.Abs(imgs[len(imgs)-1])
	lastAbs = strings.ReplaceAll(lastAbs, "'", "'\\''")
	fmt.Fprintf(f, "file '%s'\n", lastAbs)

	audioAbs, _ := filepath.Abs(audio)
	outputAbs, _ := filepath.Abs(output)

	totalSec, err := utils.ProbeDurationSeconds(audioAbs)
	if err != nil {
		log.Warn("ffprobe audio duration failed; progress may be inaccurate: " + err.Error())
		totalSec = 0
	}

	args := []string{
		"-y",

		// Loop the slideshow forever; audio decides final length
		"-stream_loop", "-1",

		"-f", "concat",
		"-safe", "0",
		"-i", listPath,

		"-i", audioAbs,

		// Force output to contain video + audio
		"-map", "0:v:0",
		"-map", "1:a:0",

		// End with audio duration
		"-shortest",

		"-c:v", "libx264",
		"-pix_fmt", "yuv420p",
		"-r", fmt.Sprintf("%d", fps),

		"-c:a", "aac",
		"-b:a", "192k",

		"-progress", "pipe:1",
		"-nostats",

		outputAbs,
	}

	log.Info("Concat list: " + listPath)
	return utils.RunFFmpegWithProgress(log, totalSec, args...)
}
