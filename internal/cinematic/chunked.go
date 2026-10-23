package cinematic

import (
 "context"
 "fmt"
 "os"
 "os/exec"
 "path/filepath"
 "strconv"
 "strings"

 "syncshotgo/internal/utils"
)

// PartitionTimeline divides a timeline into bounded scene groups. Currently
// boundaries are supported only when crossfades are disabled.
func PartitionTimeline(t Timeline, maxScenes int) ([]Timeline,error) {
 if err:=t.Validate();err!=nil{return nil,err}
 if maxScenes<1{return nil,fmt.Errorf("maxScenes must be positive")}
 if t.CrossfadeSeconds!=0{return nil,fmt.Errorf("chunked rendering requires zero crossfade")}
 chunks:=make([]Timeline,0,(len(t.Scenes)+maxScenes-1)/maxScenes)
 for start:=0;start<len(t.Scenes);start+=maxScenes {
  end:=start+maxScenes
  if end>len(t.Scenes){end=len(t.Scenes)}
  chunk:=t
  chunk.Scenes=append([]Scene(nil),t.Scenes[start:end]...)
  chunks=append(chunks,chunk)
 }
 return chunks,nil
}

// RenderChunked limits FFmpeg graph size by rendering one scene group at a
// time, concatenating independently encoded MP4s, then atomically publishing.
func RenderChunked(ctx context.Context,log *utils.Logger,t Timeline,audio,output string,maxScenes int,publish func(string,string)error) error {
 chunks,err:=PartitionTimeline(t,maxScenes)
 if err!=nil{return err}
 if err:=ctx.Err();err!=nil{return err}
 if err:=os.MkdirAll(filepath.Dir(output),0755);err!=nil{return err}
 dir,err:=os.MkdirTemp(filepath.Dir(output),".cinematic-chunks-*")
 if err!=nil{return err}
 defer os.RemoveAll(dir)
 names:=make([]string,0,len(chunks))
 offset:=0.0
 for i,chunk:=range chunks {
  if err:=ctx.Err();err!=nil{return err}
  clipAudio:=filepath.Join(dir,fmt.Sprintf("narration_%04d.wav",i))
  // Trim audio to match each chunk's video interval, preserving timestamps.
  cmd:=exec.CommandContext(ctx,"ffmpeg","-hide_banner","-loglevel","error","-y","-ss",strconv.FormatFloat(offset,'f',6,64),"-i",audio,"-t",strconv.FormatFloat(chunk.Duration(),'f',6,64),"-vn","-c:a","pcm_s16le",clipAudio)
  if data,err:=cmd.CombinedOutput();err!=nil{return fmt.Errorf("chunk %d audio trim: %w: %s",i,err,data)}
  name:=filepath.Join(dir,fmt.Sprintf("part_%04d.mp4",i))
  if err:=RenderWithOverlays(ctx,log,chunk,clipAudio,name,Overlays{},os.Rename);err!=nil{return fmt.Errorf("chunk %d: %w",i,err)}
  names=append(names,name)
  offset+=chunk.Duration()
  if err:=os.Remove(clipAudio);err!=nil{return err}
 }
 // Use an FFmpeg concat demuxer; parts share identical codec settings.
 var list strings.Builder
 for _,name:=range names {
  // Names originate from a generated temp directory: single quotes escaped.
  clean:=strings.ReplaceAll(name,"'","'\\''")
  fmt.Fprintf(&list,"file '%s'\n",clean)
 }
 manifest:=filepath.Join(dir,"chunks.txt")
 if err:=os.WriteFile(manifest,[]byte(list.String()),0600);err!=nil{return err}
 staged:=filepath.Join(dir,"joined.mp4")
 cmd:=exec.CommandContext(ctx,"ffmpeg","-hide_banner","-loglevel","error","-y","-f","concat","-safe","0","-i",manifest,"-c","copy","-movflags","+faststart",staged)
 if data,err:=cmd.CombinedOutput();err!=nil{return fmt.Errorf("concat cinematic chunks: %w: %s",err,data)}
 info,err:=os.Stat(staged)
 if err!=nil||info.Size()==0{return fmt.Errorf("missing chunked output: %v",err)}
 duration,err:=utils.ProbeDurationPrecise(ctx,staged)
 if err!=nil{return err}
 if diff:=duration-t.Duration();diff>0.35||diff< -0.35{return fmt.Errorf("chunk duration drift: output %.3fs, expected %.3fs",duration,t.Duration())}
 if err:=ctx.Err();err!=nil{return err}
 return publish(staged,output)
}
