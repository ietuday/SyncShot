package pipeline

import (
 "context"
 "errors"
 "testing"
 "syncshotgo/internal/utils"
)

func TestRunContextAlreadyCanceled(t *testing.T) {
 ctx, cancel := context.WithCancel(context.Background())
 cancel()
 err := RunContext(ctx, utils.NewLogger(), Config{})
 if !errors.Is(err, context.Canceled) {
  t.Fatalf("expected context.Canceled, got %v", err)
 }
}
