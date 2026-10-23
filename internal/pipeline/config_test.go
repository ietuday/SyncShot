package pipeline

import (
 "os"
 "math"
 "testing"
)

func validConfig(t *testing.T) Config {
 t.Helper()
 audio := t.TempDir()
 images := t.TempDir()
 return Config{AudioDir:audio, ImagesDir:images, OutVideoPath:"video.mp4", OutShortsDir:"shorts", WorkDir:t.TempDir(), FPS:24, SecondsPerImage:3, ClipSeconds:50, MaxWorkers:2, SubscribeOpacity:0.8, NotificationOpacity:0.8}
}
func TestConfigValidation(t *testing.T) {
 cfg:=validConfig(t)
 if err:=cfg.Validate(); err!=nil { t.Fatalf("valid configuration: %v",err) }
 cfg.FPS=0
 if err:=cfg.Validate(); err==nil { t.Fatal("expected FPS validation error") }
 cfg=validConfig(t)
 cfg.SubscribeOpacity=1.5
 if err:=cfg.Validate(); err==nil { t.Fatal("expected opacity validation error") }
 cfg=validConfig(t)
 if err:=os.Remove(cfg.AudioDir); err!=nil { t.Fatal(err) }
 if err:=cfg.Validate(); err==nil { t.Fatal("expected missing audio directory error") }
}

func TestAutoSceneSecondsValidation(t *testing.T) {
 for _, value := range []float64{-1, math.NaN(), math.Inf(1), math.Inf(-1)} {
  cfg:=validConfig(t)
  cfg.CinematicAutoSceneSeconds=value
  if err:=cfg.Validate();err==nil {t.Errorf("accepted invalid scene seconds: %v",value)}
 }
 for _, value := range []float64{0,30,90} {
  cfg:=validConfig(t)
  cfg.CinematicAutoSceneSeconds=value
  if err:=cfg.Validate();err!=nil {t.Errorf("rejected valid scene seconds %v: %v",value,err)}
 }
}

func TestPreviewAndRenderProfiles(t *testing.T) {
 c:=validConfig(t)
 c.CinematicEnabled=true
 c.PreviewSeconds=15
 c.RenderProfile="720p"
 if err:=c.Validate();err!=nil {t.Fatalf("valid preview: %v",err)}
 for _,profile:=range []string{"4k","480p"} {
  bad:=c;bad.RenderProfile=profile
  if err:=bad.Validate();err==nil{t.Errorf("accepted %s",profile)}
 }
 bad:=c;bad.PreviewSeconds=-1
 if err:=bad.Validate();err==nil{t.Fatal("negative preview accepted")}
 bad=c;bad.CinematicTimelinePath="scene.json"
 if err:=bad.Validate();err==nil{t.Fatal("preview of manual timeline accepted")}
 bad=c;bad.CinematicEnabled=false
 if err:=bad.Validate();err==nil{t.Fatal("non-cinematic preview accepted")}
}
