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
 return CreateSmartShortsContext(ctx,log,video,outDir,clipSeconds,maxWorkers,0,map[bool]string{true:"pan",false:"center"}[enablePan])
}

// CreateSmartShortsContext supports scene-aligned cuts and portrait framing.
func CreateSmartShortsContext(ctx context.Context, log *utils.Logger, video,outDir string, clipSeconds,maxWorkers int, sceneSeconds float64, cropMode string) error {
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

 segments,err:=PlanSmartShorts(float64(totalSec),clipSeconds,sceneSeconds)
 if err!=nil{return err}
 clips:=len(segments)
 cropFilter,err:=SmartCropFilter(cropMode)
 if err!=nil{return err}

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
            segment:=segments[idx]
            out := filepath.Join(stageDir, fmt.Sprintf("short_%03d.mp4", idx))
            filterComplex:=cropFilter

			args := []string{
				"-y",
				"-ss", fmt.Sprintf("%.6f", segment.Start),
				"-i", videoAbs,
				"-t", fmt.Sprintf("%.6f", segment.Duration),

				"-filter_complex", filterComplex,

				// Map filtered video + audio
				"-map", "[v]",
				"-map", "0:a:0?",
                "-map", "0:s?",

				// Encode with optimized settings
				"-c:v", "libx264",
				"-preset", "fast",
				"-pix_fmt", "yuv420p",
				"-c:a", "aac",
				"-b:a", "160k",
                "-c:s", "mov_text",

				// Progress
				"-progress", "pipe:1",
				"-nostats",

				out,
			}

			if err := utils.RunFFmpegWithRetryContext(ctx,log,int(segment.Duration)+1,args...); err != nil {
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
