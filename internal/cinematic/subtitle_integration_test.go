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

// Test that SRT captions are actually muxed as an MP4 subtitle stream.
func TestCinematicSubtitleTrack(t *testing.T) {
 if testing.Short() { t.Skip("FFmpeg integration test") }
 for _,bin:=range []string{"ffmpeg","ffprobe"} {
  if _,err:=exec.LookPath(bin);err!=nil {t.Skip(bin+" not installed")}
 }
 dir:=t.TempDir()
 img:=filepath.Join(dir,"frame.png")
 if out,err:=exec.Command("ffmpeg","-hide_banner","-loglevel","error","-y","-f","lavfi","-i","color=c=blue:s=320x180","-frames:v","1",img).CombinedOutput();err!=nil {t.Fatalf("image: %s (%v)",out,err)}
 audio:=filepath.Join(dir,"audio.wav")
 if out,err:=exec.Command("ffmpeg","-hide_banner","-loglevel","error","-y","-f","lavfi","-i","sine=frequency=440:duration=2","-c:a","pcm_s16le",audio).CombinedOutput();err!=nil {t.Fatalf("audio: %s (%v)",out,err)}
 srt:=filepath.Join(dir,"captions.srt")
 if err:=os.WriteFile(srt,[]byte("1\n00:00:00,000 --> 00:00:01,900\nHello world\n"),0600);err!=nil {t.Fatal(err)}
 timeline,err:=FromImages([]string{img},2,12,320,180,0,Static)
 if err!=nil {t.Fatal(err)}
 target:=filepath.Join(dir,"out.mp4")
 if err:=RenderWithOverlays(context.Background(),utils.NewLogger(),timeline,audio,target,Overlays{SubtitlePath:srt},os.Rename);err!=nil {t.Fatal(err)}
 out,err:=exec.Command("ffprobe","-v","error","-select_streams","s","-show_entries","stream=codec_name","-of","json",target).Output()
 if err!=nil {t.Fatalf("ffprobe subtitle stream: %v",err)}
 var result struct {Streams []struct{CodecName string `json:"codec_name"`} `json:"streams"`}
 if err:=json.Unmarshal(out,&result);err!=nil {t.Fatal(err)}
 if len(result.Streams)!=1 || result.Streams[0].CodecName!="mov_text" {t.Fatalf("expected mov_text subtitle stream, got: %s",out)}
}
