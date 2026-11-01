package cinematic

import (
 "context"
 "encoding/json"
 "math"
 "os"
 "os/exec"
 "path/filepath"
 "strings"
 "testing"

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
