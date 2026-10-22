package pipeline

import (
 "os"
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
