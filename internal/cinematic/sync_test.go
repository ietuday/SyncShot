package cinematic

import (
 "strings"
 "testing"
)

func TestValidateNarrationSync(t *testing.T) {
 timeline,err:=FromImages([]string{"a.png","b.png"},3.25,24,320,180,0.4,ZoomIn)
 if err!=nil {t.Fatal(err)}
 if err:=timeline.ValidateNarrationSync(3.25);err!=nil {t.Fatalf("valid timeline: %v",err)}
 if err:=timeline.ValidateNarrationSync(3.27);err!=nil {t.Fatalf("within-frame tolerance: %v",err)}
 if err:=timeline.ValidateNarrationSync(4);err==nil || !strings.Contains(err.Error(),"differs") {t.Fatalf("expected mismatch: %v",err)}
 if err:=timeline.ValidateNarrationSync(0);err==nil {t.Fatal("expected invalid duration")}
}
