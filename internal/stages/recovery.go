package stages

import (
 "fmt"
 "os"
)

// recoverPublishedPath restores a backup left by an interrupted rename sequence.
// If both paths exist, it refuses to guess which is valid and preserves both.
// Call only when no other publisher is operating on these paths.
func recoverPublishedPath(destination string) error {
 backup := destination + ".syncshot-backup"
 _, backupErr := os.Lstat(backup)
 if os.IsNotExist(backupErr) { return nil }
 if backupErr != nil { return fmt.Errorf("inspect backup: %w", backupErr) }
 _, currentErr := os.Lstat(destination)
 if currentErr == nil {
  return fmt.Errorf("both output and backup exist; manual recovery required: %s, %s",destination,backup)
 }
 if !os.IsNotExist(currentErr) { return fmt.Errorf("inspect output: %w",currentErr) }
 if err := os.Rename(backup,destination); err != nil {
  return fmt.Errorf("restore previous output: %w",err)
 }
 return nil
}
