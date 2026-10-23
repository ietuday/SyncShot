package cinematic

import (
 "context"
 "os"
 "os/exec"
 "path/filepath"
 "testing"

 "syncshotgo/internal/utils"
)

func TestPartitionTimeline(t *testing.T) {
 timeline:=Timeline{FPS:12,Width:320,Height:180,Scenes:[]Scene{{Image:"a.png",Duration:2},{Image:"b.png",Duration:2},{Image:"c.png",Duration:2},{Image:"d.png",Duration:2},{Image:"e.png",Duration:2}}}
 chunks,err:=PartitionTimeline(timeline,2)
 if err!=nil{t.Fatal(err)}
 if len(chunks)!=3||len(chunks[0].Scenes)!=2||len(chunks[1].Scenes)!=2||len(chunks[2].Scenes)!=1{t.Fatalf("incorrect partitions: %+v",chunks)}
 if chunks[0].Duration()+chunks[1].Duration()+chunks[2].Duration()!=timeline.Duration(){t.Fatal("partition lost duration")}
 if _,err:=PartitionTimeline(timeline,0);err==nil{t.Fatal("zero chunk size accepted")}
 timeline.CrossfadeSeconds=.3
 if _,err:=PartitionTimeline(timeline,2);err==nil{t.Fatal("crossfade across chunks incorrectly accepted")}
}

func TestRenderChunkedIntegration(t *testing.T) {
 if testing.Short(){t.Skip("FFmpeg integration")}
 for _,binary:=range []string{"ffmpeg","ffprobe"} {if _,err:=exec.LookPath(binary);err!=nil{t.Skip(binary+" unavailable")}}
 dir:=t.TempDir()
 still:=filepath.Join(dir,"a.png")
 narration:=filepath.Join(dir,"narr.wav")
 for _,tc:=range []struct{path string;args []string}{
 {still,[]string{"-f","lavfi","-i","color=c=blue:s=320x180","-frames:v","1"}},
 {narration,[]string{"-f","lavfi","-i","sine=frequency=440:duration=4","-c:a","pcm_s16le"}},
 } {
  args:=append([]string{"-hide_banner","-loglevel","error","-y"},tc.args...)
  if out,err:=exec.Command("ffmpeg",append(args,tc.path)...).CombinedOutput();err!=nil{t.Fatalf("source: %v %s",err,out)}
 }
 timeline,err:=FromImages([]string{still,still,still,still},4,12,320,180,0,Static)
 if err!=nil{t.Fatal(err)}
 target:=filepath.Join(dir,"final.mp4")
 if err:=RenderChunked(context.Background(),utils.NewLogger(),timeline,narration,target,2,os.Rename);err!=nil{t.Fatal(err)}
 info,err:=os.Stat(target)
 if err!=nil||info.Size()==0{t.Fatalf("missing result: %v",err)}
 actual,err:=utils.ProbeDurationPrecise(context.Background(),target)
 if err!=nil||actual<3.65||actual>4.35{t.Fatalf("duration %.3f: %v",actual,err)}
}
