package cinematic

import (
 "bytes"
 "encoding/json"
 "fmt"
 "os"
 "path/filepath"
)

// LoadTimeline loads an explicitly authored scene timeline. Relative image paths
// are resolved against the JSON file directory; unknown keys are rejected.
func LoadTimeline(path string) (Timeline,error) {
 raw,err:=os.ReadFile(path)
 if err!=nil {return Timeline{},fmt.Errorf("read timeline: %w",err)}
 var doc struct {
  Scenes []struct {
   Image string `json:"image"`
   Duration float64 `json:"duration"`
   Motion Motion `json:"motion"`
  } `json:"scenes"`
  FPS int `json:"fps"`
  Width int `json:"width"`
  Height int `json:"height"`
  CrossfadeSeconds float64 `json:"crossfade_seconds"`
 }
 decoder:=json.NewDecoder(bytes.NewReader(raw))
 decoder.DisallowUnknownFields()
 if err:=decoder.Decode(&doc);err!=nil {return Timeline{},fmt.Errorf("decode timeline: %w",err)}
 var trailing any
 if err:=decoder.Decode(&trailing);err==nil {return Timeline{},fmt.Errorf("multiple JSON values in timeline")} else if err.Error()!="EOF" {return Timeline{},fmt.Errorf("trailing JSON: %w",err)}
 base,err:=filepath.Abs(filepath.Dir(path))
 if err!=nil {return Timeline{},err}
 t:=Timeline{FPS:doc.FPS,Width:doc.Width,Height:doc.Height,CrossfadeSeconds:doc.CrossfadeSeconds}
 for _,scene:=range doc.Scenes {
  image:=scene.Image
  if image!="" && !filepath.IsAbs(image) {image=filepath.Join(base,image)}
  t.Scenes=append(t.Scenes,Scene{Image:image,Duration:scene.Duration,Motion:scene.Motion})
 }
 if err:=t.Validate();err!=nil {return Timeline{},err}
 return t,nil
}
