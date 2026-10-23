package cinematic

import (
 "fmt"
 "math"
)

// PlanScenes creates a narration-length timeline. Images are rotated in input
// order when there are fewer images than scenes. It does not infer story content.
func PlanScenes(images []string, narrationSeconds float64, fps, width, height int, fade float64, motion Motion, targetSceneSeconds float64) (Timeline, error) {
 if len(images)==0 || !finite(narrationSeconds) || narrationSeconds<=0 {return Timeline{},fmt.Errorf("positive narration and at least one image required")}
 if !finite(targetSceneSeconds) || targetSceneSeconds<=0 {return Timeline{},fmt.Errorf("target scene duration must be finite and positive")}
 if !finite(fade) || fade<0 {return Timeline{},fmt.Errorf("crossfade must be finite and nonnegative")}
 if fps<1 || fps>120 {return Timeline{},fmt.Errorf("fps must be 1..120")}
 // The number of scenes is limited by available narration frames so that all
 // scenes have a nonzero visible interval even for very short narration.
 frames:=int(math.Round(narrationSeconds*float64(fps)))
 if frames<1 {return Timeline{},fmt.Errorf("narration shorter than one video frame")}
 count:=int(math.Ceil(narrationSeconds/targetSceneSeconds))
 if count<1 {count=1}
 if count>frames {count=frames}
 // Ensure every scene is longer than its fade overlap.
 for count>1 && narrationSeconds/float64(count)<=fade+1.0/float64(fps) {count--}
 // Allocate whole output frames among scenes, avoiding floating-point gaps.
 base:=frames/count
 remainder:=frames%count
 scenes:=make([]Scene,count)
 for i:=range scenes {
  visibleFrames:=base
  if i<remainder {visibleFrames++}
  seconds:=float64(visibleFrames)/float64(fps)
  if i<count-1 {seconds+=fade}
  scenes[i]=Scene{Image:images[i%len(images)],Duration:seconds,Motion:motion}
 }
 timeline:=Timeline{Scenes:scenes,FPS:fps,Width:width,Height:height,CrossfadeSeconds:fade}
 if err:=timeline.Validate();err!=nil {return Timeline{},err}
 return timeline,nil
}
