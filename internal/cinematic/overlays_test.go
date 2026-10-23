package cinematic

import (
 "context"
 "image"
 "image/color"
 "image/png"
 "os"
 "os/exec"
 "path/filepath"
 "testing"

 "syncshotgo/internal/utils"
)

func TestRenderCinematicWithBothOverlays(t *testing.T) {
 if testing.Short(){t.Skip("FFmpeg integration")}
 if _,err:=exec.LookPath("ffmpeg");err!=nil {t.Skip("ffmpeg not available")}
 dir:=t.TempDir()
 src:=filepath.Join(dir,"scene.png")
 audio:=filepath.Join(dir,"audio.wav")
 out:=filepath.Join(dir,"cinematic.mp4")
 if output,err:=exec.Command("ffmpeg","-hide_banner","-loglevel","error","-y","-f","lavfi","-i","color=c=blue:s=320x180","-frames:v","1",src).CombinedOutput();err!=nil {t.Fatalf("create still: %v %s",err,output)}
 if output,err:=exec.Command("ffmpeg","-hide_banner","-loglevel","error","-y","-f","lavfi","-i","sine=frequency=440:duration=2","-c:a","pcm_s16le",audio).CombinedOutput();err!=nil {t.Fatalf("create audio: %v %s",err,output)}
 makeOverlay:=func(name string)string {
  path:=filepath.Join(dir,name)
  f,err:=os.Create(path);if err!=nil {t.Fatal(err)}
  pic:=image.NewRGBA(image.Rect(0,0,20,20))
  for y:=0;y<20;y++ {for x:=0;x<20;x++ {pic.Set(x,y,color.RGBA{R:255,A:255})}}
  if err:=png.Encode(f,pic);err!=nil {_=f.Close();t.Fatal(err)}
  if err:=f.Close();err!=nil {t.Fatal(err)}
  return path
 }
 timeline,err:=FromImages([]string{src},2,12,320,180,0,Static)
 if err!=nil {t.Fatal(err)}
 overlays:=Overlays{SubscribePath:makeOverlay("subscribe.png"),NotificationPath:makeOverlay("bell.png"),SubscribeOpacity:0.8,NotificationOpacity:0.5}
 if err:=RenderWithOverlays(context.Background(),utils.NewLogger(),timeline,audio,out,overlays,os.Rename);err!=nil {t.Fatal(err)}
 d,err:=utils.ProbeDurationPrecise(context.Background(),out)
 if err!=nil || d<1.7 || d>2.3 {t.Fatalf("output duration %.3f: %v",d,err)}
}
