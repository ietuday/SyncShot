package pipeline

import (
 "os"
 "path/filepath"
 "testing"
)

func TestRunLockExcludesConcurrentRun(t *testing.T) {
 work:=filepath.Join(t.TempDir(),"work")
 release,err:=acquireRunLock(work)
 if err!=nil {t.Fatal(err)}
 if _,err:=acquireRunLock(work);err==nil {t.Fatal("expected concurrent run rejection")}
 if err:=release();err!=nil {t.Fatal(err)}
 release2,err:=acquireRunLock(work)
 if err!=nil {t.Fatal(err)}
 if err:=release2();err!=nil {t.Fatal(err)}
}
func TestRunLockPreservesStaleLock(t *testing.T) {
 parent:=t.TempDir()
 work:=filepath.Join(parent,"work")
 path:=filepath.Join(parent,".work.syncshot.lock")
 if err:=os.WriteFile(path,[]byte("pid=123\n"),0600);err!=nil {t.Fatal(err)}
 if _,err:=acquireRunLock(work);err==nil {t.Fatal("expected stale lock error")}
 data,err:=os.ReadFile(path)
 if err!=nil || string(data)!="pid=123\n" {t.Fatalf("lock modified: %q %v",data,err)}
}
