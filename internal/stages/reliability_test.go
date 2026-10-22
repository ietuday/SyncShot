package stages

import (
 "os"
 "path/filepath"
 "testing"
)

func TestSceneSeconds(t *testing.T) {
 got, err := SceneSeconds(120, 30, 3)
 if err != nil || got != 4 { t.Fatalf("got %v, %v; want 4", got, err) }
 if _, err := SceneSeconds(12, 0, 3); err == nil { t.Fatal("wanted invalid image count error") }
}
func TestScanImages(t *testing.T) {
 dir := t.TempDir()
 for _, f := range []string{"001.png","note.txt","002.JPG"} {
  if err := os.WriteFile(filepath.Join(dir, f), []byte("x"), 0600); err != nil { t.Fatal(err) }
 }
 if err := os.Mkdir(filepath.Join(dir,"folder.png"),0700); err != nil { t.Fatal(err) }
 got, err := ScanImages(dir)
 if err != nil || len(got) != 2 { t.Fatalf("got %v, %v", got, err) }
}
func TestPickAudio(t *testing.T) {
 dir := t.TempDir()
 if err := os.WriteFile(filepath.Join(dir,".gitkeep"), nil,0600); err != nil { t.Fatal(err) }
 if err := os.WriteFile(filepath.Join(dir,"voice.MP3"), []byte("x"),0600); err != nil { t.Fatal(err) }
 got, err := PickAudio(dir)
 if err != nil || filepath.Base(got)!="voice.MP3" { t.Fatalf("got %q, %v",got,err) }
}
func TestFilterImageFiles(t *testing.T) {
 got := filterImageFiles([]string{"a.PNG","b.txt","c.webp"})
 if len(got) != 2 { t.Fatalf("got %v", got) }
}
