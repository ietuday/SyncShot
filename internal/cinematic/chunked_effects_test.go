package cinematic

import (
 "context"
 "errors"
 "fmt"
 "encoding/json"
 "math"
 "os"
 "os/exec"
 "path/filepath"
 "strings"
 "testing"
 "time"

 "syncshotgo/internal/utils"
)

func TestPartitionEffectsPreservesDuration(t *testing.T){
 timeline:=Timeline{FPS:12,Width:320,Height:180,CrossfadeSeconds:0.25,Scenes:[]Scene{
 {Image:"same.png",Duration:1.25},{Image:"same.png",Duration:1.25},
 {Image:"same.png",Duration:1.25},{Image:"same.png",Duration:1},
 }}
 chunks,err:=PartitionEffectsTimeline(timeline,2);if err!=nil{t.Fatal(err)}
 if len(chunks)!=2||len(chunks[0].Scenes)!=2||len(chunks[1].Scenes)!=2{t.Fatalf("incorrect chunks %+v",chunks)}
 total:=0.0
 for _,c:=range chunks{total+=c.Duration()}
 total-=float64(len(chunks)-1)*timeline.CrossfadeSeconds
 if math.Abs(total-timeline.Duration())>1e-8{t.Fatalf("duration mismatch: %v versus %v",total,timeline.Duration())}
 graph,label,err:=chunkVideoGraph(chunks)
 if err!=nil||label!="[joined1]"||!strings.Contains(graph,"xfade="){t.Fatalf("invalid graph %s, %s, %v",graph,label,err)}
 if _,err:=PartitionEffectsTimeline(timeline,0);err==nil{t.Fatal("accepted zero chunk size")}
}

func TestRenderChunkedEffectsWithFullTracks(t *testing.T){
 if testing.Short(){t.Skip("FFmpeg integration")}
 for _,bin:=range []string{"ffmpeg","ffprobe"}{if _,err:=exec.LookPath(bin);err!=nil{t.Skip(bin+" unavailable")}}
 dir:=t.TempDir()
 img:=filepath.Join(dir,"frame.png")
 voice:=filepath.Join(dir,"voice.wav")
 music:=filepath.Join(dir,"music.wav")
 sub:=filepath.Join(dir,"caption.srt")
 mk:=func(path string,args ...string){
  all:=append([]string{"-hide_banner","-loglevel","error","-y"},args...)
  all=append(all,path)
  if out,err:=exec.Command("ffmpeg",all...).CombinedOutput();err!=nil{t.Fatalf("make %s: %v %s",path,err,out)}
 }
 mk(img,"-f","lavfi","-i","color=c=blue:s=320x180","-frames:v","1")
 mk(voice,"-f","lavfi","-i","sine=frequency=440:duration=3.4","-c:a","pcm_s16le")
 mk(music,"-f","lavfi","-i","sine=frequency=220:duration=1","-c:a","pcm_s16le")
 if err:=os.WriteFile(sub,[]byte("1\n00:00:00,000 --> 00:00:01,000\nHello\n"),0600);err!=nil{t.Fatal(err)}
 tl:=Timeline{FPS:12,Width:320,Height:180,CrossfadeSeconds:0.2,Scenes:[]Scene{
  {Image:img,Duration:1.1},{Image:img,Duration:1.1},{Image:img,Duration:1.1},{Image:img,Duration:0.7},
 }}
 // 1.1 + 1.1 + 1.1 + .7 - 3*.2 = 3.4 seconds.
 target:=filepath.Join(dir,"result.mp4")
 effects:=Overlays{MusicPath:music,MusicVolume:0.15,MusicFadeSeconds:0.2,MusicDucking:true,SubtitlePath:sub}
 if err:=RenderChunkedEffects(context.Background(),utils.NewLogger(),tl,voice,target,2,effects,os.Rename);err!=nil{t.Fatal(err)}
 d,err:=utils.ProbeDurationPrecise(context.Background(),target)
 if err!=nil||math.Abs(d-tl.Duration())>0.35{t.Fatalf("duration %.3f expected %.3f: %v",d,tl.Duration(),err)}
 data,err:=exec.Command("ffprobe","-v","error","-show_entries","stream=codec_type,codec_name","-of","json",target).Output()
 if err!=nil{t.Fatal(err)}
 var probe struct{Streams []struct{CodecType string `json:"codec_type"`;CodecName string `json:"codec_name"`} `json:"streams"`}
 if err:=json.Unmarshal(data,&probe);err!=nil{t.Fatal(err)}
 video,audio,subs:=0,0,0
 for _,stream:=range probe.Streams{
  switch stream.CodecType{
  case "video":video++
  case "audio":audio++
  case "subtitle":if stream.CodecName!="mov_text"{t.Fatalf("unexpected subtitle codec %s",stream.CodecName)};subs++
  }
 }
 if video!=1||audio!=1||subs!=1{t.Fatalf("incorrect streams: %s",data)}
 cached,err:=filepath.Glob(filepath.Join(dir,".syncshot-chunk-cache","*.mp4"))
 if err!=nil||len(cached)!=2{t.Fatalf("expected two cached visual chunks, found %v (%v)",cached,err)}
 stamps:=make([]int64,len(cached))
 for i,p:=range cached{info,err:=os.Stat(p);if err!=nil{t.Fatal(err)};stamps[i]=info.ModTime().UnixNano()}
 if err:=RenderChunkedEffects(context.Background(),utils.NewLogger(),tl,voice,target,2,effects,os.Rename);err!=nil{t.Fatal(err)}
 for i,p:=range cached{info,err:=os.Stat(p);if err!=nil{t.Fatal(err)};if info.ModTime().UnixNano()!=stamps[i]{t.Fatal("cache hit unexpectedly re-rendered chunk")}}

}

func TestChunkCacheKeyUsesImageContentAndSettings(t *testing.T){
 dir:=t.TempDir()
 image:=filepath.Join(dir,"image.png")
 if err:=os.WriteFile(image,[]byte("image-A"),0600);err!=nil{t.Fatal(err)}
 scene:=Scene{Image:image,Duration:2,Motion:Static}
 chunk:=Timeline{FPS:24,Width:320,Height:180,Scenes:[]Scene{scene}}
 a,err:=chunkCacheKey(chunk);if err!=nil{t.Fatal(err)}
 moved:=filepath.Join(dir,"moved.png")
 if err:=os.Rename(image,moved);err!=nil{t.Fatal(err)}
 chunk.Scenes[0].Image=moved
 b,err:=chunkCacheKey(chunk);if err!=nil{t.Fatal(err)}
 if a!=b{t.Fatal("temporary path should not affect cache identity")}
 if err:=os.WriteFile(moved,[]byte("image-B"),0600);err!=nil{t.Fatal(err)}
 c,err:=chunkCacheKey(chunk);if err!=nil{t.Fatal(err)}
 if a==c{t.Fatal("changed image content reused cached visual")}
 chunk.Scenes[0].Duration=3
 d,err:=chunkCacheKey(chunk);if err!=nil{t.Fatal(err)}
 if c==d{t.Fatal("changed scene duration reused cached visual")}
}

func TestInvalidCachedChunkIsRejected(t *testing.T){
 dir:=t.TempDir()
 p:=filepath.Join(dir,"bad.mp4")
 if validCachedChunk(context.Background(),p,1){t.Fatal("missing cache accepted")}
 if err:=os.WriteFile(p,[]byte("not mp4"),0600);err!=nil{t.Fatal(err)}
 if validCachedChunk(context.Background(),p,1){t.Fatal("corrupt cache accepted")}
}

func TestPruneChunkCacheOnlyOldUnreferencedFiles(t *testing.T){
 dir:=t.TempDir()
 old:="a"+strings.Repeat("0",63)+".mp4"
 keep:="b"+strings.Repeat("0",63)+".mp4"
 recent:="c"+strings.Repeat("0",63)+".mp4"
 other:="notes.txt"
 for _,name:=range []string{old,keep,recent,other}{
  if err:=os.WriteFile(filepath.Join(dir,name),[]byte("x"),0600);err!=nil{t.Fatal(err)}
 }
 now:=time.Now()
 for _,name:=range []string{old,keep,other}{
  if err:=os.Chtimes(filepath.Join(dir,name),now.Add(-8*24*time.Hour),now.Add(-8*24*time.Hour));err!=nil{t.Fatal(err)}
 }
 if err:=os.Symlink(filepath.Join(dir,old),filepath.Join(dir,strings.Repeat("d",64)+".mp4"));err!=nil{t.Fatal(err)}
 removed,err:=pruneChunkCache(dir,map[string]bool{keep:true},now)
 if err!=nil||removed!=1{t.Fatalf("removed=%d err=%v",removed,err)}
 if _,err:=os.Stat(filepath.Join(dir,old));!os.IsNotExist(err){t.Fatalf("stale cache remains: %v",err)}
 for _,name:=range []string{keep,recent,other}{
  if _,err:=os.Stat(filepath.Join(dir,name));err!=nil{t.Fatalf("unexpected deletion of %s: %v",name,err)}
 }
 if _,err:=os.Lstat(filepath.Join(dir,strings.Repeat("d",64)+".mp4"));err!=nil{t.Fatal("symlink removed")}
}

func TestStitchFFmpegArgsBoundFilterThreads(t *testing.T){
 args:=strings.Join(stitchFFmpegArgs()," ")
 for _,flag:=range []string{"-filter_complex_threads 1","-filter_threads 1"}{
  if !strings.Contains(args,flag){t.Fatalf("missing memory bound %q: %s",flag,args)}
 }
}

func TestInterruptedPublishPreservesCacheForRetry(t *testing.T){
 if testing.Short(){t.Skip("FFmpeg integration")}
 for _,bin:=range []string{"ffmpeg","ffprobe"}{if _,err:=exec.LookPath(bin);err!=nil{t.Skip(bin+" unavailable")}}
 dir:=t.TempDir()
 image:=filepath.Join(dir,"image.png")
 audio:=filepath.Join(dir,"narration.wav")
 for _,item:=range []struct{path string;args []string}{
  {image,[]string{"-f","lavfi","-i","color=c=blue:s=320x180","-frames:v","1"}},
  {audio,[]string{"-f","lavfi","-i","sine=frequency=440:duration=2.4","-c:a","pcm_s16le"}},
 }{
  args:=append([]string{"-hide_banner","-loglevel","error","-y"},item.args...)
  if out,err:=exec.Command("ffmpeg",append(args,item.path)...).CombinedOutput();err!=nil{t.Fatalf("make input: %v %s",err,out)}
 }
 tl:=Timeline{FPS:12,Width:320,Height:180,CrossfadeSeconds:0.2,Scenes:[]Scene{
  {Image:image,Duration:1.3,Motion:Static},{Image:image,Duration:1.3,Motion:Static},
 }}
 output:=filepath.Join(dir,"final.mp4")
 injected:=fmt.Errorf("injected publication failure")
 publishFail:=func(staged,dest string)error{return injected}
 if err:=RenderChunkedEffects(context.Background(),utils.NewLogger(),tl,audio,output,1,Overlays{},publishFail);!errors.Is(err,injected){t.Fatalf("expected publication failure, got %v",err)}
 if _,err:=os.Stat(output);!os.IsNotExist(err){t.Fatalf("failed publication unexpectedly replaced output: %v",err)}
 cache,err:=filepath.Glob(filepath.Join(dir,".syncshot-chunk-cache","*.mp4"))
 if err!=nil||len(cache)!=1{t.Fatalf("expected one content-addressed chunk for two identical scenes, got %v: %v",cache,err)}
 stamps:=make(map[string]int64,len(cache))
 for _,part:=range cache{
  info,err:=os.Stat(part);if err!=nil{t.Fatal(err)}
  stamps[part]=info.ModTime().UnixNano()
 }
 if err:=RenderChunkedEffects(context.Background(),utils.NewLogger(),tl,audio,output,1,Overlays{},os.Rename);err!=nil{t.Fatalf("retry failed: %v",err)}
 if info,err:=os.Stat(output);err!=nil||info.Size()==0{t.Fatalf("missing recovered output: %v",err)}
 for part,stamp:=range stamps{
  info,err:=os.Stat(part);if err!=nil{t.Fatal(err)}
  if info.ModTime().UnixNano()!=stamp{t.Fatalf("cache chunk re-rendered: %s",part)}
 }
 duration,err:=utils.ProbeDurationPrecise(context.Background(),output)
 if err!=nil||math.Abs(duration-tl.Duration())>.35{t.Fatalf("recovered video duration %.3f expected %.3f: %v",duration,tl.Duration(),err)}
}

func TestCorruptCachedChunkIsRebuilt(t *testing.T){
 if testing.Short(){t.Skip("FFmpeg integration")}
 for _,binary:=range []string{"ffmpeg","ffprobe"}{if _,err:=exec.LookPath(binary);err!=nil{t.Skip(binary+" unavailable")}}
 dir:=t.TempDir()
 img:=filepath.Join(dir,"scene.png")
 narration:=filepath.Join(dir,"voice.wav")
 makeMedia:=func(dest string,params ...string){
  args:=append([]string{"-hide_banner","-loglevel","error","-y"},params...)
  if out,err:=exec.Command("ffmpeg",append(args,dest)...).CombinedOutput();err!=nil{t.Fatalf("generate media %s: %v %s",dest,err,out)}
 }
 makeMedia(img,"-f","lavfi","-i","color=c=red:s=320x180","-frames:v","1")
 makeMedia(narration,"-f","lavfi","-i","sine=frequency=440:duration=1.2","-c:a","pcm_s16le")
 tl:=Timeline{FPS:12,Width:320,Height:180,Scenes:[]Scene{{Image:img,Duration:1.2,Motion:Static}}}
 target:=filepath.Join(dir,"rendered.mp4")
 if err:=RenderChunkedEffects(context.Background(),utils.NewLogger(),tl,narration,target,1,Overlays{},os.Rename);err!=nil{t.Fatal(err)}
 parts,err:=filepath.Glob(filepath.Join(dir,".syncshot-chunk-cache","*.mp4"))
 if err!=nil||len(parts)!=1{t.Fatalf("expected one cached chunk: %v %v",parts,err)}
 if err:=os.WriteFile(parts[0],[]byte("corrupt MP4"),0600);err!=nil{t.Fatal(err)}
 if validCachedChunk(context.Background(),parts[0],1.2){t.Fatal("corrupt cached chunk validated")}
 if err:=RenderChunkedEffects(context.Background(),utils.NewLogger(),tl,narration,target,1,Overlays{},os.Rename);err!=nil{t.Fatalf("recovery failed: %v",err)}
 if !validCachedChunk(context.Background(),parts[0],1.2){t.Fatal("corrupt cache not rebuilt")}
 if info,err:=os.Stat(target);err!=nil||info.Size()==0{t.Fatalf("output missing after recovery: %v",err)}
}
