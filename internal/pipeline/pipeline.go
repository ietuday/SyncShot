package pipeline

import (
	"context"
 "fmt"
	"path/filepath"

	"syncshotgo/internal/stages"
 "syncshotgo/internal/cinematic"
	"syncshotgo/internal/utils"
)

type Config struct {
 CinematicEnabled bool
 CinematicTimelinePath string
 CinematicCrossfade float64
 CinematicMotion cinematic.Motion
	AudioDir        string
	ImagesDir       string
	OutVideoPath    string
	OutShortsDir    string
	WorkDir         string
	FPS             int
	SecondsPerImage float64
	ClipSeconds     int
	MaxWorkers      int
	// Overlay settings
	AddSubscribeButton  bool
	AddNotificationBell bool
	SubscribeOpacity    float32 // 0.0-1.0
	NotificationOpacity float32 // 0.0-1.0
}

func Run(log *utils.Logger, cfg Config) error {
 return RunContext(context.Background(), log, cfg)
}

func RunContext(ctx context.Context, log *utils.Logger, cfg Config) error {
 if err:=ctx.Err(); err!=nil { return err }
 if err := cfg.Validate(); err != nil { return fmt.Errorf("invalid configuration: %w", err) }
 release, err := acquireRunLock(cfg.WorkDir)
 if err != nil { return err }
 defer func() { if unlockErr := release(); unlockErr != nil { log.Warn("Failed to remove run lock: "+unlockErr.Error()) } }()

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
	processed, err := stages.ProcessImagesWorkerPoolContext(
        ctx,
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

	// 4.5) Prepare overlays if enabled
	var subscribePath, notificationPath string
	if cfg.AddSubscribeButton || cfg.AddNotificationBell {
		overlayConfig := stages.OverlayConfig{
			EnableSubscribe:     cfg.AddSubscribeButton,
			EnableNotification:  cfg.AddNotificationBell,
			SubscribeOpacity:    cfg.SubscribeOpacity,
			NotificationOpacity: cfg.NotificationOpacity,
		}
		subscribePath, notificationPath, err = stages.PrepareOverlays(log, overlayConfig, cfg.WorkDir)
		if err != nil {
			return err
		}
	}

	// 5) Render YouTube video using PROCESSED images directory (not original)
	log.Info("Creating YouTube video")
 if cfg.CinematicEnabled {
  if cfg.AddSubscribeButton || cfg.AddNotificationBell { log.Warn("Cinematic mode currently renders without subscribe/bell overlays") }
  var cinematicErr error
  if cfg.CinematicTimelinePath != "" {
   cinematicErr = stages.RenderCinematicTimeline(ctx, log, cfg.CinematicTimelinePath, audio, cfg.OutVideoPath)
  } else {
   cinematicErr = stages.RenderCinematic(ctx, log, workProcessed, audio, cfg.OutVideoPath, cfg.FPS, cfg.CinematicCrossfade, cfg.CinematicMotion)
  }
  if err := cinematicErr; err != nil {
   return fmt.Errorf("cinematic rendering: %w", err)
  }
 } else {
 	if err := stages.RenderYouTubeVideoWithOverlaysContext(
        ctx,
		log,
		workProcessed, // ✅ important: use processed_images folder
		audio,
		cfg.OutVideoPath,
		cfg.SecondsPerImage,
		cfg.FPS,
		subscribePath,
		notificationPath,
		cfg.SubscribeOpacity,
		cfg.NotificationOpacity,
	); err != nil {
		return err
	}

 }

	// 6) Create vertical Shorts only when requested.
 if cfg.ClipSeconds > 0 {
  log.Info("Creating Shorts")
  if err := stages.CreateShortsVerticalWithPanContext(ctx, log, cfg.OutVideoPath, cfg.OutShortsDir, cfg.ClipSeconds, cfg.MaxWorkers, false); err != nil {
   return fmt.Errorf("create shorts: %w", err)
  }
 }
 return nil
}
