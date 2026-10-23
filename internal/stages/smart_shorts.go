package stages

import (
 "fmt"
 "math"
)

// ShortSegment is a half-open source interval in seconds.
type ShortSegment struct { Start, Duration float64 }

// PlanSmartShorts divides a video into clips no longer than maxSeconds.
// When sceneSeconds is positive, it prefers a scene boundary near the target
// duration; very small tail clips are folded into previous clips when possible.
func PlanSmartShorts(totalSeconds float64, maxSeconds int, sceneSeconds float64) ([]ShortSegment,error) {
 if math.IsNaN(totalSeconds)||math.IsInf(totalSeconds,0)||totalSeconds<=0{return nil,fmt.Errorf("video duration must be positive and finite")}
 if maxSeconds<1{return nil,fmt.Errorf("Shorts duration must be positive")}
 if math.IsNaN(sceneSeconds)||math.IsInf(sceneSeconds,0)||sceneSeconds<0{return nil,fmt.Errorf("scene duration must be finite and nonnegative")}
 var clips []ShortSegment
 for start:=0.0;start<totalSeconds-0.00001; {
  end:=math.Min(totalSeconds,start+float64(maxSeconds))
  if sceneSeconds>0 && end<totalSeconds {
   boundary:=math.Floor((end+0.000001)/sceneSeconds)*sceneSeconds
   // Do not make a tiny clip just to match a scene boundary.
   if boundary-start>=float64(maxSeconds)*0.60 && boundary>start {end=boundary}
  }
  if end<=start{return nil,fmt.Errorf("unable to advance Shorts planning")}
  clips=append(clips,ShortSegment{Start:start,Duration:end-start})
  start=end
  if len(clips)>100000{return nil,fmt.Errorf("too many Shorts")}
 }
 return clips,nil
}

// SmartCropFilter chooses a portrait crop and preserves aspect ratio.
// 'pan' keeps the existing animated central crop behavior.
func SmartCropFilter(mode string) (string,error) {
 pos:="(in_w-1080)/2"
 switch mode {
 case "","center": 
 case "left":pos="0"
 case "right":pos="in_w-1080"
 case "pan":
  return "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920:(in_w-1080)/2:(in_h-1920)/2,zoompan=z='min(zoom+0.0005,1.1)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=24[v]",nil
 default:return "",fmt.Errorf("invalid portrait crop mode %q",mode)
 }
 return "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920:"+pos+":(in_h-1920)/2[v]",nil
}
