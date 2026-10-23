package subtitles

import (
 "context"
 "os"
 "path/filepath"
 "strings"
 "testing"
)
const valid = "1\n00:00:00,000 --> 00:00:02,000\nHello world\n\n2\n00:00:02,000 --> 00:00:04,000\nनमस्ते\n"
func TestValidateSRT(t *testing.T) {
 if err:=ValidateSRT([]byte(valid));err!=nil {t.Fatal(err)}
 cases:=[]string{"","1\n00:00:03,000 --> 00:00:02,000\nwrong", "1\n00:00:00,000 --> 00:00:02,000\ncaption\n\n2\n00:00:01,000 --> 00:00:03,000\noverlap", "2\n00:00:00,000 --> 00:00:01,000\nwrong index"}
 for _,c:=range cases {if err:=ValidateSRT([]byte(c));err==nil {t.Errorf("accepted invalid SRT: %q",c)}}
}
func TestPrepareImport(t *testing.T) {
 dir:=t.TempDir()
 src:=filepath.Join(dir,"my captions.srt")
 if err:=os.WriteFile(src,[]byte(valid),0600);err!=nil {t.Fatal(err)}
 out,err:=Prepare(context.Background(),"",src,"import",filepath.Join(dir,"work"))
 if err!=nil {t.Fatal(err)}
 b,err:=os.ReadFile(out);if err!=nil || string(b)!=valid {t.Fatalf("copied captions: %v",err)}
 if _,err:=Prepare(context.Background(),"",strings.TrimSuffix(src,"srt")+"missing","import",dir);err==nil {t.Fatal("expected missing file error")}
}
