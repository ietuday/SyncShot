package stages

import (
 "os"
 "path/filepath"
 "strings"
 "testing"
)

func TestRecoverRestoresMissingFinal(t *testing.T) {
 dir:=t.TempDir()
 final:=filepath.Join(dir,"final.mp4")
 if err:=os.WriteFile(final+".syncshot-backup",[]byte("previous"),0600);err!=nil {t.Fatal(err)}
 if err:=recoverPublishedPath(final);err!=nil {t.Fatal(err)}
 b,err:=os.ReadFile(final)
 if err!=nil || string(b)!="previous" {t.Fatalf("output %q, %v",b,err)}
}
func TestRecoverRefusesAmbiguousState(t *testing.T) {
 dir:=t.TempDir()
 final:=filepath.Join(dir,"shorts")
 if err:=os.Mkdir(final,0700);err!=nil {t.Fatal(err)}
 if err:=os.Mkdir(final+".syncshot-backup",0700);err!=nil {t.Fatal(err)}
 if err:=recoverPublishedPath(final);err==nil || !strings.Contains(err.Error(),"manual recovery") {t.Fatalf("expected refusal, got %v",err)}
 for _,p:=range []string{final,final+".syncshot-backup"} {if _,err:=os.Stat(p);err!=nil {t.Fatal(err)}}
}
func TestRecoverNoBackup(t *testing.T) {
 if err:=recoverPublishedPath(filepath.Join(t.TempDir(),"missing"));err!=nil {t.Fatal(err)}
}
