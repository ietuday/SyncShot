package cinematic

import (
 "context"
 "os"
 "os/exec"
 "path/filepath"
 "testing"

 "syncshotgo/internal/utils"
)

func TestVisualChunkHasNoAudio(t *testing.T){
 if testing.Short(){t.Skip("FFmpeg integration")}
 for _,binary:=range []string{"ffmpeg","ffprobe"} {if _,err:=exec.LookPath(binary);err!=nil{t.Skip(binary+" unavailable")}}
 dir:=t.TempDir()
 image:=filepath.Join(dir,"image.png")
 if b,err:=exec.Command("ffmpeg","-hide_banner","-loglevel","error","-y","-f","lavfi","-i","color=c=red:s=320x180","-frames:v","1",image).CombinedOutput();err!=nil{t.Fatalf("create input: %v %s",err,b)}
 timeline:=Timeline{FPS:12,Width:320,Height:180,CrossfadeSeconds:0.2,Scenes:[]Scene{{Image:image,Duration:1.2},{Image:image,Duration:1}}}
 out:=filepath.Join(dir,"visual.mp4")
 if err:=renderVisualChunk(context.Background(),utils.NewLogger(),timeline,out);err!=nil{t.Fatal(err)}
 probe,err:=exec.Command("ffprobe","-v","error","-show_entries","stream=codec_type","-of","csv=p=0",out).Output()
 if err!=nil{t.Fatal(err)}
 if string(probe)!="video\n"{t.Fatalf("expected video-only intermediate; streams=%q",probe)}
 d,err:=utils.ProbeDurationPrecise(context.Background(),out)
 if err!=nil||d<1.8||d>2.2{t.Fatalf("invalid visual duration %.3f: %v",d,err)}
 if _,err:=os.Stat(out);err!=nil{t.Fatal(err)}
}

func TestVisualChunkFailureDoesNotCreateOutput(t *testing.T){
 if testing.Short(){t.Skip("FFmpeg integration")}
 if _,err:=exec.LookPath("ffmpeg");err!=nil{t.Skip("FFmpeg unavailable")}
 dir:=t.TempDir()
 out:=filepath.Join(dir,"missing.mp4")
 timeline:=Timeline{FPS:12,Width:320,Height:180,Scenes:[]Scene{{Image:filepath.Join(dir,"missing.png"),Duration:1}}}
 if err:=renderVisualChunk(context.Background(),utils.NewLogger(),timeline,out);err==nil{t.Fatal("expected missing image error")}
 if _,err:=os.Stat(out);!os.IsNotExist(err){t.Fatalf("unexpected published chunk: %v",err)}
}
