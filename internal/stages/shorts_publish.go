package stages

import (
 "fmt"
 "os"
 "path/filepath"
)

// publishShortsDirectory replaces a completed Shorts batch. Both staging and
// destination directories must share a parent filesystem. A backup provides
// rollback when publishing fails, but this is not a crash-atomic transaction.
func publishShortsDirectory(stageDir, destination string) error {
 stageParent, err := filepath.Abs(filepath.Dir(stageDir))
 if err != nil { return err }
 destParent, err := filepath.Abs(filepath.Dir(destination))
 if err != nil { return err }
 if stageParent != destParent { return fmt.Errorf("Shorts staging and destination must share a parent directory") }
 if err := os.MkdirAll(destParent, 0755); err != nil { return err }
 backup := destination+".syncshot-backup"
 if _, err := os.Stat(backup); err == nil {
  return fmt.Errorf("existing Shorts backup requires recovery: %s",backup)
 } else if !os.IsNotExist(err) { return err }
 oldExists := false
 if _, err := os.Stat(destination); err == nil {
  oldExists = true
  if err := os.Rename(destination,backup); err != nil { return fmt.Errorf("backup previous Shorts: %w",err) }
 } else if !os.IsNotExist(err) { return err }
 if err := os.Rename(stageDir,destination); err != nil {
  if oldExists {
   if restoreErr := os.Rename(backup,destination); restoreErr != nil {
    return fmt.Errorf("publish Shorts: %v; restore backup: %w",err,restoreErr)
   }
  }
  return fmt.Errorf("publish Shorts: %w",err)
 }
 if oldExists {
  if err := os.RemoveAll(backup); err != nil { return fmt.Errorf("published Shorts but could not remove backup %s: %w",backup,err) }
 }
 return nil
}
