package stages

import (
	"fmt"
	"image"
	"image/color"
	"image/draw"
	"image/png"
	"os"
	"path/filepath"

	"syncshotgo/internal/utils"
)

type OverlayConfig struct {
	EnableSubscribe     bool
	EnableNotification  bool
	SubscribeOpacity    float32 // 0.0-1.0
	NotificationOpacity float32 // 0.0-1.0
}

// GenerateSubscribeButton creates a YouTube-style subscribe button overlay
func GenerateSubscribeButton(outputPath string) error {
	width, height := 200, 60
	img := image.NewRGBA(image.Rect(0, 0, width, height))

	// Red background (YouTube red)
	red := color.RGBA{R: 255, G: 0, B: 0, A: 255}
	for x := 0; x < width; x++ {
		for y := 0; y < height; y++ {
			img.Set(x, y, red)
		}
	}

	// Rounded corners (simple version - corner pixels transparent)
	transparent := color.RGBA{R: 0, G: 0, B: 0, A: 0}
	corner := 10
	for x := 0; x < corner; x++ {
		for y := 0; y < corner; y++ {
			draw.DrawMask(img, image.Rect(x, y, x+1, y+1),
				image.NewUniform(transparent), image.Point{},
				nil, image.Point{}, draw.Src)
		}
	}

	f, err := os.Create(outputPath)
	if err != nil {
		return err
	}
	defer f.Close()

	return png.Encode(f, img)
}

// GenerateNotificationBell creates a notification bell icon overlay
func GenerateNotificationBell(outputPath string) error {
	width, height := 80, 80
	img := image.NewRGBA(image.Rect(0, 0, width, height))

	// Transparent background
	transparent := color.RGBA{R: 0, G: 0, B: 0, A: 0}
	for x := 0; x < width; x++ {
		for y := 0; y < height; y++ {
			img.Set(x, y, transparent)
		}
	}

	// White bell icon
	white := color.RGBA{R: 255, G: 255, B: 255, A: 255}

	// Bell shape (simplified)
	cx, cy := width/2, height/2

	// Bell body (circle)
	for x := 0; x < width; x++ {
		for y := 0; y < height; y++ {
			px, py := float64(x-cx), float64(y-cy)
			dist := px*px + py*py
			if dist < 400 && dist > 200 { // Ring shape
				img.Set(x, y, white)
			}
		}
	}

	// Red notification dot (top right)
	redDot := color.RGBA{R: 255, G: 0, B: 0, A: 255}
	dotSize := 15
	for x := width - dotSize; x < width; x++ {
		for y := 0; y < dotSize; y++ {
			img.Set(x, y, redDot)
		}
	}

	f, err := os.Create(outputPath)
	if err != nil {
		return err
	}
	defer f.Close()

	return png.Encode(f, img)
}

// PrepareOverlays generates all required overlay graphics
func PrepareOverlays(
	log *utils.Logger,
	cfg OverlayConfig,
	workDir string,
) (string, string, error) {

	overlayDir := filepath.Join(workDir, "overlays")
	if err := utils.EnsureDirs(overlayDir); err != nil {
		return "", "", err
	}

	subscribePath := filepath.Join(overlayDir, "subscribe.png")
	notificationPath := filepath.Join(overlayDir, "notification.png")

	if cfg.EnableSubscribe {
		log.Info("Generating subscribe button overlay")
		if err := GenerateSubscribeButton(subscribePath); err != nil {
			return "", "", fmt.Errorf("failed to generate subscribe button: %w", err)
		}
	}

	if cfg.EnableNotification {
		log.Info("Generating notification bell overlay")
		if err := GenerateNotificationBell(notificationPath); err != nil {
			return "", "", fmt.Errorf("failed to generate notification bell: %w", err)
		}
	}

	return subscribePath, notificationPath, nil
}
