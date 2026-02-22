package pipeline

import (
	"fmt"
	"path/filepath"

	"syncshotgo/internal/stages"
	"syncshotgo/internal/utils"
)

type Config struct {
	AudioDir        string
	ImagesDir       string
	OutVideoPath    string
	OutShortsDir    string
	WorkDir         string
	FPS             int
	SecondsPerImage float64
	ClipSeconds     int
	MaxWorkers      int
}

func Run(log *utils.Logger, cfg Config) error {

	workProcessed := filepath.Join(cfg.WorkDir, "processed_images")
	workSubtitles := filepath.Join(cfg.WorkDir, "subtitles")

	// Create required dirs
	if err := utils.EnsureDirs(
		workProcessed,
		workSubtitles,
		cfg.OutShortsDir,
		filepath.Dir(cfg.OutVideoPath),
	); err != nil {
		return err
	}

	// 1) Pick audio
	log.Info("Picking audio")
	audio, err := stages.PickAudio(cfg.AudioDir)
	if err != nil {
		return err
	}

	// 2) Scan images
	log.Info("Scanning images")
	images, err := stages.ScanImages(cfg.ImagesDir)
	if err != nil {
		return err
	}
	if len(images) == 0 {
		return fmt.Errorf("no images found in %s", cfg.ImagesDir)
	}
	log.Info(fmt.Sprintf("Found %d images", len(images)))

	// 3) Process images (resize/letterbox to 1920x1080)
	log.Info("Processing images")
	processed, err := stages.ProcessImagesWorkerPool(
		log,
		images,
		workProcessed,
		cfg.MaxWorkers,
	)
	if err != nil {
		return err
	}
	log.Info(fmt.Sprintf("Processed %d images into %s", len(processed), workProcessed))

	// 4) Subtitles (placeholder)
	srtPath := filepath.Join(workSubtitles, "captions.srt")
	if err := stages.GeneratePlaceholderSRT(srtPath); err != nil {
		return err
	}

	// 5) Render YouTube video using PROCESSED images directory (not original)
	log.Info("Creating YouTube video")
	if err := stages.RenderYouTubeVideo(
		log,
		workProcessed, // ✅ important: use processed_images folder
		audio,
		cfg.OutVideoPath,
		cfg.SecondsPerImage,
		cfg.FPS,
	); err != nil {
		return err
	}

	// 6) Create Shorts (N clips of 57s or configured seconds)
	log.Info("Creating Shorts")
	if err := stages.CreateShortsVertical(
		log,
		cfg.OutVideoPath,
		cfg.OutShortsDir,
		cfg.ClipSeconds,
	); err != nil {
		return err
	}

	return nil
}
