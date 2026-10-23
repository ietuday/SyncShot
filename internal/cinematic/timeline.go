package cinematic

import (
 "fmt"
 "math"
 "path/filepath"
 "strings"
)

type Motion string
const (
 Static Motion = "static"
 ZoomIn Motion = "zoom_in"
 ZoomOut Motion = "zoom_out"
 PanLeft Motion = "pan_left"
 PanRight Motion = "pan_right"
)

type Scene struct {
 Image string
 Duration float64
 Motion Motion
}

type Timeline struct {
 Scenes []Scene
 FPS int
 Width int
 Height int
 CrossfadeSeconds float64
}

func (t Timeline) Validate() error {
 if t.FPS < 1 || t.FPS > 120 { return fmt.Errorf("FPS must be 1..120") }
 if t.Width < 2 || t.Height < 2 || t.Width%2 != 0 || t.Height%2 != 0 { return fmt.Errorf("dimensions must be positive even numbers") }
 if len(t.Scenes)==0 { return fmt.Errorf("timeline requires scenes") }
 if !finite(t.CrossfadeSeconds) || t.CrossfadeSeconds<0 { return fmt.Errorf("crossfade must be finite and nonnegative") }
 for i,s := range t.Scenes {
  if s.Image=="" { return fmt.Errorf("scene %d missing image",i) }
  if !finite(s.Duration) || s.Duration<=0 { return fmt.Errorf("scene %d duration must be positive",i) }
  switch s.Motion {
  case "",Static,ZoomIn,ZoomOut,PanLeft,PanRight:
  default: return fmt.Errorf("scene %d invalid motion %q",i,s.Motion)
  }
  if len(t.Scenes)>1 && t.CrossfadeSeconds>0 && s.Duration<=t.CrossfadeSeconds {
   return fmt.Errorf("scene %d must be longer than crossfade",i)
  }
 }
 return nil
}

func finite(v float64) bool { return !math.IsNaN(v) && !math.IsInf(v,0) }

// Duration returns the composited visual runtime.
func (t Timeline) Duration() float64 {
 sum:=0.0
 for _,s:=range t.Scenes { sum+=s.Duration }
 if len(t.Scenes)>1 { sum-=float64(len(t.Scenes)-1)*t.CrossfadeSeconds }
 return sum
}

// FromImages builds a narration-aligned timeline using equal-duration scenes.
// Each scene includes its outgoing overlap except the final scene.
func FromImages(images []string, narrationSeconds float64, fps,width,height int, fade float64, motion Motion) (Timeline,error) {
 if len(images)==0 || !finite(narrationSeconds) || narrationSeconds<=0 { return Timeline{},fmt.Errorf("images and positive narration duration required") }
 if !finite(fade) || fade<0 { return Timeline{},fmt.Errorf("invalid crossfade") }
 base:=narrationSeconds/float64(len(images))
 if len(images)>1 && fade>=base { return Timeline{},fmt.Errorf("crossfade must be less than narration per image") }
 scenes:=make([]Scene,len(images))
 for i,img:=range images {
  duration:=base
  if i<len(images)-1 { duration+=fade }
  scenes[i]=Scene{Image:img,Duration:duration,Motion:motion}
 }
 t:=Timeline{Scenes:scenes,FPS:fps,Width:width,Height:height,CrossfadeSeconds:fade}
 if err:=t.Validate();err!=nil { return Timeline{},err }
 return t,nil
}

// BuildFilter constructs explicit Ken Burns and xfade graphs, using frame-based
// scene lengths to avoid timebase drift across still-image input streams.
func (t Timeline) BuildFilter() (string,string,error) {
 if err:=t.Validate();err!=nil {return "","",err}
 parts:=make([]string,0,len(t.Scenes)*2)
 accumulated:=0.0
 for i,s:=range t.Scenes {
  frames:=int(math.Ceil(s.Duration*float64(t.FPS)))
  w,h:=t.Width,t.Height
  motion:=s.Motion
  if motion=="" {motion=Static}
  var filter string
  switch motion {
  case Static:
   filter=fmt.Sprintf("[%d:v]fps=%d,scale=%d:%d:force_original_aspect_ratio=decrease,pad=%d:%d:(ow-iw)/2:(oh-ih)/2,setsar=1,trim=end_frame=%d,setpts=PTS-STARTPTS,fps=%d,settb=AVTB,format=yuv420p[s%d]",i,t.FPS,w,h,w,h,frames,t.FPS,i)
  default:
   // Crop from an oversized, letterboxed canvas. All expressions are generated
   // from known enum values and integer dimensions; no user-supplied filter text.
   sw,sh:=2*int(math.Ceil(float64(w)*1.12/2)),2*int(math.Ceil(float64(h)*1.12/2))
   x,y,z:="(iw-iw/zoom)/2","(ih-ih/zoom)/2","min(zoom+0.0004,1.10)"
   switch motion {
   case ZoomOut: z="max(1.10-on*0.0004,1.0)"
   case PanLeft: z="1.10";x="(iw-iw/zoom)*(1-min(on/"+fmt.Sprintf("%d",max(1,frames-1))+",1))"
   case PanRight: z="1.10";x="(iw-iw/zoom)*min(on/"+fmt.Sprintf("%d",max(1,frames-1))+",1)"
   }
   filter=fmt.Sprintf("[%d:v]scale=%d:%d:force_original_aspect_ratio=decrease:force_divisible_by=2,pad=%d:%d:(ow-iw)/2:(oh-ih)/2,zoompan=z='%s':x='%s':y='%s':d=1:s=%dx%d:fps=%d,trim=end_frame=%d,setpts=PTS-STARTPTS,format=yuv420p[s%d]",i,sw,sh,sw,sh,z,x,y,w,h,t.FPS,frames,i)
  }
  parts=append(parts,filter)
  if i==0 {
   accumulated=s.Duration
   continue
  }
  fade:=t.CrossfadeSeconds
  if fade==0 {continue}
  offset:=accumulated-fade
  first:=fmt.Sprintf("s%d",i-1)
  if i>1 { first=fmt.Sprintf("x%d",i-1) }
  parts=append(parts,fmt.Sprintf("[%s][s%d]xfade=transition=fade:duration=%.6f:offset=%.6f[x%d]",first,i,fade,offset,i))
  accumulated+=s.Duration-fade
 }
 if len(t.Scenes)==1 {return strings.Join(parts,";"),"[s0]",nil}
 if t.CrossfadeSeconds==0 {
  var refs strings.Builder
  for i:=range t.Scenes {fmt.Fprintf(&refs,"[s%d]",i)}
  parts=append(parts,fmt.Sprintf("%sconcat=n=%d:v=1:a=0[outv]",refs.String(),len(t.Scenes)))
  return strings.Join(parts,";"),"[outv]",nil
 }
 return strings.Join(parts,";"),fmt.Sprintf("[x%d]",len(t.Scenes)-1),nil
}

func (t Timeline) InputPaths() []string {
 paths:=make([]string,len(t.Scenes))
 for i,s:=range t.Scenes {paths[i]=filepath.Clean(s.Image)}
 return paths
}
