package stages

import (
	"context"
 "fmt"
 "os"
 "errors"
	"path/filepath"
	"sync"
	"time"

	"syncshotgo/internal/utils"

	"github.com/schollz/progressbar/v3"
)

func CreateShortsVertical(log *utils.Logger, video string, outDir string, clipSeconds int, maxWorkers int) error {
	return CreateShortsVerticalWithPan(log, video, outDir, clipSeconds, maxWorkers, false)
}

// CreateShortsVerticalWithPan creates vertical shorts with optional smart panning effect
func CreateShortsVerticalWithPan(log *utils.Logger, video string, outDir string, clipSeconds int, maxWorkers int, enablePan bool) error {
	return CreateShortsVerticalWithPanContext(context.Background(),log,video,outDir,clipSeconds,maxWorkers,enablePan)
}

func CreateShortsVerticalWithPanContext(ctx context.Context, log *utils.Logger, video string, outDir string, clipSeconds int, maxWorkers int, enablePan bool) error {
 if err:=ctx.Err(); err!=nil { return err }
 if clipSeconds <= 0 {
		clipSeconds = 57
	}
	if maxWorkers <= 0 {
		maxWorkers = 2
	}

	videoAbs, err := filepath.Abs(video)
	if err != nil {
		return err
	}
	if err := recoverPublishedPath(outDir); err != nil { return err }
 parent := filepath.Dir(outDir)
 if err := utils.EnsureDirs(parent); err != nil { return err }
 stageDir, err := os.MkdirTemp(parent, ".shorts-staging-*")
 if err != nil { return fmt.Errorf("create Shorts staging directory: %w", err) }
 defer os.RemoveAll(stageDir)

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

	// Progress bar for shorts creation
	bar := progressbar.NewOptions64(
		int64(clips),
		progressbar.OptionSetDescription("Creating shorts"),
		progressbar.OptionShowIts(),
		progressbar.OptionSetWidth(15),
		progressbar.OptionThrottle(100*time.Millisecond),
	)
	var progressMutex sync.Mutex

	// Parallel shorts using worker pool
	sem := make(chan struct{}, maxWorkers)
	var wg sync.WaitGroup
 errCh := make(chan error, clips)

	for i := 0; i < clips; i++ {
        select { case sem <- struct{}{}: case <-ctx.Done(): wg.Wait(); return ctx.Err() }
        wg.Add(1)
		go func(idx int) {
			defer wg.Done()
			defer func() { <-sem }()

			if ctx.Err()!=nil { return }
            start := idx * clipSeconds
			out := filepath.Join(stageDir, fmt.Sprintf("short_%03d.mp4", idx))

			// Smart crop: intelligently crop landscape to vertical format
			// Scale to fill the entire 1080x1920 frame (with zoom)
			// Then crop to center (can be adjusted for different framing)
			var filterComplex string

			if enablePan {
				// With panning: subtle zoom effect that moves across the frame
				zoomEnd := 1.1
				filterComplex = fmt.Sprintf(
					"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920:(in_w-1080)/2:(in_h-1920)/2,zoompan=z='min(zoom+0.0005,%.1f)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)',fps=24[v]",
					zoomEnd,
				)
			} else {
				// Static crop: no panning, just intelligent crop
				filterComplex = "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920:(in_w-1080)/2:(in_h-1920)/2[v]"
			}

			args := []string{
				"-y",
				"-ss", fmt.Sprintf("%d", start),
				"-i", videoAbs,
				"-t", fmt.Sprintf("%d", clipSeconds),

				"-filter_complex", filterComplex,

				// Map filtered video + audio
				"-map", "[v]",
				"-map", "0:a:0?",

				// Encode with optimized settings
				"-c:v", "libx264",
				"-preset", "fast",
				"-pix_fmt", "yuv420p",
				"-c:a", "aac",
				"-b:a", "160k",

				// Progress
				"-progress", "pipe:1",
				"-nostats",

				out,
			}

			if err := utils.RunFFmpegWithRetryContext(ctx,log,clipSeconds,args...); err != nil {
				errCh <- fmt.Errorf("short %d failed: %w", idx, err)
				return
			}

			// Update progress bar
			progressMutex.Lock()
			bar.Add(1)
			progressMutex.Unlock()
		}(i)
	}

	wg.Wait()
 if ctx.Err()!=nil { return ctx.Err() }
 close(errCh)
 var failures []error
 for err := range errCh { failures = append(failures, err) }
 if len(failures) != 0 { return errors.Join(failures...) }
 for i := 0; i < clips; i++ {
  path := filepath.Join(stageDir,fmt.Sprintf("short_%03d.mp4",i))
  info, err := os.Stat(path)
  if err != nil { return fmt.Errorf("missing Short %d: %w", i, err) }
  if info.Size() == 0 { return fmt.Errorf("Short %d is empty",i) }
  if err := validateRenderedMedia(path); err != nil { return fmt.Errorf("Short %d invalid: %w",i,err) }
 }
 if err := publishShortsDirectory(stageDir,outDir); err != nil { return err }
 return nil
}
