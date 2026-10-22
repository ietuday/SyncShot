package utils

import (
 "context"
 "errors"
 "fmt"
 "strings"
 "time"
)

type FFmpegRunError struct {
 Cause error
 Stderr string
}
func (e *FFmpegRunError) Error() string { return fmt.Sprintf("ffmpeg exited: %v", e.Cause) }
func (e *FFmpegRunError) Unwrap() error { return e.Cause }

// Only known transient system resource failures are retried. Bad input,
// missing codecs, invalid filters, cancellation and timeouts are never retried.
func IsTransientFFmpegError(err error) bool {
 var runErr *FFmpegRunError
 if !errors.As(err,&runErr) { return false }
 s := strings.ToLower(runErr.Stderr)
 return strings.Contains(s,"resource temporarily unavailable") ||
  strings.Contains(s,"device or resource busy")
}

// RunFFmpegWithRetryContext performs at most three total attempts.
// Each attempt reuses the caller's context; cancellation aborts backoff immediately.
func RunFFmpegWithRetryContext(ctx context.Context, log *Logger, totalSeconds int, args ...string) error {
 return retryFFmpeg(ctx, 3, 250*time.Millisecond, func() error {
  return RunFFmpegWithProgressContext(ctx, log, totalSeconds, args...)
 })
}

func retryFFmpeg(ctx context.Context, attempts int, delay time.Duration, run func() error) error {
 if attempts < 1 { return fmt.Errorf("retry attempts must be positive") }
 for i:=0;i<attempts;i++ {
  if err:=ctx.Err(); err!=nil { return err }
  err:=run()
  if err==nil { return nil }
  if ctx.Err()!=nil { return ctx.Err() }
  if !IsTransientFFmpegError(err) || i==attempts-1 { return err }
  timer:=time.NewTimer(delay)
  select {
  case <-ctx.Done():
   if !timer.Stop() { <-timer.C }
   return ctx.Err()
  case <-timer.C:
  }
  delay *= 2
 }
 return nil
}
