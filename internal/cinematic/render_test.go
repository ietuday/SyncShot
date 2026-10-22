package cinematic

import (
 "context"
 "os"
 "os/exec"
 "path/filepath"
 "testing"

 "syncshotgo/internal/utils"
)

func TestCinematicFFmpegSmoke(t *testing.T) {
 if testing.Short() {t.Skip("integration")}
 if _,err:=exec.LookPath("ffmpeg");err!=nil {t.Skip("FFmpeg missing")}
 dir:=t.TempDir()
 images:=[]string{filepath.Join(dir,"a.png"),filepath.Join(dir,"b.png")}
 for i,color:=range []string{"red","blue"} {
  if out,err:=exec.Command("ffmpeg","-hide_banner","-loglevel","error","-y","-f","lavfi","-i","color=c="+color+":s=320x180","-frames:v","1",images[i]).CombinedOutput();err!=nil {t.Fatalf("image ffmpeg: %v %s",err,out)}
 }
 audio:=filepath.Join(dir,"audio.wav")
 if out,err:=exec.Command("ffmpeg","-hide_banner","-loglevel","error","-y","-f","lavfi","-i","sine=frequency=440:duration=3","-c:a","pcm_s16le",audio).CombinedOutput();err!=nil {t.Fatalf("audio ffmpeg: %v %s",err,out)}
 timeline,err:=FromImages(images,3,12,320,180,0.4,ZoomIn)
 if err!=nil {t.Fatal(err)}
 target:=filepath.Join(dir,"cinematic.mp4")
 if err:=Render(context.Background(),utils.NewLogger(),timeline,audio,target,os.Rename);err!=nil {t.Fatal(err)}
 info,err:=os.Stat(target)
 if err!=nil || info.Size()==0 {t.Fatalf("cinematic output missing: %v",err)}
 duration,err:=utils.ProbeDurationSeconds(target)
 if err!=nil || duration<2 || duration>4 {t.Fatalf("output duration=%d err=%v",duration,err)}
}
