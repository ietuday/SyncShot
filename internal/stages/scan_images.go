package stages

import (
 "fmt"
 "os"
 "path/filepath"
 "strings"
)

func ScanImages(dir string) ([]string, error) {
 entries, err := os.ReadDir(dir)
 if err != nil { return nil, fmt.Errorf("read images directory: %w", err) }
 images := make([]string, 0, len(entries))
 for _, entry := range entries {
  if entry.IsDir() { continue }
  switch strings.ToLower(filepath.Ext(entry.Name())) {
  case ".jpg", ".jpeg", ".png", ".webp", ".bmp":
   images = append(images, filepath.Join(dir, entry.Name()))
  }
 }
 if len(images) == 0 { return nil, fmt.Errorf("no supported images in %s", dir) }
 return images, nil
}
