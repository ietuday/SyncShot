package main

import (
	"fmt"
	
	"syncshotgo/internal/pipeline"
	"syncshotgo/internal/utils"
)

func main() {

	log := utils.NewLogger()

	cfg := pipeline.Config{
		AudioDir:        "./inputs/audio",
		ImagesDir:       "./inputs/images",
		OutVideoPath:    "./output/video/final.mp4",
		OutShortsDir:    "./output/shorts",
		WorkDir:         "./output/work",
		FPS:             24,
		SecondsPerImage: 3.0,
		ClipSeconds:     50,
		MaxWorkers:      8,
		// Overlay settings - enable/disable as needed
		AddSubscribeButton:  true, // Add YouTube subscribe button
		AddNotificationBell: true, // Add notification bell icon
		SubscribeOpacity:    0.8,  // 80% opacity
		NotificationOpacity: 0.8,  // 80% opacity
	}

	log.Info("Starting SyncShot-Go")

 // Preserve previous outputs until inputs have been validated; no destructive preflight cleanup.

	// run pipeline
	err = pipeline.Run(log, cfg)
	if err != nil {
		log.Error(fmt.Sprintf("Pipeline failed: %v", err))
		return
	}

	log.Info("Pipeline completed successfully")
}
