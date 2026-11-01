package pipeline

import (
 "os"
 "path/filepath"
 "strings"
 "testing"
)

func TestDiskPreflightRejectsImpossibleRequirement(t *testing.T) {
 if err:=ensureFreeDiskSpace(t.TempDir(),filepath.Join(t.TempDir(),"out.mp4"),0);err!=nil{t.Fatal(err)}
}

func TestDiskPreflightMissingDirectories(t *testing.T) {
 root:=t.TempDir()
 work:=filepath.Join(root,"work","nested")
 output:=filepath.Join(root,"video","final.mp4")
 if err:=ensureFreeDiskSpace(work,output,0);err!=nil{t.Fatal(err)}
 if _,err:=os.Stat(work);err!=nil{t.Fatal(err)}
 if _,err:=os.Stat(filepath.Dir(output));err!=nil{t.Fatal(err)}
}

func TestDiskPreflightRequiresSpaceLinux(t *testing.T) {
 if err:=ensureFreeDiskSpace(t.TempDir(),filepath.Join(t.TempDir(),"out.mp4"),^uint64(0));err!=nil && !strings.Contains(err.Error(),"insufficient free disk space"){t.Fatal(err)}
}
