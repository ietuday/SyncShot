package stages

import (
 "fmt"
 "os"
 "path/filepath"
 "syncshotgo/internal/utils"
)

// validateRenderedMedia requires a nonempty, probeable MP4 before publishing it.
func validateRenderedMedia(path string) error {
 info, err := os.Stat(path)
 if err != nil { return fmt.Errorf("stat rendered video: %w", err) }
 if info.Size() == 0 { return fmt.Errorf("rendered video is empty: %s",path) }
 duration, err := utils.ProbeDurationSeconds(path)
 if err != nil { return fmt.Errorf("probe rendered video: %w",err) }
 if duration <= 0 { return fmt.Errorf("rendered video duration is invalid: %s",path) }
 return nil
}

// promoteVideo swaps the validated video into place. A backup protects an existing
// output if the rename fails. Both files are created on the same filesystem.
func promoteVideo(tempPath, finalPath string) error {
 if filepath.Dir(tempPath) != filepath.Dir(finalPath) { return fmt.Errorf("temporary video and final video must share a directory") }
 backup := finalPath+".syncshot-backup"
 if _, err := os.Stat(finalPath); err == nil {
  if err := os.Rename(finalPath, backup); err != nil { return fmt.Errorf("backup prior video: %w",err) }
  if err := os.Rename(tempPath, finalPath); err != nil {
   restoreErr := os.Rename(backup,finalPath)
   if restoreErr != nil { return fmt.Errorf("publish video: %v; restore backup: %w",err,restoreErr) }
   return fmt.Errorf("publish video: %w",err)
  }
  _ = os.Remove(backup)
  return nil
 } else if !os.IsNotExist(err) { return err }
 if err := os.Rename(tempPath,finalPath); err != nil { return fmt.Errorf("publish video: %w",err) }
 return nil
}
