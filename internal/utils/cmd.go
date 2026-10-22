package utils

import (
 "bufio"
 "bytes"
 "context"
 "fmt"
 "io"
 "os/exec"
 "strconv"
 "strings"
 "sync"
 "time"
)

const DefaultFFmpegTimeout = 45 * time.Minute

// RunFFmpegWithProgress preserves the existing API, but bounds FFmpeg runtime.
func RunFFmpegWithProgress(log *Logger, totalSeconds int, args ...string) error {
 ctx, cancel := context.WithTimeout(context.Background(), DefaultFFmpegTimeout)
 defer cancel()
 return RunFFmpegWithRetryContext(ctx, log, totalSeconds, args...)
}

// RunFFmpegWithProgressContext runs FFmpeg, drains output streams concurrently,
// propagates cancellation and avoids unbounded stderr memory usage.
func RunFFmpegWithProgressContext(ctx context.Context, log *Logger, totalSeconds int, args ...string) error {
 if err := ctx.Err(); err != nil { return err }
 cmd := exec.CommandContext(ctx, "ffmpeg", args...)
 stdout, err := cmd.StdoutPipe()
 if err != nil { return fmt.Errorf("ffmpeg stdout: %w", err) }
 stderr, err := cmd.StderrPipe()
 if err != nil { return fmt.Errorf("ffmpeg stderr: %w", err) }
 if err := cmd.Start(); err != nil { return fmt.Errorf("start ffmpeg: %w", err) }

 // Keep only the last 64 KiB; FFmpeg's verbose logs can be enormous.
 tail := &boundedLog{max: 64 * 1024}
 var wg sync.WaitGroup
 wg.Add(2)
 var scanErr error
 go func() {
  defer wg.Done()
  _, _ = io.Copy(tail, stderr)
 }()
 go func() {
  defer wg.Done()
  sc := bufio.NewScanner(stdout)
  sc.Buffer(make([]byte, 4096), 1024*1024)
  lastLog := time.Time{}
  lastPct := -1
  for sc.Scan() {
   line := strings.TrimSpace(sc.Text())
   if strings.HasPrefix(line, "out_time_ms=") || strings.HasPrefix(line, "out_time_us=") {
    sep := strings.IndexByte(line, '=')
    us, parseErr := strconv.ParseInt(line[sep+1:], 10, 64)
    if parseErr != nil { continue }
    sec := float64(us) / 1000000
    if time.Since(lastLog) < 700*time.Millisecond { continue }
    lastLog = time.Now()
    if totalSeconds > 0 {
     pct := int(sec / float64(totalSeconds) * 100)
     if pct < 0 { pct = 0 }
     if pct > 100 { pct = 100 }
     if pct != lastPct { lastPct = pct; log.Info(fmt.Sprintf("ffmpeg progress: %d%%", pct)) }
    } else { log.Info(fmt.Sprintf("ffmpeg progress: %.1fs", sec)) }
   }
  }
  scanErr = sc.Err()
 }()
 wg.Wait()
 waitErr := cmd.Wait()
 if err := ctx.Err(); err != nil { return fmt.Errorf("ffmpeg interrupted: %w", err) }
 if waitErr != nil {
  log.Error("FFmpeg failed. Recent stderr:\n" + tail.String())
  return &FFmpegRunError{Cause: waitErr, Stderr: tail.String()}
 }
 if scanErr != nil { return fmt.Errorf("read ffmpeg progress: %w", scanErr) }
 return nil
}

type boundedLog struct {
 mu sync.Mutex
 buf bytes.Buffer
 max int
}
func (b *boundedLog) Write(p []byte) (int, error) {
 b.mu.Lock()
 defer b.mu.Unlock()
 n := len(p)
 if n >= b.max {
  b.buf.Reset()
  _, err := b.buf.Write(p[n-b.max:])
  return n, err
 }
 excess := b.buf.Len() + n - b.max
 if excess > 0 {
  old := b.buf.Bytes()
  remaining := append([]byte(nil), old[excess:]...)
  b.buf.Reset()
  _, _ = b.buf.Write(remaining)
 }
 _, err := b.buf.Write(p)
 return n, err
}
func (b *boundedLog) String() string {
 b.mu.Lock()
 defer b.mu.Unlock()
 return b.buf.String()
}

