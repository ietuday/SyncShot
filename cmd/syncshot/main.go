package main

import (
	"fmt"
	"os"

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
		FPS:             30,
		SecondsPerImage: 3.5,
		ClipSeconds:     50,
		MaxWorkers:      6,
	}

	log.Info("Starting SyncShot-Go")

	err := pipeline.Run(log, cfg)
	if err != nil {
		log.Error(fmt.Sprintf("Pipeline failed: %v", err))
		os.Exit(1)
	}

	log.Info("Video and Shorts created successfully")
}
