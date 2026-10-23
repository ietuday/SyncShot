package stages

import (
 "context"
 "os"
 "os/exec"
 "path/filepath"
 "testing"

 "syncshotgo/internal/utils"
)
func TestTrimPreviewAudio(t *testing.T) {
 if testing.Short(){t.Skip("FFmpeg integration")}
 if _,err:=exec.LookPath("ffmpeg");err!=nil {t.Skip("FFmpeg not installed")}
 dir:=t.TempDir()
 original:=filepath.Join(dir,"narration.wav")
 if out,err:=exec.Command("ffmpeg","-hide_banner","-loglevel","error","-y","-f","lavfi","-i","sine=frequency=440:duration=5","-c:a","pcm_s16le",original).CombinedOutput();err!=nil{t.Fatalf("make input: %v %s",err,out)}
 target:=filepath.Join(dir,"work","preview.wav")
 if err:=TrimPreviewAudio(context.Background(),original,target,2);err!=nil{t.Fatal(err)}
 d,err:=utils.ProbeDurationPrecise(context.Background(),target)
 if err!=nil||d<1.8||d>2.2{t.Fatalf("duration %v: %v",d,err)}
 if _,err:=os.Stat(original);err!=nil{t.Fatalf("original audio lost: %v",err)}
 if err:=TrimPreviewAudio(context.Background(),original,target,0);err==nil{t.Fatal("accepted zero preview")}
}
