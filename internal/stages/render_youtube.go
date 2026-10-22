package stages

import (
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"
 "math"

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
	imgs, globErr := filepath.Glob(filepath.Join(absImagesDir, "*.jpg"))
	if globErr != nil { return fmt.Errorf("scan processed images: %w", globErr) }
 if len(imgs) == 0 {
		return fmt.Errorf("no images found in %s", absImagesDir)
	}
	sort.Strings(imgs)

	// Build concat list file
	workDir := filepath.Dir(imagesDir)
	if err := os.MkdirAll(workDir, 0755); err != nil { return err }
	listPath := filepath.Join(workDir, "list.txt")

	f, err := os.Create(listPath)
	if err != nil {
		return err
	}
	defer func() { _ = f.Close() }()

	audioAbs, err := filepath.Abs(audio)
 if err != nil { return err }
 totalSec, err := utils.ProbeDurationSeconds(audioAbs)
 if err != nil { return fmt.Errorf("probe narration: %w", err) }
 if totalSec <= 0 { return fmt.Errorf("invalid narration duration %d", totalSec) }
 secondsPerImage, err = SceneSeconds(float64(totalSec), len(imgs), secondsPerImage)
 if err != nil { return err }
 for _, img := range imgs {
		abs, _ := filepath.Abs(img)
		abs = strings.ReplaceAll(abs, "'", "'\\''")
		if _, err := fmt.Fprintf(f, "file '%s'\n", abs); err != nil { return err }
		if _, err := fmt.Fprintf(f, "duration %.6f\n", secondsPerImage); err != nil { return err }
	}
	// Last file repeated (concat requirement)
	lastAbs, _ := filepath.Abs(imgs[len(imgs)-1])
	lastAbs = strings.ReplaceAll(lastAbs, "'", "'\\''")
	if _, err := fmt.Fprintf(f, "file '%s'\n", lastAbs); err != nil { return err }

	if err := f.Close(); err != nil { return fmt.Errorf("close concat list: %w", err) }
 outputAbs, err := filepath.Abs(output)
 if err != nil { return err }
 if err := os.MkdirAll(filepath.Dir(outputAbs),0755); err != nil { return err }
 tempFile, err := os.CreateTemp(filepath.Dir(outputAbs), ".syncshot-*.mp4")
 if err != nil { return fmt.Errorf("create temporary video: %w", err) }
 tempPath := tempFile.Name()
 if err := tempFile.Close(); err != nil { os.Remove(tempPath); return err }
 defer os.Remove(tempPath)

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
	// overlay inputs follow narration stream
	if subscribePath != "" {
		args = append(args, "-loop", "1", "-i", subscribePath)
	}
	if notificationPath != "" {
		args = append(args, "-loop", "1", "-i", notificationPath)
	}

	// Build filter complex for overlays
	var filterComplex string
	if subscribePath != "" || notificationPath != "" {
		// Start with video input and format
		filterComplex = "[0:v]scale=1920:1080,format=yuv420p[base]"

		if subscribePath != "" && notificationPath != "" {
			// Both overlays: subscribe + notification
			// Subscribe button (bottom right)
			filterComplex += fmt.Sprintf(";[2:v]scale=200:60,format=rgba,colorchannelmixer=aa=%.3f[sub];[base][sub]overlay=x=W-220:y=H-80:shortest=1[tmp]", math.Max(0, math.Min(1, float64(subscribeOpacity))))
			// Notification bell (top right)
			filterComplex += fmt.Sprintf(";[3:v]scale=80:80,format=rgba,colorchannelmixer=aa=%.3f[notif];[tmp][notif]overlay=x=W-100:y=20:shortest=1[v]", math.Max(0, math.Min(1, float64(notificationOpacity))))
		} else if subscribePath != "" {
			// Only subscribe button
			filterComplex += fmt.Sprintf(";[2:v]scale=200:60,format=rgba,colorchannelmixer=aa=%.3f[sub];[base][sub]overlay=x=W-220:y=H-80:shortest=1[v]", math.Max(0, math.Min(1, float64(subscribeOpacity))))
		} else {
			// Only notification bell
			filterComplex += fmt.Sprintf(";[2:v]scale=80:80,format=rgba,colorchannelmixer=aa=%.3f[notif];[base][notif]overlay=x=W-100:y=20:shortest=1[v]", math.Max(0, math.Min(1, float64(notificationOpacity))))
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

		tempPath,
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
            if err != nil { return fmt.Errorf("render video: %w", err) }
            if err := validateRenderedMedia(tempPath); err != nil { return err }
            if err := promoteVideo(tempPath, outputAbs); err != nil { return err }
            return nil
		case <-ticker.C:
			// Let the progress bar animate
		}
	}
}
