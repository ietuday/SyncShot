package stages

import (
 "fmt"
 "os"
 "path/filepath"
 "strings"
)

func PickAudio(dir string) (string, error) {
 files, err := os.ReadDir(dir)
 if err != nil { return "", fmt.Errorf("read audio directory: %w", err) }
 for _, f := range files {
  if f.IsDir() { continue }
  switch strings.ToLower(filepath.Ext(f.Name())) {
  case ".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg":
   return filepath.Join(dir, f.Name()), nil
  }
 }
 return "", fmt.Errorf("no supported audio files in %s", dir)
}
