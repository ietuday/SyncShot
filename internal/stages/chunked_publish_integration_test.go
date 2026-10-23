package stages

import (
 "context"
 "os"
 "os/exec"
 "path/filepath"
 "testing"

 "syncshotgo/internal/cinematic"
 "syncshotgo/internal/utils"
)

func TestChunkedProductionPublisher(t *testing.T){
 if testing.Short(){t.Skip("FFmpeg integration")}
 for _,bin:=range []string{"ffmpeg","ffprobe"}{if _,err:=exec.LookPath(bin);err!=nil{t.Skip(bin+" unavailable")}}
 root:=t.TempDir()
 image:=filepath.Join(root,"scene.png")
 audio:=filepath.Join(root,"voice.wav")
 makeInput:=func(dst string,args ...string){
  params:=append([]string{"-hide_banner","-loglevel","error","-y"},args...)
  if b,err:=exec.Command("ffmpeg",append(params,dst)...).CombinedOutput();err!=nil{t.Fatalf("ffmpeg source %s: %v: %s",dst,err,b)}
 }
 makeInput(image,"-f","lavfi","-i","color=c=green:s=320x180","-frames:v","1")
 makeInput(audio,"-f","lavfi","-i","sine=frequency=500:duration=3","-c:a","pcm_s16le")
 timeline:=cinematic.Timeline{FPS:12,Width:320,Height:180,CrossfadeSeconds:0.2,Scenes:[]cinematic.Scene{
 {Image:image,Duration:1.2},{Image:image,Duration:1.2},{Image:image,Duration:1.0},
 }}
 output:=filepath.Join(root,"final.mp4")
 original:=[]byte("prior published media")
 if err:=os.WriteFile(output,original,0600);err!=nil{t.Fatal(err)}
 if err:=cinematic.RenderChunkedEffects(context.Background(),utils.NewLogger(),timeline,audio,output,2,cinematic.Overlays{},promoteVideo);err!=nil{t.Fatalf("production publication failed: %v",err)}
 if err:=validateRenderedMedia(output);err!=nil{t.Fatal(err)}
 if _,err:=os.Stat(output+".syncshot-backup");!os.IsNotExist(err){t.Fatalf("backup unexpectedly present: %v",err)}
 good,err:=os.ReadFile(output);if err!=nil{t.Fatal(err)}
 failedTimeline:=timeline
 failedTimeline.Scenes=append([]cinematic.Scene(nil),timeline.Scenes...)
 failedTimeline.Scenes[0].Image=filepath.Join(root,"missing.png")
 if err:=cinematic.RenderChunkedEffects(context.Background(),utils.NewLogger(),failedTimeline,audio,output,2,cinematic.Overlays{},promoteVideo);err==nil{t.Fatal("expected invalid source to fail")}
 after,err:=os.ReadFile(output);if err!=nil{t.Fatal(err)}
 if string(after)!=string(good){t.Fatal("failed render modified previously published video")}
 matches,err:=filepath.Glob(filepath.Join(root,".cinematic-final-*.mp4"));if err!=nil{t.Fatal(err)}
 if len(matches)!=0{t.Fatalf("temporary files remain: %v",matches)}
}
