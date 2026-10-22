package stages

import (
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"

	"syncshotgo/internal/utils"

	"github.com/schollz/progressbar/v3"
)

func RenderYouTubeVideo(
	log *utils.Logger,
	imagesDir string,
	audio string,
	output string,
	secondsPerImage float64,
	fps int,
) error {
	return RenderYouTubeVideoWithOverlays(log, imagesDir, audio, output, secondsPerImage, fps, "", "", 1.0, 1.0)
}

// RenderYouTubeVideoWithOverlays renders video with optional overlays
func RenderYouTubeVideoWithOverlays(
	log *utils.Logger,
	imagesDir string,
	audio string,
	output string,
	secondsPerImage float64,
	fps int,
	subscribePath string,
	notificationPath string,
	subscribeOpacity float32,
	notificationOpacity float32,
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

	// Create progress bar for video rendering
	bar := progressbar.NewOptions64(
		int64(totalSec),
		progressbar.OptionSetDescription("Rendering YouTube video"),
		progressbar.OptionShowIts(),
		progressbar.OptionSetWidth(15),
		progressbar.OptionThrottle(500*time.Millisecond),
	)

	// Build FFmpeg command with optional overlays
	args := []string{
		"-y",

		// Loop the slideshow forever; audio decides final length
		"-stream_loop", "-1",

		"-f", "concat",
		"-safe", "0",
		"-i", listPath,

		"-i", audioAbs,
	}

	// Add overlay inputs if provided
	inputCount := 2 // video + audio
	if subscribePath != "" {
		args = append(args, "-i", subscribePath)
		inputCount++
	}
	if notificationPath != "" {
		args = append(args, "-i", notificationPath)
		inputCount++
	}

	// Build filter complex for overlays
	var filterComplex string
	if subscribePath != "" || notificationPath != "" {
		// Start with video input and format
		filterComplex = "[0:v]scale=1920:1080[base]"

		if subscribePath != "" && notificationPath != "" {
			// Both overlays: subscribe + notification
			// Subscribe button (bottom right)
			filterComplex += fmt.Sprintf(";[2]scale=200:60[sub];[base][sub]overlay=x=W-220:y=H-80[tmp]")
			// Notification bell (top right)
			filterComplex += fmt.Sprintf(";[3]scale=80:80[notif];[tmp][notif]overlay=x=W-100:y=20[v]")
		} else if subscribePath != "" {
			// Only subscribe button
			filterComplex += fmt.Sprintf(";[2]scale=200:60[sub];[base][sub]overlay=x=W-220:y=H-80[v]")
		} else {
			// Only notification bell
			filterComplex += fmt.Sprintf(";[2]scale=80:80[notif];[base][notif]overlay=x=W-100:y=20[v]")
		}

		args = append(args, "-filter_complex", filterComplex)
		args = append(args, "-map", "[v]", "-map", "1:a:0")
	} else {
		// Force output to contain video + audio
		args = append(args, "-map", "0:v:0", "-map", "1:a:0")
	}

	// Common encoding settings
	args = append(args,
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
	)

	log.Info("Concat list: " + listPath)
	log.Info(fmt.Sprintf("Target duration: %d seconds", totalSec))

	// Wrap the rendering with progress bar updates
	errCh := make(chan error, 1)
	go func() {
		errCh <- utils.RunFFmpegWithProgress(log, totalSec, args...)
	}()

	// Monitor progress
	ticker := time.NewTicker(500 * time.Millisecond)
	defer ticker.Stop()

	for {
		select {
		case err := <-errCh:
			bar.Finish()
			return err
		case <-ticker.C:
			// Let the progress bar animate
		}
	}
}
