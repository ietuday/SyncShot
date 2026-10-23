package stages

import (
 "math"
 "strings"
 "testing"
)

func TestPlanSmartShorts(t *testing.T) {
 cases:=[]struct{name string;total float64;max int;scene float64;durations []float64}{
  {"fixed",125,50,0,[]float64{50,50,25}},
  {"scene aligned",125,50,30,[]float64{30,30,30,35}},
  {"short video",8,50,30,[]float64{8}},
  {"exact boundary",90,30,30,[]float64{30,30,30}},
 }
 for _,tc:=range cases {t.Run(tc.name,func(t *testing.T){
  segments,err:=PlanSmartShorts(tc.total,tc.max,tc.scene)
  if err!=nil {t.Fatal(err)}
  if len(segments)!=len(tc.durations){t.Fatalf("count=%d expected %d (%+v)",len(segments),len(tc.durations),segments)}
  elapsed:=0.0
  for i,segment:=range segments {
   if math.Abs(segment.Start-elapsed)>0.000001 {t.Fatalf("segment %d is not contiguous",i)}
   if math.Abs(segment.Duration-tc.durations[i])>0.000001 {t.Fatalf("segment %d duration=%v wanted %v",i,segment.Duration,tc.durations[i])}
   if segment.Duration>float64(tc.max)+0.000001{t.Fatalf("segment too long %v",segment.Duration)}
   elapsed+=segment.Duration
  }
  if math.Abs(elapsed-tc.total)>0.000001{t.Fatalf("duration total=%v",elapsed)}
 })}
}

func TestPlanSmartShortsRejectsInvalid(t *testing.T) {
 for _,tc:=range []struct{duration float64;max int;scene float64}{
  {0,30,0},{math.NaN(),30,0},{math.Inf(1),30,0},{10,0,0},{10,30,-1},{10,30,math.NaN()},
 } {
  if _,err:=PlanSmartShorts(tc.duration,tc.max,tc.scene);err==nil {t.Fatalf("accepted invalid %+v",tc)}
 }
}

func TestSmartCropFilter(t *testing.T) {
 for mode,want:=range map[string]string{"center":"(in_w-1080)/2","left":"crop=1080:1920:0:","right":"crop=1080:1920:in_w-1080:","pan":"zoompan="} {
  got,err:=SmartCropFilter(mode)
  if err!=nil || !strings.Contains(got,want){t.Fatalf("mode=%s got %q error=%v",mode,got,err)}
 }
 if _,err:=SmartCropFilter("face_ai");err==nil{t.Fatal("invalid crop mode accepted")}
}
