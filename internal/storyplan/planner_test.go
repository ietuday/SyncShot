package storyplan

import (
 "math"
 "testing"
)

func TestBuild(t *testing.T) {
 in:=Input{Audio:"narration.m4a",Duration:30,Segments:[]Segment{{Start:0,End:21,Text:"Shri Ram walks in the forest"},{Start:21,End:30,Text:"He meets a sage"}}}
 p,err:=Build(in,"",8)
 if err!=nil {t.Fatal(err)}
 if p.Style!=DefaultStyle||len(p.Scenes)!=5 {t.Fatalf("unexpected plan: %+v",p)}
 if math.Abs(p.Scenes[2].End-21)>0.0001||p.Scenes[4].End!=30 {t.Fatalf("invalid timeline: %+v",p.Scenes)}
}
func TestInvalid(t *testing.T) {
 base:=Input{Audio:"a.m4a",Duration:10,Segments:[]Segment{{Start:0,End:10,Text:"hello"}}}
 if _,err:=Build(base,"unknown",5);err==nil {t.Fatal("expected invalid style")}
 if _,err:=Build(base,"",math.NaN());err==nil {t.Fatal("expected invalid scene duration")}
 base.Segments=append(base.Segments,Segment{Start:9,End:10,Text:"overlap"})
 if _,err:=Build(base,"",5);err==nil {t.Fatal("expected overlap rejection")}
}
