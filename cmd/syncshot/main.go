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
		FPS:             24,
		SecondsPerImage: 3.0,
		ClipSeconds:     50,
		MaxWorkers:      8,
	}

	log.Info("Starting SyncShot-Go")

	// ✅ NEW: clear previous outputs
	log.Info("Cleaning previous output files")

	err := utils.CleanOutput(
		cfg.WorkDir,
		cfg.OutShortsDir,
		cfg.OutVideoPath,
	)

	if err != nil {
		log.Error("Failed to clean output: " + err.Error())
		os.Exit(1)
	}

	log.Info("Cleanup complete")

	// run pipeline
	err = pipeline.Run(log, cfg)
	if err != nil {
		log.Error(fmt.Sprintf("Pipeline failed: %v", err))
		os.Exit(1)
	}

	log.Info("Video and Shorts created successfully")
}
