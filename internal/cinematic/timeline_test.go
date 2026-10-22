package cinematic

import (
 "math"
 "strings"
 "testing"
)

func TestNarrationAlignedTimeline(t *testing.T) {
 p,err:=FromImages([]string{"a.jpg","b.jpg","c.jpg"},12,24,1920,1080,0.5,ZoomIn)
 if err!=nil {t.Fatal(err)}
 if math.Abs(p.Duration()-12)>1e-6 {t.Fatalf("duration=%f",p.Duration())}
 if math.Abs(p.Scenes[0].Duration-4.5)>1e-6 || math.Abs(p.Scenes[2].Duration-4)>1e-6 {t.Fatalf("%+v",p.Scenes)}
 graph,label,err:=p.BuildFilter()
 if err!=nil {t.Fatal(err)}
 if label!="[x2]" || strings.Count(graph,"xfade=")!=2 || !strings.Contains(graph,"zoompan=") {t.Fatalf("unexpected graph %s %s",label,graph)}
}
func TestSingleSceneAndHardCuts(t *testing.T) {
 p,err:=FromImages([]string{"one.jpg"},3,24,320,180,0,Static)
 if err!=nil {t.Fatal(err)}
 _,label,err:=p.BuildFilter()
 if err!=nil || label!="[s0]" {t.Fatalf("%v %s",err,label)}
 p,err=FromImages([]string{"a.jpg","b.jpg"},5,24,320,180,0,Static)
 if err!=nil {t.Fatal(err)}
 graph,label,err:=p.BuildFilter()
 if err!=nil || label!="[outv]" || !strings.Contains(graph,"concat=n=2") {t.Fatalf("%v %s",err,graph)}
}
func TestInvalidScenes(t *testing.T) {
 cases:=[]Timeline{
  {FPS:0,Width:320,Height:180,Scenes:[]Scene{{Image:"a",Duration:3}}},
  {FPS:24,Width:321,Height:180,Scenes:[]Scene{{Image:"a",Duration:3}}},
  {FPS:24,Width:320,Height:180,CrossfadeSeconds:2,Scenes:[]Scene{{Image:"a",Duration:2},{Image:"b",Duration:3}}},
  {FPS:24,Width:320,Height:180,Scenes:[]Scene{{Image:"a",Duration:3,Motion:"rawfilter"}}},
 }
 for i,p:=range cases {if err:=p.Validate();err==nil {t.Fatalf("case %d accepted",i)}}
 if _,err:=FromImages([]string{"a","b"},4,24,320,180,2,ZoomIn);err==nil {t.Fatal("invalid fade accepted")}
}
