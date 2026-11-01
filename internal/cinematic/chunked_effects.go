package cinematic

import (
 "context"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "io"
 "fmt"
 "math"
 "os"
 "path/filepath"
 "strconv"
 "strings"
 "time"

 "syncshotgo/internal/utils"
)

// PartitionEffectsTimeline preserves crossfades within each chunk and between
// adjacent chunks. Each chunk has at most maxScenes image scenes.
func PartitionEffectsTimeline(t Timeline,maxScenes int)([]Timeline,error){
 if err:=t.Validate();err!=nil{return nil,err}
 if maxScenes<1{return nil,fmt.Errorf("chunk size must be positive")}
 var out []Timeline
 for start:=0;start<len(t.Scenes);start+=maxScenes{
  end:=start+maxScenes
  if end>len(t.Scenes){end=len(t.Scenes)}
  c:=t;c.Scenes=append([]Scene(nil),t.Scenes[start:end]...)
  out=append(out,c)
 }
 return out,nil
}

func chunkVideoGraph(chunks []Timeline)(string,string,error){
 if len(chunks)==0{return "","",fmt.Errorf("no chunks")}
 fps:=chunks[0].FPS
 fade:=chunks[0].CrossfadeSeconds
 var p []string
 for i:=range chunks {p=append(p,fmt.Sprintf("[%d:v]fps=fps=%d:start_time=0,format=yuv420p[part%d]",i,fps,i))}
 if len(chunks)==1{return strings.Join(p,";"),"[part0]",nil}
 if fade==0{
  var refs strings.Builder
  for i:=range chunks {fmt.Fprintf(&refs,"[part%d]",i)}
  p=append(p,fmt.Sprintf("%sconcat=n=%d:v=1:a=0[stitched]",refs.String(),len(chunks)))
  return strings.Join(p,";"),"[stitched]",nil
 }
 offset:=chunks[0].Duration()
 for i:=1;i<len(chunks);i++{
  prev:=fmt.Sprintf("part%d",i-1)
  if i>1{prev=fmt.Sprintf("joined%d",i-1)}
  p=append(p,fmt.Sprintf("[%s][part%d]xfade=transition=fade:duration=%.6f:offset=%.6f[joined%d]",prev,i,fade,offset-fade,i))
  offset+=chunks[i].Duration()-fade
 }
 return strings.Join(p,";"),fmt.Sprintf("[joined%d]",len(chunks)-1),nil
}

// chunkCacheKey ties resumed visual chunks to exact processed image bytes and
// render settings. Temporary processed-image paths are deliberately excluded.
func chunkCacheKey(chunk Timeline)(string,error){
 h:=sha256.New()
 settings:=struct{
  Version int
  FPS,Width,Height int
  Fade float64
  Scenes []struct{Duration float64;Motion Motion;ImageSHA256 string}
 }{Version:1,FPS:chunk.FPS,Width:chunk.Width,Height:chunk.Height,Fade:chunk.CrossfadeSeconds}
 for _,scene:=range chunk.Scenes{
  input,err:=os.Open(scene.Image);if err!=nil{return "",err}
  hash:=sha256.New()
  _,copyErr:=io.Copy(hash,input)
  closeErr:=input.Close()
  if copyErr!=nil{return "",copyErr};if closeErr!=nil{return "",closeErr}
  settings.Scenes=append(settings.Scenes,struct{Duration float64;Motion Motion;ImageSHA256 string}{
   scene.Duration,scene.Motion,hex.EncodeToString(hash.Sum(nil)),
  })
 }
 if err:=json.NewEncoder(h).Encode(settings);err!=nil{return "",err}
 return hex.EncodeToString(h.Sum(nil)),nil
}

func validCachedChunk(ctx context.Context,path string,want float64)bool{
 info,err:=os.Stat(path)
 if err!=nil||!info.Mode().IsRegular()||info.Size()==0{return false}
 duration,err:=utils.ProbeDurationPrecise(ctx,path)
 return err==nil && math.Abs(duration-want)<=0.35
}

// pruneChunkCache removes only old, unreferenced regular MP4 cache files.
// It never follows symlinks, and preserves all chunks used by this run.
func pruneChunkCache(directory string, keep map[string]bool, now time.Time) (int,error) {
 entries,err:=os.ReadDir(directory);if err!=nil{return 0,err}
 removed:=0
 for _,entry:=range entries {
  name:=entry.Name()
  if keep[name] || entry.Type()&os.ModeSymlink!=0 || !entry.Type().IsRegular() {continue}
  if !strings.HasSuffix(name,".mp4") || len(name)!=68 {continue}
  key:=strings.TrimSuffix(name,".mp4")
  if len(key)!=64 || strings.Trim(key,"0123456789abcdef")!="" {continue}
  info,err:=entry.Info();if err!=nil{return removed,err}
  if now.Sub(info.ModTime())<7*24*time.Hour {continue}
  if err:=os.Remove(filepath.Join(directory,name));err!=nil{return removed,err}
  removed++
 }
 return removed,nil
}

// RenderChunkedEffects processes bounded scene groups and adds narration, music,
// ducking, subtitles and graphics in a single final, full-duration mux pass.
func RenderChunkedEffects(ctx context.Context,log *utils.Logger,t Timeline,audio,output string,maxScenes int,overlays Overlays,publish func(string,string)error) error{
 chunks,err:=PartitionEffectsTimeline(t,maxScenes);if err!=nil{return err}
 if err:=ctx.Err();err!=nil{return err}
 if err:=os.MkdirAll(filepath.Dir(output),0755);err!=nil{return err}
 dir,err:=os.MkdirTemp(filepath.Dir(output),".cinematic-effects-*");if err!=nil{return err}
 defer os.RemoveAll(dir)
 cacheDir:=filepath.Join(filepath.Dir(output),".syncshot-chunk-cache")
 keep:=make(map[string]bool,len(chunks))
 args:=[]string{"-hide_banner","-y"}
 for i,chunk:=range chunks{
  if err:=ctx.Err();err!=nil{return err}
  key,err:=chunkCacheKey(chunk)
  if err!=nil{return fmt.Errorf("fingerprint chunk %d: %w",i,err)}
  if err:=os.MkdirAll(cacheDir,0700);err!=nil{return err}
  keep[key+".mp4"]=true
  part:=filepath.Join(cacheDir,key+".mp4")
  if validCachedChunk(ctx,part,chunk.Duration()){
   log.Info(fmt.Sprintf("Reusing validated cinematic chunk %d/%d",i+1,len(chunks)))
  }else{
   // A failed render cannot overwrite the last known good cache entry.
   tmp,err:=os.CreateTemp(cacheDir,".chunk-*.mp4")
   if err!=nil{return err}
   staging:=tmp.Name()
   if err:=tmp.Close();err!=nil{os.Remove(staging);return err}
   os.Remove(staging)
   if err:=renderVisualChunk(ctx,log,chunk,staging);err!=nil{os.Remove(staging);return fmt.Errorf("render chunk %d: %w",i,err)}
   if !validCachedChunk(ctx,staging,chunk.Duration()){os.Remove(staging);return fmt.Errorf("invalid rendered chunk %d",i)}
   if err:=os.Rename(staging,part);err!=nil{os.Remove(staging);return err}
  }
  args=append(args,"-i",part)
 }
 args=append(args,"-i",audio)
 filter,videoLabel,err:=chunkVideoGraph(chunks);if err!=nil{return err}
 audioIdx:=len(chunks)
 graphics:=[]struct{path string;opacity float32;width,height,x,y int}{}
 if overlays.SubscribePath!=""{graphics=append(graphics,struct{path string;opacity float32;width,height,x,y int}{overlays.SubscribePath,overlays.SubscribeOpacity,200,60,220,80})}
 if overlays.NotificationPath!=""{graphics=append(graphics,struct{path string;opacity float32;width,height,x,y int}{overlays.NotificationPath,overlays.NotificationOpacity,80,80,100,20})}
 for i,o:=range graphics{
  if _,err:=os.Stat(o.path);err!=nil{return fmt.Errorf("overlay %s: %w",o.path,err)}
  idx:=audioIdx+1+i
  args=append(args,"-loop","1","-i",o.path)
  next:=fmt.Sprintf("[overlay%d]",i)
  alpha:=math.Max(0,math.Min(1,float64(o.opacity)))
  filter+=fmt.Sprintf(";[%d:v]scale=%d:%d,format=rgba,colorchannelmixer=aa=%.3f[graphic%d];%s[graphic%d]overlay=x=%s:y=%s:shortest=1%s",idx,o.width,o.height,alpha,i,videoLabel,i,overlayX(o.x),overlayY(o.y),next)
  videoLabel=next
 }
 nextIdx:=audioIdx+1+len(graphics)
 subtitleIdx:=-1
 if overlays.SubtitlePath!=""{
  if _,err:=os.Stat(overlays.SubtitlePath);err!=nil{return fmt.Errorf("subtitle: %w",err)}
  subtitleIdx=nextIdx;nextIdx++
  args=append(args,"-i",overlays.SubtitlePath)
 }
 musicIdx:=-1
 if overlays.MusicPath!=""{
  if _,err:=os.Stat(overlays.MusicPath);err!=nil{return fmt.Errorf("music: %w",err)}
  if !finite(overlays.MusicVolume)||overlays.MusicVolume<=0||overlays.MusicVolume>1{return fmt.Errorf("music volume must be in (0,1]")}
  if !finite(overlays.MusicFadeSeconds)||overlays.MusicFadeSeconds<0||overlays.MusicFadeSeconds>t.Duration(){return fmt.Errorf("invalid music fade duration")}
  musicIdx=nextIdx
  args=append(args,"-stream_loop","-1","-i",overlays.MusicPath)
 }
 audioMap:=fmt.Sprintf("%d:a:0",audioIdx)
 if musicIdx>=0 {
  bed:=fmt.Sprintf("[%d:a:0]aresample=48000,volume=%.4f",musicIdx,overlays.MusicVolume)
  if overlays.MusicFadeSeconds>0 {
   d:=overlays.MusicFadeSeconds
   bed+=fmt.Sprintf(",afade=t=in:st=0:d=%.3f,afade=t=out:st=%.3f:d=%.3f",d,math.Max(0,t.Duration()-d),d)
  }
  filter+=";"+bed+"[musicbed]"
  if overlays.MusicDucking{
   filter+=fmt.Sprintf(";[%s]aresample=48000,asplit=2[narrmix][narrkey]",audioMap)
   filter+=";[musicbed][narrkey]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=300[ducked]"
  }else{
   filter+=fmt.Sprintf(";[%s]aresample=48000[narrmix];[musicbed]anull[ducked]",audioMap)
  }
  filter+=";[narrmix][ducked]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[aout]"
  audioMap="[aout]"
 }
 // Stage beside destination to satisfy the production publisher's
 // same-directory rename and rollback requirements.
 stagedFile,err:=os.CreateTemp(filepath.Dir(output),".cinematic-final-*.mp4")
 if err!=nil{return err}
 final:=stagedFile.Name()
 if err:=stagedFile.Close();err!=nil{os.Remove(final);return err}
 defer os.Remove(final)
 args=append(args,"-filter_complex",filter,"-map",videoLabel,"-map",audioMap,
  "-t",strconv.FormatFloat(t.Duration(),'f',6,64),
  "-c:v","libx264","-pix_fmt","yuv420p","-r",strconv.Itoa(t.FPS),
  "-c:a","aac","-b:a","192k","-movflags","+faststart")
 if subtitleIdx>=0{args=append(args,"-map",fmt.Sprintf("%d:0",subtitleIdx),"-c:s","mov_text","-metadata:s:s:0","language=und")}
 args=append(args,final)
 if err:=utils.RunFFmpegWithRetryContext(ctx,log,int(t.Duration()),args...);err!=nil{return fmt.Errorf("stitch cinematic chunks: %w",err)}
 info,err:=os.Stat(final);if err!=nil||info.Size()==0{return fmt.Errorf("empty stitched output: %v",err)}
 d,err:=utils.ProbeDurationPrecise(ctx,final);if err!=nil{return err}
 if math.Abs(d-t.Duration())>0.35{return fmt.Errorf("chunked duration drift %.3f vs %.3f",d,t.Duration())}
 if err:=ctx.Err();err!=nil{return err}
 if err:=publish(final,output);err!=nil{return err}
 if removed,err:=pruneChunkCache(cacheDir,keep,time.Now());err!=nil {
  log.Warn("Chunk cache cleanup skipped: "+err.Error())
 }else if removed>0 {log.Info(fmt.Sprintf("Removed %d old unused cached chunks",removed))}
 return nil
}
