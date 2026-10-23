package cinematic

import (
 "context"
 "fmt"
 "math"
 "os"
 "os/exec"
 "path/filepath"
 "strconv"
 "strings"

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

// RenderChunkedEffects processes bounded scene groups and adds narration, music,
// ducking, subtitles and graphics in a single final, full-duration mux pass.
func RenderChunkedEffects(ctx context.Context,log *utils.Logger,t Timeline,audio,output string,maxScenes int,overlays Overlays,publish func(string,string)error) error{
 chunks,err:=PartitionEffectsTimeline(t,maxScenes);if err!=nil{return err}
 if err:=ctx.Err();err!=nil{return err}
 if err:=os.MkdirAll(filepath.Dir(output),0755);err!=nil{return err}
 dir,err:=os.MkdirTemp(filepath.Dir(output),".cinematic-effects-*");if err!=nil{return err}
 defer os.RemoveAll(dir)
 args:=[]string{"-hide_banner","-y"}
 offset:=0.0
 for i,chunk:=range chunks{
  if err:=ctx.Err();err!=nil{return err}
  narration:=filepath.Join(dir,fmt.Sprintf("sample_%04d.wav",i))
  cmd:=exec.CommandContext(ctx,"ffmpeg","-hide_banner","-loglevel","error","-y","-ss",strconv.FormatFloat(offset,'f',6,64),"-i",audio,"-t",strconv.FormatFloat(chunk.Duration(),'f',6,64),"-vn","-c:a","pcm_s16le",narration)
  if msg,err:=cmd.CombinedOutput();err!=nil{return fmt.Errorf("chunk %d narration: %w %s",i,err,msg)}
  part:=filepath.Join(dir,fmt.Sprintf("part_%04d.mp4",i))
  if err:=RenderWithOverlays(ctx,log,chunk,narration,part,Overlays{},os.Rename);err!=nil{return fmt.Errorf("render chunk %d: %w",i,err)}
  if err:=os.Remove(narration);err!=nil{return err}
  args=append(args,"-i",part)
  offset+=chunk.Duration()
  if i<len(chunks)-1{offset-=t.CrossfadeSeconds}
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
 return publish(final,output)
}
