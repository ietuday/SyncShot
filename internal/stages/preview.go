package stages

import (
 "context"
 "fmt"
 "os"
 "os/exec"
 "path/filepath"
 "strconv"
)

// TrimPreviewAudio produces a short WAV copy without modifying the narration.
func TrimPreviewAudio(ctx context.Context, source,target string, seconds int) error {
 if seconds<=0 {return fmt.Errorf("preview duration must be positive")}
 if err:=os.MkdirAll(filepath.Dir(target),0755);err!=nil{return err}
 cmd:=exec.CommandContext(ctx,"ffmpeg","-hide_banner","-loglevel","error","-y","-i",source,"-t",strconv.Itoa(seconds),"-vn","-c:a","pcm_s16le",target)
 if out,err:=cmd.CombinedOutput();err!=nil {return fmt.Errorf("trim narration: %w: %s",err,out)}
 info,err:=os.Stat(target)
 if err!=nil{return fmt.Errorf("trimmed preview: %w",err)}
 if info.Size()==0{return fmt.Errorf("trimmed preview audio is empty")}
 return nil
}
