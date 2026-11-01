package storyplan

import (
 "fmt"
 "math"
 "strings"
)

type Segment struct {
 Start float64 `json:"start"`
 End float64 `json:"end"`
 Text string `json:"text"`
}
type Input struct {
 Audio string `json:"audio"`
 Duration float64 `json:"duration_seconds"`
 Segments []Segment `json:"segments"`
}
type Scene struct {
 Index int `json:"index"`
 Start float64 `json:"start"`
 End float64 `json:"end"`
 Narration string `json:"narration"`
 VisualPrompt string `json:"visual_prompt"`
 AnimationStyle string `json:"animation_style"`
}
type Plan struct {
 Version int `json:"version"`
 Audio string `json:"audio"`
 Duration float64 `json:"duration_seconds"`
 Style string `json:"style"`
 Scenes []Scene `json:"scenes"`
}

const DefaultStyle = "mythological_3d"
func ValidStyle(s string) bool {
 switch s {case "mythological_3d", "cartoon_2d", "cinematic_realistic": return true}
 return false
}
func finite(x float64) bool { return !math.IsNaN(x) && !math.IsInf(x,0) }

// Build creates narration-timed scene prompts from an existing timestamped transcript.
// This is deterministic planning, not transcription or generated animation.
func Build(in Input, style string, maxSceneSeconds float64) (Plan,error) {
 if style=="" {style=DefaultStyle}
 if !ValidStyle(style) {return Plan{},fmt.Errorf("unsupported animation style %q",style)}
 if !finite(in.Duration)||in.Duration<=0 {return Plan{},fmt.Errorf("duration_seconds must be positive and finite")}
 if !finite(maxSceneSeconds)||maxSceneSeconds<=0 {return Plan{},fmt.Errorf("max scene seconds must be positive and finite")}
 if strings.TrimSpace(in.Audio)=="" {return Plan{},fmt.Errorf("audio path required")}
 if len(in.Segments)==0 {return Plan{},fmt.Errorf("timestamped transcript segments required")}
 plan:=Plan{Version:1,Audio:in.Audio,Duration:in.Duration,Style:style}
 previous:=0.0
 for i,seg:=range in.Segments {
  if !finite(seg.Start)||!finite(seg.End)||seg.Start<0||seg.Start>=seg.End||seg.End>in.Duration+0.001 {
   return Plan{},fmt.Errorf("segment %d has invalid timestamps",i)
  }
  if seg.Start<previous-0.001 {return Plan{},fmt.Errorf("segment %d overlaps or is out of order",i)}
  if strings.TrimSpace(seg.Text)=="" {return Plan{},fmt.Errorf("segment %d has empty narration",i)}
  previous=seg.End
  count:=int(math.Ceil((seg.End-seg.Start)/maxSceneSeconds))
  if count>10000||len(plan.Scenes)+count>10000 {return Plan{},fmt.Errorf("scene count exceeds 10000")}
  for n:=0;n<count;n++ {
   start:=seg.Start+float64(n)*(seg.End-seg.Start)/float64(count)
   end:=seg.Start+float64(n+1)*(seg.End-seg.Start)/float64(count)
   text:=strings.TrimSpace(seg.Text)
   prompt:=fmt.Sprintf("%s animation, consistent characters and setting, visually depict this narration: %s. No on-screen text.",strings.ReplaceAll(style,"_"," "),text)
   plan.Scenes=append(plan.Scenes,Scene{Index:len(plan.Scenes)+1,Start:start,End:end,Narration:text,VisualPrompt:prompt,AnimationStyle:style})
  }
 }
 return plan,nil
}
