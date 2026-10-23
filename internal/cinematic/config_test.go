package cinematic

import (
 "os"
 "path/filepath"
 "strings"
 "testing"
)

func TestLoadTimeline(t *testing.T) {
 dir:=t.TempDir()
 p:=filepath.Join(dir,"timeline.json")
 content:=`{"fps":24,"width":320,"height":180,"crossfade_seconds":0.3,"scenes":[{"image":"a.png","duration":2.3,"motion":"zoom_in"},{"image":"b.png","duration":2,"motion":"pan_left"}]}`
 if err:=os.WriteFile(p,[]byte(content),0600);err!=nil {t.Fatal(err)}
 timeline,err:=LoadTimeline(p)
 if err!=nil {t.Fatal(err)}
 if len(timeline.Scenes)!=2 || timeline.Duration()<3.99 || timeline.Duration()>4.01 {t.Fatalf("invalid timeline: %+v",timeline)}
 if timeline.Scenes[0].Image!=filepath.Join(dir,"a.png") {t.Fatalf("image not resolved: %s",timeline.Scenes[0].Image)}
}
func TestRejectInvalidTimeline(t *testing.T) {
 for _,content:=range []string{
  `{"fps":24,"width":320,"height":180,"unknown":true,"scenes":[{"image":"x","duration":2}]}`,
  `{"fps":24,"width":320,"height":180,"scenes":[{"image":"x","duration":2,"motion":"invalid"}]}`,
  `{} {}`,
 } {
  file:=filepath.Join(t.TempDir(),"timeline.json")
  if err:=os.WriteFile(file,[]byte(content),0600);err!=nil {t.Fatal(err)}
  if _,err:=LoadTimeline(file);err==nil {t.Fatalf("accepted invalid %s",strings.TrimSpace(content))}
 }
}
