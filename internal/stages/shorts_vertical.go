package stages

import (
	"fmt"
	"path/filepath"
	"sync"

	"syncshotgo/internal/utils"
)

func CreateShortsVertical(log *utils.Logger, video string, outDir string, clipSeconds int) error {
	if clipSeconds <= 0 {
		clipSeconds = 57
	}

	videoAbs, err := filepath.Abs(video)
	if err != nil {
		return err
	}
	if err := utils.EnsureDirs(outDir); err != nil {
		return err
	}

	totalSec, err := utils.ProbeDurationSeconds(videoAbs)
	if err != nil {
		return err
	}

	clips := totalSec / clipSeconds
	if totalSec%clipSeconds != 0 {
		clips++
	}
	if clips < 1 {
		clips = 1
	}

	// Limit parallel shorts (CPU heavy)
	limit := 2
	sem := make(chan struct{}, limit)
	var wg sync.WaitGroup

	for i := 0; i < clips; i++ {
		wg.Add(1)
		sem <- struct{}{}
		go func(idx int) {
			defer wg.Done()
			defer func() { <-sem }()

			start := idx * clipSeconds
			out := filepath.Join(outDir, fmt.Sprintf("short_%03d.mp4", idx))

			// ✅ Use filter_complex (not -vf)
			// Background: scale/crop to fill 1080x1920 + blur
			// Foreground: scale to fit inside 1080x1920
			// Overlay centered
			filterComplex := "" +
				"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:1[bg];" +
				"[0:v]scale=1080:1920:force_original_aspect_ratio=decrease[fg];" +
				"[bg][fg]overlay=(W-w)/2:(H-h)/2[v]"

			args := []string{
				"-y",
				"-ss", fmt.Sprintf("%d", start),
				"-i", videoAbs,
				"-t", fmt.Sprintf("%d", clipSeconds),

				"-filter_complex", filterComplex,

				// ✅ map filtered video + audio
				"-map", "[v]",
				"-map", "0:a:0?",

				// encode
				"-c:v", "libx264",
				"-pix_fmt", "yuv420p",
				"-c:a", "aac",
				"-b:a", "160k",

				// progress
				"-progress", "pipe:1",
				"-nostats",

				out,
			}

			log.Info(fmt.Sprintf("Creating short %d/%d (with progress)...", idx+1, clips))
			if err := utils.RunFFmpegWithProgress(log, clipSeconds, args...); err != nil {
				log.Error(fmt.Sprintf("short %d failed: %v", idx, err))
				return
			}
			log.Info("short -> " + out)
		}(i)
	}

	wg.Wait()
	return nil
}
