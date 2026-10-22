package stages

import (
 "os"
 "path/filepath"
 "testing"
)

func TestPublishShortsDirectory(t *testing.T) {
 root:=t.TempDir()
 dest:=filepath.Join(root,"shorts")
 stage:=filepath.Join(root,".staging")
 if err:=os.MkdirAll(dest,0755);err!=nil { t.Fatal(err) }
 if err:=os.WriteFile(filepath.Join(dest,"old.mp4"),[]byte("old"),0600);err!=nil { t.Fatal(err) }
 if err:=os.MkdirAll(stage,0755);err!=nil { t.Fatal(err) }
 if err:=os.WriteFile(filepath.Join(stage,"new.mp4"),[]byte("new"),0600);err!=nil { t.Fatal(err) }
 if err:=publishShortsDirectory(stage,dest);err!=nil { t.Fatal(err) }
 if b,err:=os.ReadFile(filepath.Join(dest,"new.mp4"));err!=nil || string(b)!="new" { t.Fatalf("new Shorts missing: %s %v",b,err) }
 if _,err:=os.Stat(filepath.Join(dest,"old.mp4"));!os.IsNotExist(err) { t.Fatalf("stale clip retained: %v",err) }
 if _,err:=os.Stat(dest+".syncshot-backup");!os.IsNotExist(err) { t.Fatalf("backup still exists: %v",err) }
}

func TestPublishShortsDirectoryRejectsExistingBackup(t *testing.T) {
 root:=t.TempDir()
 dest:=filepath.Join(root,"shorts")
 stage:=filepath.Join(root,"stage")
 if err:=os.MkdirAll(dest,0755);err!=nil { t.Fatal(err) }
 if err:=os.MkdirAll(stage,0755);err!=nil { t.Fatal(err) }
 if err:=os.MkdirAll(dest+".syncshot-backup",0755);err!=nil { t.Fatal(err) }
 if err:=publishShortsDirectory(stage,dest);err==nil { t.Fatal("expected error on existing backup") }
 if _,err:=os.Stat(dest);err!=nil { t.Fatalf("destination changed: %v",err) }
}
