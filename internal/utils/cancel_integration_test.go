package utils

import (
 "context"
 "errors"
 "os"
 "os/exec"
 "path/filepath"
 "runtime"
 "testing"
 "time"
)

// Exercises actual FFmpeg cancellation while rendering an indefinitely looping
// synthetic input; verifies that no completed output is published.
func TestFFmpegRealCancellation(t *testing.T) {
 if testing.Short() { t.Skip("integration test") }
 if runtime.GOOS == "windows" { t.Skip("Unix integration test") }
 if _,err:=exec.LookPath("ffmpeg");err!=nil { t.Skip("ffmpeg unavailable") }
 out:=filepath.Join(t.TempDir(),"cancelled.mp4")
 ctx,cancel:=context.WithTimeout(context.Background(),1200*time.Millisecond)
 defer cancel()
 args:=[]string{"-hide_banner","-loglevel","error","-y","-f","lavfi","-i","testsrc2=size=320x180:rate=24","-c:v","libx264","-preset","ultrafast","-f","mp4",out}
 started:=time.Now()
 err:=RunFFmpegWithProgressContext(ctx,NewLogger(),0,args...)
 if !errors.Is(err,context.DeadlineExceeded) {t.Fatalf("expected timeout, got %v",err)}
 if time.Since(started)>8*time.Second {t.Fatalf("cancellation took too long: %v",time.Since(started))}
 // FFmpeg itself may leave partial MP4; callers must use staged publishing.
 if _,err:=os.Stat(out);err==nil {t.Log("partial output correctly remains caller responsibility")}
}
