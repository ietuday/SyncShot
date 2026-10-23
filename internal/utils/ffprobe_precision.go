package utils

import (
 "context"
 "fmt"
 "math"
 "os/exec"
 "strconv"
 "strings"
 "time"
)

// ProbeDurationPrecise returns FFprobe media duration without integer rounding.
func ProbeDurationPrecise(ctx context.Context, path string) (float64,error) {
 probeCtx,cancel:=context.WithTimeout(ctx,30*time.Second)
 defer cancel()
 out,err:=exec.CommandContext(probeCtx,"ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",path).Output()
 if err!=nil {return 0,fmt.Errorf("ffprobe duration for %s: %w",path,err)}
 n,err:=strconv.ParseFloat(strings.TrimSpace(string(out)),64)
 if err!=nil || math.IsNaN(n) || math.IsInf(n,0) || n<=0 {return 0,fmt.Errorf("invalid media duration %q",strings.TrimSpace(string(out)))}
 return n,nil
}
