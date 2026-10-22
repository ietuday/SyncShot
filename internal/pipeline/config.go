package pipeline

import (
 "fmt"
 "math"
 "os"
 "path/filepath"
)

func (c Config) Validate() error {
 for name, val := range map[string]string{"audio directory": c.AudioDir, "images directory":c.ImagesDir, "output video":c.OutVideoPath, "work directory":c.WorkDir} {
  if val == "" { return fmt.Errorf("%s is required", name) }
 }
 if c.FPS <= 0 || c.FPS > 120 { return fmt.Errorf("FPS must be 1..120") }
 if math.IsNaN(c.SecondsPerImage) || math.IsInf(c.SecondsPerImage, 0) || c.SecondsPerImage <= 0 { return fmt.Errorf("seconds per image must be finite and positive") }
 if c.MaxWorkers <= 0 { return fmt.Errorf("max workers must be positive") }
 if c.SubscribeOpacity < 0 || c.SubscribeOpacity > 1 || c.NotificationOpacity < 0 || c.NotificationOpacity > 1 { return fmt.Errorf("overlay opacity must be 0..1") }
 if c.ClipSeconds < 0 { return fmt.Errorf("clip seconds cannot be negative") }
 if c.ClipSeconds > 0 && c.OutShortsDir == "" { return fmt.Errorf("shorts directory is required") }
 for _, p := range []string{c.AudioDir,c.ImagesDir} {
  info, err := os.Stat(p)
  if err != nil { return fmt.Errorf("input directory %s: %w", p, err) }
  if !info.IsDir() { return fmt.Errorf("not a directory: %s", p) }
 }
 if filepath.Clean(c.WorkDir) == filepath.Clean(c.ImagesDir) || filepath.Clean(c.WorkDir) == filepath.Clean(c.AudioDir) { return fmt.Errorf("work directory must differ from input directories") }
 return nil
}
