package utils

import (
 "context"
 "errors"
 "fmt"
 "testing"
 "time"
)

func TestRetryTransientFailure(t *testing.T) {
 calls:=0
 err:=retryFFmpeg(context.Background(),3,0,func() error {
  calls++
  if calls<3 { return &FFmpegRunError{Cause:fmt.Errorf("exit 1"),Stderr:"Resource temporarily unavailable"} }
  return nil
 })
 if err!=nil || calls!=3 { t.Fatalf("got error %v and %d calls",err,calls) }
}
func TestNoRetryOnPermanentFailure(t *testing.T) {
 calls:=0
 err:=retryFFmpeg(context.Background(),3,0,func() error {
  calls++
  return &FFmpegRunError{Cause:fmt.Errorf("exit 1"),Stderr:"Invalid argument"}
 })
 if err==nil || calls!=1 { t.Fatalf("got error %v and %d calls",err,calls) }
}
func TestBackoffCancellation(t *testing.T) {
 ctx,cancel:=context.WithCancel(context.Background())
 calls:=0
 go func(){ time.Sleep(15*time.Millisecond); cancel() }()
 err:=retryFFmpeg(ctx,3,time.Second,func() error {
  calls++
  return &FFmpegRunError{Cause:fmt.Errorf("exit 1"),Stderr:"Device or resource busy"}
 })
 if !errors.Is(err,context.Canceled) || calls!=1 { t.Fatalf("got %v and %d calls",err,calls) }
}
