package utils

import (
 "context"
 "errors"
 "os"
 "path/filepath"
 "runtime"
 "strings"
 "testing"
 "time"
)

func TestBoundedLog(t *testing.T) {
 b := &boundedLog{max: 5}
 if _, err := b.Write([]byte("abcd")); err != nil { t.Fatal(err) }
 if _, err := b.Write([]byte("efgh")); err != nil { t.Fatal(err) }
 if got := b.String(); got != "defgh" { t.Fatalf("got %q",got) }
 if _, err := b.Write([]byte("1234567")); err != nil { t.Fatal(err) }
 if got := b.String(); got != "34567" { t.Fatalf("got %q",got) }
}

func TestFFmpegContextTimeout(t *testing.T) {
 if runtime.GOOS == "windows" { t.Skip("requires Unix shell") }
 dir := t.TempDir()
 executable := filepath.Join(dir, "ffmpeg")
 if err := os.WriteFile(executable, []byte("#!/bin/sh\nexec sleep 10\n"),0755); err != nil { t.Fatal(err) }
 t.Setenv("PATH",dir+string(os.PathListSeparator)+os.Getenv("PATH"))
 ctx,cancel:=context.WithTimeout(context.Background(),100*time.Millisecond)
 defer cancel()
 started:=time.Now()
 err:=RunFFmpegWithProgressContext(ctx,NewLogger(),1)
 if !errors.Is(err,context.DeadlineExceeded) { t.Fatalf("expected deadline, got %v",err) }
 if time.Since(started)>3*time.Second { t.Fatalf("cancellation delayed: %v",time.Since(started)) }
}

func TestFFmpegExitError(t *testing.T) {
 if runtime.GOOS=="windows" { t.Skip("requires Unix shell") }
 dir:=t.TempDir()
 executable:=filepath.Join(dir,"ffmpeg")
 if err:=os.WriteFile(executable,[]byte("#!/bin/sh\necho bad >&2\nexit 7\n"),0755);err!=nil { t.Fatal(err) }
 t.Setenv("PATH",dir+string(os.PathListSeparator)+os.Getenv("PATH"))
 err:=RunFFmpegWithProgressContext(context.Background(),NewLogger(),1)
 if err==nil || !strings.Contains(err.Error(),"exited") { t.Fatalf("expected process failure, got %v",err) }
}
