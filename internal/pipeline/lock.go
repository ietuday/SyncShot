package pipeline

import (
 "errors"
 "fmt"
 "os"
 "path/filepath"
)

// acquireRunLock prevents multiple SyncShot runs targeting the same work directory.
// A lock left after a crash is intentionally not removed automatically: automated
// stale-lock deletion can race with a live publisher on another host.
func acquireRunLock(workDir string) (func() error, error) {
 parent, err := filepath.Abs(filepath.Dir(workDir))
 if err != nil { return nil, err }
 if err := os.MkdirAll(parent, 0755); err != nil { return nil, err }
 lockPath := filepath.Join(parent, "."+filepath.Base(workDir)+".syncshot.lock")
 file, err := os.OpenFile(lockPath, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
 if errors.Is(err, os.ErrExist) {
  return nil, fmt.Errorf("another run or stale lock exists at %s; verify no SyncShot process is running before removing it: %w", lockPath, err)
 }
 if err != nil { return nil, fmt.Errorf("create run lock: %w", err) }
 if _, err := fmt.Fprintf(file, "pid=%d\n", os.Getpid()); err != nil {
  _ = file.Close()
  _ = os.Remove(lockPath)
  return nil, err
 }
 ownedInfo, statErr := file.Stat()
 if statErr != nil { _ = file.Close(); _ = os.Remove(lockPath); return nil, statErr }
 if err := file.Close(); err != nil {
  _ = os.Remove(lockPath)
  return nil, err
 }
 return func() error {
  current, err := os.Lstat(lockPath)
  if err != nil { return err }
  if !os.SameFile(ownedInfo,current) { return fmt.Errorf("lock ownership changed; refusing removal: %s",lockPath) }
  return os.Remove(lockPath)
 }, nil
}
