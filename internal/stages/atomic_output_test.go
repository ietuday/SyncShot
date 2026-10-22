package stages

import (
 "os"
 "path/filepath"
 "testing"
)

func TestPromoteVideoPreservesAndReplacesOutput(t *testing.T) {
 dir := t.TempDir()
 previous := filepath.Join(dir,"final.mp4")
 temp := filepath.Join(dir,".new.mp4")
 if err:=os.WriteFile(previous,[]byte("old"),0600);err!=nil { t.Fatal(err) }
 if err:=os.WriteFile(temp,[]byte("new"),0600);err!=nil { t.Fatal(err) }
 if err:=promoteVideo(temp,previous);err!=nil { t.Fatal(err) }
 got,err:=os.ReadFile(previous)
 if err!=nil || string(got)!="new" { t.Fatalf("result %q %v",got,err) }
 if _,err:=os.Stat(previous+".syncshot-backup"); !os.IsNotExist(err) { t.Fatalf("backup should be gone: %v",err) }
}
func TestPromoteVideoDoesNotRemoveOldOnMissingTemp(t *testing.T) {
 dir:=t.TempDir()
 target:=filepath.Join(dir,"final.mp4")
 if err:=os.WriteFile(target,[]byte("old"),0600);err!=nil { t.Fatal(err) }
 if err:=promoteVideo(filepath.Join(dir,"missing.mp4"),target);err==nil { t.Fatal("expected error") }
 got,err:=os.ReadFile(target)
 if err!=nil || string(got)!="old" { t.Fatalf("old output lost: %q %v",got,err) }
}
