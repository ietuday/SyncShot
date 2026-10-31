package cinematic

import (
 "context"
 "fmt"
 "os"
 "path/filepath"
 "strconv"

 "syncshotgo/internal/utils"
)

// renderVisualChunk avoids decoding, trimming, writing and re-encoding narration
// for temporary video parts. The original narration is mixed once at final mux.
func renderVisualChunk(ctx context.Context,log *utils.Logger,t Timeline,output string) error {
 if err:=t.Validate();err!=nil{return err}
 if err:=ctx.Err();err!=nil{return err}
 images,refs,prefix:=sharedSceneInputs(t)
 filter,label,err:=t.buildFilterInputs(refs);if err!=nil{return err}
 if prefix!=""{filter=prefix+";"+filter}
 args:=[]string{"-hide_banner","-y"}
 for _,path:=range images{
  if _,err:=os.Stat(path);err!=nil{return fmt.Errorf("scene image: %w",err)}
  args=append(args,"-loop","1","-framerate",strconv.Itoa(t.FPS),"-i",path)
 }
 if err:=os.MkdirAll(filepath.Dir(output),0755);err!=nil{return err}
 args=append(args,"-filter_complex",filter,"-map",label,"-an",
  "-t",strconv.FormatFloat(t.Duration(),'f',6,64),
  "-c:v","libx264","-pix_fmt","yuv420p","-r",strconv.Itoa(t.FPS),
  "-movflags","+faststart",output)
 if err:=utils.RunFFmpegWithRetryContext(ctx,log,int(t.Duration()),args...);err!=nil{return fmt.Errorf("render visual chunk: %w",err)}
 stat,err:=os.Stat(output);if err!=nil{return err}
 if stat.Size()==0{return fmt.Errorf("empty visual chunk")}
 return ctx.Err()
}
