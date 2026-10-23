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
 if c.CinematicChunkScenes<0 {return fmt.Errorf("cinematic chunk size must not be negative")}
 if c.CinematicChunkScenes>0 {
  if !c.CinematicEnabled||c.CinematicTimelinePath!="" {return fmt.Errorf("chunked rendering requires automatic cinematic mode")}
  if c.CinematicCrossfade!=0 {return fmt.Errorf("chunked rendering currently requires zero crossfade")}
  if c.MusicPath!=""||c.SubtitleMode!=""||c.SubtitleSRTPath!=""||c.AddSubscribeButton||c.AddNotificationBell {return fmt.Errorf("chunked rendering currently does not support music, subtitles or image overlays")}
 }
 if c.MusicPath!="" {
  if !c.CinematicEnabled {return fmt.Errorf("background music requires cinematic mode")}
  if math.IsNaN(c.MusicVolume)||math.IsInf(c.MusicVolume,0)||c.MusicVolume<=0||c.MusicVolume>1 {return fmt.Errorf("music volume must be >0 and <=1")}
  if math.IsNaN(c.MusicFadeSeconds)||math.IsInf(c.MusicFadeSeconds,0)||c.MusicFadeSeconds<0 {return fmt.Errorf("music fade must be finite and nonnegative")}
 } else if c.MusicVolume!=0 || c.MusicFadeSeconds!=0 || c.MusicDucking {return fmt.Errorf("music options require MusicPath")}
 if c.SubtitleMode!="" && c.SubtitleMode!="import" && c.SubtitleMode!="whisper" {return fmt.Errorf("invalid subtitle mode %q",c.SubtitleMode)}
 if c.SubtitleMode=="import" && c.SubtitleSRTPath=="" {return fmt.Errorf("subtitle import requires SubtitleSRTPath")}
 if c.SubtitleMode=="whisper" && c.SubtitleSRTPath!="" {return fmt.Errorf("whisper mode cannot use SubtitleSRTPath")}
 if (c.SubtitleMode!="" || c.SubtitleSRTPath!="") && !c.CinematicEnabled {return fmt.Errorf("subtitles require cinematic rendering")}
 if c.SmartShortsCrop!="" && c.SmartShortsCrop!="center" && c.SmartShortsCrop!="left" && c.SmartShortsCrop!="right" && c.SmartShortsCrop!="pan" {return fmt.Errorf("invalid smart Shorts crop mode %q",c.SmartShortsCrop)}
 if c.PreviewSeconds<0 {return fmt.Errorf("preview seconds must be nonnegative")}
 if c.RenderProfile!="" && c.RenderProfile!="1080p" && c.RenderProfile!="720p" {return fmt.Errorf("render profile must be 720p or 1080p")}
 if c.PreviewSeconds>0 && !c.CinematicEnabled {return fmt.Errorf("preview mode requires cinematic rendering")}
 if (c.RenderProfile=="720p") && (!c.CinematicEnabled || c.CinematicTimelinePath!="") {return fmt.Errorf("720p profile requires automatic cinematic timeline")}
 if c.PreviewSeconds>0 && c.CinematicTimelinePath!="" {return fmt.Errorf("preview mode does not support manual cinematic timelines")}
 if c.FPS <= 0 || c.FPS > 120 { return fmt.Errorf("FPS must be 1..120") }
 if math.IsNaN(c.SecondsPerImage) || math.IsInf(c.SecondsPerImage, 0) || c.SecondsPerImage <= 0 { return fmt.Errorf("seconds per image must be finite and positive") }
 if math.IsNaN(c.CinematicAutoSceneSeconds) || math.IsInf(c.CinematicAutoSceneSeconds, 0) || c.CinematicAutoSceneSeconds < 0 { return fmt.Errorf("cinematic auto scene seconds must be finite and nonnegative") }
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
