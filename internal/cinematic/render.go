package cinematic

import (
 "context"
 "fmt"
 "os"
 "path/filepath"
 "strconv"

 "syncshotgo/internal/utils"
)

// Render stages and validates the cinematic output before publishing.
// Publishing uses the existing pipeline's backup/recovery logic via the
// caller-provided publish callback.
func Render(ctx context.Context, log *utils.Logger, timeline Timeline, audio, output string, publish func(string,string)error) error {
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
 args=append(args,"-i",audio,"-filter_complex",filter,
  "-map",label,"-map",fmt.Sprintf("%d:a:0",len(timeline.Scenes)),
  "-t",strconv.FormatFloat(timeline.Duration(),'f',6,64),
  "-c:v","libx264","-pix_fmt","yuv420p","-r",strconv.Itoa(timeline.FPS),
  "-c:a","aac","-b:a","192k","-movflags","+faststart",
  "-progress","pipe:1","-nostats",staged)
 if err:=utils.RunFFmpegWithRetryContext(ctx,log,int(timeline.Duration()),args...);err!=nil {return fmt.Errorf("cinematic rendering: %w",err)}
 if err:=ctx.Err();err!=nil {return err}
 info,err:=os.Stat(staged)
 if err!=nil || info.Size()==0 {return fmt.Errorf("rendered cinematic MP4 missing or empty: %v",err)}
 if duration,err:=utils.ProbeDurationSeconds(staged);err!=nil || duration<=0 {return fmt.Errorf("invalid cinematic output duration: %v",err)}
 return publish(staged,output)
}
