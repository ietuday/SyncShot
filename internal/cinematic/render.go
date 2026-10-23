package cinematic

import (
 "context"
 "fmt"
 "math"
 "os"
 "path/filepath"
 "strconv"

 "syncshotgo/internal/utils"
)

// Render stages and validates the cinematic output before publishing.
// Publishing uses the existing pipeline's backup/recovery logic via the
// caller-provided publish callback.
func Render(ctx context.Context, log *utils.Logger, timeline Timeline, audio, output string, publish func(string,string)error) error {
 return RenderWithOverlays(ctx,log,timeline,audio,output,Overlays{},publish)
}

// Overlays contains optional static images for cinematic compositing.
type Overlays struct { MusicPath string; MusicVolume float64; MusicFadeSeconds float64; MusicDucking bool; SubtitlePath string; SubscribePath string; NotificationPath string; SubscribeOpacity float32; NotificationOpacity float32 }

func RenderWithOverlays(ctx context.Context, log *utils.Logger, timeline Timeline, audio, output string, overlays Overlays, publish func(string,string)error) error {
 if err:=timeline.Validate();err!=nil {return err}
 if err:=ctx.Err();err!=nil {return err}
 filter,label,err:=timeline.BuildFilter()
 if err!=nil {return err}
 if err:=os.MkdirAll(filepath.Dir(output),0755);err!=nil {return err}
 temp,err:=os.CreateTemp(filepath.Dir(output),".cinematic-*.mp4")
 if err!=nil {return err}
 staged:=temp.Name()
 if err:=temp.Close();err!=nil {os.Remove(staged);return err}
 defer os.Remove(staged)

 args:=[]string{"-hide_banner","-y"}
 for _,p:=range timeline.InputPaths() {
  if _,err:=os.Stat(p);err!=nil {return fmt.Errorf("scene image %s: %w",p,err)}
  args=append(args,"-loop","1","-framerate",strconv.Itoa(timeline.FPS),"-i",p)
 }
 args=append(args,"-i",audio)
 var overlaySteps []struct {path string; opacity float32; width,height,x,y int}
 if overlays.SubscribePath!="" {overlaySteps=append(overlaySteps,struct {path string;opacity float32;width,height,x,y int}{overlays.SubscribePath,overlays.SubscribeOpacity,200,60,220,80})}
 if overlays.NotificationPath!="" {overlaySteps=append(overlaySteps,struct {path string;opacity float32;width,height,x,y int}{overlays.NotificationPath,overlays.NotificationOpacity,80,80,100,20})}
 for _,o:=range overlaySteps {
  if _,err:=os.Stat(o.path);err!=nil {return fmt.Errorf("overlay image %s: %w",o.path,err)}
  args=append(args,"-loop","1","-framerate",strconv.Itoa(timeline.FPS),"-i",o.path)
 }
 subtitleIndex:=-1
 if overlays.SubtitlePath!="" {
  if _,err:=os.Stat(overlays.SubtitlePath);err!=nil{return fmt.Errorf("subtitle SRT: %w",err)}
  subtitleIndex=len(timeline.Scenes)+1+len(overlaySteps)
  args=append(args,"-i",overlays.SubtitlePath)
 }
 musicIndex:=-1
 if overlays.MusicPath!="" {
  if _,err:=os.Stat(overlays.MusicPath);err!=nil{return fmt.Errorf("music file: %w",err)}
  if math.IsNaN(overlays.MusicVolume) || math.IsInf(overlays.MusicVolume,0) || overlays.MusicVolume<=0 || overlays.MusicVolume>1 {return fmt.Errorf("music volume must be >0 and <=1")}
  if math.IsNaN(overlays.MusicFadeSeconds) || math.IsInf(overlays.MusicFadeSeconds,0) || overlays.MusicFadeSeconds<0 || overlays.MusicFadeSeconds>timeline.Duration() {return fmt.Errorf("music fade must be between zero and video duration")}
  musicIndex=len(timeline.Scenes)+1+len(overlaySteps)
  if subtitleIndex>=0 {musicIndex++}
  args=append(args,"-stream_loop","-1","-i",overlays.MusicPath)
 }
 for i,o:=range overlaySteps {
  inputIndex:=len(timeline.Scenes)+1+i
  alpha:=math.Max(0,math.Min(1,float64(o.opacity)))
  previous:=label
  next:=fmt.Sprintf("[overlay%d]",i)
  filter+=fmt.Sprintf(";[%d:v]scale=%d:%d,format=rgba,colorchannelmixer=aa=%.3f[graphic%d];%s[graphic%d]overlay=x=%s:y=%s:shortest=1%s",inputIndex,o.width,o.height,alpha,i,previous,i,overlayX(o.x),overlayY(o.y),next)
  label=next
 }
 audioLabel:=fmt.Sprintf("%d:a:0",len(timeline.Scenes))
 if musicIndex>=0 {
  // Narration remains primary; music is limited and ducked whenever speech is present.
  musicFilter:=fmt.Sprintf("[%d:a:0]aresample=48000,volume=%.4f",musicIndex,overlays.MusicVolume)
  if overlays.MusicFadeSeconds>0 {
   musicFilter+=fmt.Sprintf(",afade=t=in:st=0:d=%.3f,afade=t=out:st=%.3f:d=%.3f",overlays.MusicFadeSeconds,math.Max(0,timeline.Duration()-overlays.MusicFadeSeconds),overlays.MusicFadeSeconds)
  }
  filter+=";"+musicFilter+"[musicbed]"
  if overlays.MusicDucking {
   filter+=fmt.Sprintf(";[%s]aresample=48000,asplit=2[narrmix][narrkey]",audioLabel)
   filter+=";[musicbed][narrkey]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=300[ducked]"
  } else {
   filter+=fmt.Sprintf(";[%s]aresample=48000[narrmix]",audioLabel)
   filter+=";[musicbed]anull[ducked]"
  }
  filter+=";[narrmix][ducked]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[aout]"
  audioLabel="aout"
 }
 audioMap:=audioLabel
 if musicIndex<0 {audioMap=audioLabel} else {audioMap="["+audioLabel+"]"}
 args=append(args,"-filter_complex",filter,
  "-map",label,"-map",audioMap,
  "-t",strconv.FormatFloat(timeline.Duration(),'f',6,64),
  "-c:v","libx264","-pix_fmt","yuv420p","-r",strconv.Itoa(timeline.FPS),
  "-c:a","aac","-b:a","192k","-movflags","+faststart",
  "-progress","pipe:1","-nostats")
 if subtitleIndex>=0 {
  args=append(args,"-map",fmt.Sprintf("%d:0",subtitleIndex),"-c:s","mov_text","-metadata:s:s:0","language=und")
 }
 args=append(args,staged)
 if err:=utils.RunFFmpegWithRetryContext(ctx,log,int(timeline.Duration()),args...);err!=nil {return fmt.Errorf("cinematic rendering: %w",err)}
 if err:=ctx.Err();err!=nil {return err}
 info,err:=os.Stat(staged)
 if err!=nil || info.Size()==0 {return fmt.Errorf("rendered cinematic MP4 missing or empty: %v",err)}
 if duration,err:=utils.ProbeDurationSeconds(staged);err!=nil || duration<=0 {return fmt.Errorf("invalid cinematic output duration: %v",err)}
 return publish(staged,output)
}

func overlayX(rightMargin int) string {return fmt.Sprintf("W-%d",rightMargin)}
func overlayY(bottomOrTop int) string {if bottomOrTop==80 {return "H-80"};return fmt.Sprintf("%d",bottomOrTop)}
