package main

import (
	"context"
 "fmt"
 "os/signal"
 "syscall"
	"os"

	"syncshotgo/internal/pipeline"
	"syncshotgo/internal/utils"
)

func main() {
	log := utils.NewLogger()

	cfg := pipeline.Config{
		AudioDir:            "./inputs/audio",
		ImagesDir:           "./inputs/images",
		OutVideoPath:        "./output/video/final.mp4",
		OutShortsDir:        "./output/shorts",
		WorkDir:             "./output/work",
		FPS:                 24,
		SecondsPerImage:     3.0,
		ClipSeconds:         50,
		MaxWorkers:          8,
		AddSubscribeButton:  true,
		AddNotificationBell: true,
		SubscribeOpacity:    0.8,
		NotificationOpacity: 0.8,
	}

	log.Info("Starting SyncShot-Go")
	// Do not delete successful output files before validating the inputs.
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
 defer stop()
 if err := pipeline.RunContext(ctx, log, cfg); err != nil {
		log.Error(fmt.Sprintf("Pipeline failed: %v", err))
		os.Exit(1)
	}

	log.Info("Pipeline completed successfully")
}
