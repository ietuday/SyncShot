package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"

	"syncshotgo/internal/pipeline"
	"syncshotgo/internal/stages"
	"syncshotgo/internal/subtitles"
)

type plannedScene struct {
	Image     string   `json:"image"`
	Start     float64  `json:"start"`
	End       float64  `json:"end"`
	Narration []string `json:"narration,omitempty"`
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
	if cfg.SubtitleSRTPath != "" {
		data, err := os.ReadFile(cfg.SubtitleSRTPath)
		if err != nil {
			return fmt.Errorf("read narration captions: %w", err)
		}
		cues, err := subtitles.ParseSRT(data)
		if err != nil {
			return fmt.Errorf("parse narration captions: %w", err)
		}
		assignNarration(scenes, cues)
	}
	return json.NewEncoder(output).Encode(scenes)
}

// A cue belongs to the latest scene that has started when the line begins.
// Each line appears once, including when it starts during a crossfade.
func assignNarration(scenes []plannedScene, cues []subtitles.Cue) {
	if len(scenes) == 0 {
		return
	}
	index := 0
	for _, cue := range cues {
		start := float64(cue.StartMillis) / 1000
		for index+1 < len(scenes) && start >= scenes[index+1].Start {
			index++
		}
		if start < scenes[index].End {
			scenes[index].Narration = append(scenes[index].Narration, cue.Text)
		}
	}
}
