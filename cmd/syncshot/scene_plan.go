package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"path/filepath"

	"syncshotgo/internal/pipeline"
	"syncshotgo/internal/stages"
)

type plannedScene struct {
	Image string  `json:"image"`
	Start float64 `json:"start"`
	End   float64 `json:"end"`
}

func printScenePlan(ctx context.Context, cfg pipeline.Config, output io.Writer) error {
	if !cfg.CinematicEnabled || cfg.CinematicTimelinePath != "" || cfg.PreviewSeconds != 0 {
		return fmt.Errorf("scene planning requires a full automatic cinematic render")
	}

	images, err := stages.ScanImages(cfg.ImagesDir)
	if err != nil {
		return err
	}
	audio, err := stages.PickAudio(cfg.AudioDir)
	if err != nil {
		return err
	}
	width, height := 1920, 1080
	if cfg.RenderProfile == "720p" {
		width, height = 1280, 720
	}
	timeline, _, err := stages.PlanCinematicTimeline(ctx, images, audio, cfg.FPS,
		cfg.CinematicCrossfade, cfg.CinematicMotion, cfg.CinematicAutoSceneSeconds, width, height)
	if err != nil {
		return err
	}
	scenes := make([]plannedScene, 0, len(timeline.Scenes))
	start := 0.0
	for _, scene := range timeline.Scenes {
		end := start + scene.Duration
		scenes = append(scenes, plannedScene{Image: filepath.Base(scene.Image), Start: start, End: end})
		start = end - timeline.CrossfadeSeconds
	}
	return json.NewEncoder(output).Encode(scenes)
}
