package cinematic

import (
 "math"
 "testing"
)

func TestPlanScenes(t *testing.T) {
 cases:=[]struct{name string;images []string;seconds,scene,fade float64;want int}{
  {"long single image",[]string{"a.jpg"},120,30,.5,4},
  {"multiple images",[]string{"a.jpg","b.jpg"},65,30,.5,3},
  {"short narration",[]string{"a.jpg"},.12,30,.5,1},
  {"fade limits number of scenes",[]string{"a.jpg"},1,0.1,.5,1},
 }
 for _,tc:=range cases {t.Run(tc.name,func(t *testing.T){
  got,err:=PlanScenes(tc.images,tc.seconds,24,1920,1080,tc.fade,ZoomIn,tc.scene)
  if err!=nil {t.Fatal(err)}
  if len(got.Scenes)!=tc.want {t.Fatalf("scenes=%d want=%d",len(got.Scenes),tc.want)}
  if math.Abs(got.Duration()-tc.seconds)>1.0/24+.00001 {t.Fatalf("duration=%f want=%f",got.Duration(),tc.seconds)}
  for i,s:=range got.Scenes {if s.Image!=tc.images[i%len(tc.images)] {t.Fatalf("image[%d]=%q",i,s.Image)}}
 })}
}

func TestPlanScenesRejectsInvalid(t *testing.T) {
 for _,tc:=range []struct{images []string;seconds,scene,fade float64}{
  {nil,5,2,.5}, {[]string{"a"},0,2,.5},{[]string{"a"},10,0,.5},{[]string{"a"},10,2,-1},
  {[]string{"a"},math.NaN(),2,.5},{[]string{"a"},10,math.Inf(1),.5},
 } {
  if _,err:=PlanScenes(tc.images,tc.seconds,24,1920,1080,tc.fade,Static,tc.scene);err==nil {t.Fatalf("accepted invalid plan: %+v",tc)}
 }
}
