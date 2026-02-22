package stages

import (
	"fmt"
	"path/filepath"
	"sort"
	"strings"
	"sync"

	"syncshotgo/internal/utils"
)

func ProcessImagesWorkerPool(
	log *utils.Logger,
	images []string,
	outDir string,
	workers int,
) ([]string, error) {

	if err := utils.EnsureDirs(outDir); err != nil {
		return nil, err
	}

	// Filter only images (avoid .txt/.gitkeep)
	images = filterImageFiles(images)
	if len(images) == 0 {
		return nil, fmt.Errorf("no valid images found to process")
	}

	if workers <= 0 {
		workers = 4
	}

	type job struct {
		inPath  string
		outPath string
	}
	jobs := make(chan job)
	errCh := make(chan error, 1)

	var wg sync.WaitGroup
	for i := 0; i < workers; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for j := range jobs {
				// Convert to jpg and normalize size (optional but good)
				args := []string{
					"-y",
					"-i", j.inPath,
					"-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
					"-q:v", "2",
					j.outPath,
				}
				if err := utils.RunFFmpegWithProgress(log, 0, args...); err != nil {
					select {
					case errCh <- fmt.Errorf("image convert failed (%s): %w", j.inPath, err):
					default:
					}
					return
				}
			}
		}()
	}

	// Create deterministic names so slideshow order stays stable
	sort.Strings(images)
	out := make([]string, 0, len(images))

	for idx, in := range images {
		outPath := filepath.Join(outDir, fmt.Sprintf("img_%03d.jpg", idx))
		out = append(out, outPath)
		jobs <- job{inPath: in, outPath: outPath}
	}

	close(jobs)
	wg.Wait()

	select {
	case err := <-errCh:
		return nil, err
	default:
	}

	// Validate output exists
	matches, _ := filepath.Glob(filepath.Join(outDir, "*.jpg"))
	if len(matches) == 0 {
		return nil, fmt.Errorf("processed_images folder is empty: %s", outDir)
	}

	return out, nil
}

func filterImageFiles(paths []string) []string {
	ok := make([]string, 0, len(paths))
	for _, p := range paths {
		ext := strings.ToLower(filepath.Ext(p))
		switch ext {
		case ".jpg", ".jpeg", ".png", ".webp", ".bmp":
			ok = append(ok, p)
		}
	}
	return ok
}
