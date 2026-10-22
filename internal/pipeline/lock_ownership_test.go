package pipeline

import (
 "os"
 "path/filepath"
 "testing"
)

func TestLockCannotBeReleasedTwiceWithoutError(t *testing.T) {
 work:=filepath.Join(t.TempDir(),"work")
 release,err:=acquireRunLock(work)
 if err!=nil { t.Fatal(err) }
 if err:=release();err!=nil {t.Fatal(err)}
 // The lock is absent and subsequent acquisition remains possible.
 again,err:=acquireRunLock(work)
 if err!=nil {t.Fatal(err)}
 if err:=again();err!=nil {t.Fatal(err)}
}
func TestLockLeftByCrashIsNotAutomaticallyOverwritten(t *testing.T) {
 dir:=t.TempDir()
 p:=filepath.Join(dir,".work.syncshot.lock")
 if err:=os.WriteFile(p,[]byte("pid=99999999\n"),0600);err!=nil {t.Fatal(err)}
 if _,err:=acquireRunLock(filepath.Join(dir,"work"));err==nil {t.Fatal("expected stale lock block")}
}
