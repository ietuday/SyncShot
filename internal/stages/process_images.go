package stages

import (
 "context"
 "fmt"
 "os"
 "path/filepath"
 "sort"
 "strings"
 "sync"
 "syncshotgo/internal/utils"
)

func ProcessImagesWorkerPool(log *utils.Logger, images []string, outDir string, workers int) ([]string, error) {
 return ProcessImagesWorkerPoolContext(context.Background(),log,images,outDir,workers)
}

func ProcessImagesWorkerPoolContext(ctx context.Context, log *utils.Logger, images []string, outDir string, workers int) ([]string, error) {
 images = filterImageFiles(images)
 if len(images) == 0 { return nil, fmt.Errorf("no valid images found") }
 if workers <= 0 { workers = 2 }
 if workers > len(images) { workers = len(images) }
 if err := utils.EnsureDirs(outDir); err != nil { return nil, err }
 sort.Strings(images)
 type job struct { in, out string }
 jobs := make(chan job)
 var wg sync.WaitGroup
 var mu sync.Mutex
 var firstErr error
 worker := func() {
  defer wg.Done()
  for j := range jobs {
   if ctx.Err()!=nil { continue }
   args := []string{"-y", "-i", j.in, "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2", "-frames:v", "1", "-q:v", "2", j.out}
   if err := utils.RunFFmpegWithProgressContext(ctx,log, 0, args...); err != nil {
    mu.Lock()
    if firstErr == nil { firstErr = fmt.Errorf("process %s: %w", j.in, err) }
    mu.Unlock()
    continue // Drain all jobs; producer cannot deadlock.
   }
  }
 }
 for i := 0; i < workers; i++ { wg.Add(1); go worker() }
 out := make([]string, len(images))
 for i, p := range images {
  out[i] = filepath.Join(outDir, fmt.Sprintf("img_%06d.jpg", i))
  select { case jobs <- job{p, out[i]}: case <-ctx.Done(): close(jobs); wg.Wait(); return nil, ctx.Err() }
 }
 close(jobs)
 wg.Wait()
 if ctx.Err()!=nil { return nil, ctx.Err() }
 if firstErr != nil { return nil, firstErr }
 for _, p := range out {
  info, err := os.Stat(p)
  if err != nil { return nil, fmt.Errorf("expected processed image %s: %w", p, err) }
  if info.Size() == 0 { return nil, fmt.Errorf("processed image is empty: %s", p) }
 }
 return out, nil
}

func filterImageFiles(paths []string) []string {
 result := make([]string, 0, len(paths))
 for _, p := range paths {
  switch strings.ToLower(filepath.Ext(p)) {
  case ".jpg", ".jpeg", ".png", ".webp", ".bmp": result = append(result, p)
  }
 }
 return result
}
