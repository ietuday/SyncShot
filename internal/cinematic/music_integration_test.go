package cinematic

import (
 "context"
 "encoding/json"
 "os"
 "os/exec"
 "path/filepath"
 "testing"
 "syncshotgo/internal/utils"
)

func TestMusicDuckingFFmpeg(t *testing.T) {
 if testing.Short(){t.Skip("FFmpeg integration")}
 for _,bin:=range []string{"ffmpeg","ffprobe"} {if _,err:=exec.LookPath(bin);err!=nil {t.Skip(bin+" missing")}}
 dir:=t.TempDir()
 run:=func(args ...string){t.Helper();if out,err:=exec.Command("ffmpeg",args...).CombinedOutput();err!=nil {t.Fatalf("ffmpeg %v: %v %s",args,err,out)}}
 still:=filepath.Join(dir,"still.png")
 narr:=filepath.Join(dir,"voice.wav")
 music:=filepath.Join(dir,"music.wav")
 run("-hide_banner","-loglevel","error","-y","-f","lavfi","-i","color=c=blue:s=320x180","-frames:v","1",still)
 run("-hide_banner","-loglevel","error","-y","-f","lavfi","-i","sine=frequency=440:duration=2","-c:a","pcm_s16le",narr)
 run("-hide_banner","-loglevel","error","-y","-f","lavfi","-i","sine=frequency=220:duration=0.6","-c:a","pcm_s16le",music)
 timeline,err:=FromImages([]string{still},2,12,320,180,0,Static);if err!=nil {t.Fatal(err)}
 for _,duck:=range []bool{false,true} {
  name:="mix";if duck{name="duck"}
  target:=filepath.Join(dir,name+".mp4")
  opts:=Overlays{MusicPath:music,MusicVolume:.18,MusicFadeSeconds:.2,MusicDucking:duck}
  if err:=RenderWithOverlays(context.Background(),utils.NewLogger(),timeline,narr,target,opts,os.Rename);err!=nil {t.Fatalf("duck=%t: %v",duck,err)}
  out,err:=exec.Command("ffprobe","-v","error","-show_entries","stream=codec_type","-of","json",target).Output()
  if err!=nil {t.Fatal(err)}
  var parsed struct{Streams []struct{CodecType string `json:"codec_type"`} `json:"streams"`}
  if err:=json.Unmarshal(out,&parsed);err!=nil {t.Fatal(err)}
  video,audio:=0,0
  for _,stream:=range parsed.Streams {if stream.CodecType=="video"{video++};if stream.CodecType=="audio"{audio++}}
  if video!=1||audio!=1 {t.Fatalf("duck=%t streams: %s",duck,out)}
 }
}

func TestMusicInvalidConfiguration(t *testing.T) {
 timeline,err:=FromImages([]string{"one.png"},2,12,320,180,0,Static);if err!=nil {t.Fatal(err)}
 dir:=t.TempDir()
 for _,volume:=range []float64{-1,0,1.2} {
  opts:=Overlays{MusicPath:filepath.Join(dir,"missing.mp3"),MusicVolume:volume}
  // Absent file is always rejected before transcoding.
  if err:=RenderWithOverlays(context.Background(),utils.NewLogger(),timeline,"no.wav",filepath.Join(dir,"out.mp4"),opts,os.Rename);err==nil {t.Fatal("expected missing music error")}
 }
}
