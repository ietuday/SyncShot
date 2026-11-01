package pipeline

import (
 "fmt"
 "os"
 "path/filepath"
 "syscall"
)

const minimumFreeBytes uint64 = 2 * 1024 * 1024 * 1024

// ensureFreeDiskSpace checks both workspace and final output filesystems.
// This is a safety floor rather than a prediction of actual render disk usage.
func ensureFreeDiskSpace(workDir, output string, minimum uint64) error {
 for _,dir:=range []string{workDir,filepath.Dir(output)} {
  if err:=os.MkdirAll(dir,0755);err!=nil{return fmt.Errorf("prepare disk preflight directory %s: %w",dir,err)}
  var fs syscall.Statfs_t
  if err:=syscall.Statfs(dir,&fs);err!=nil{return fmt.Errorf("inspect free disk space %s: %w",dir,err)}
  free:=fs.Bavail*uint64(fs.Bsize)
  if free<minimum {
   return fmt.Errorf("insufficient free disk space in %s: %.2f GiB available, at least %.2f GiB required; free disk space or select another output/work directory",dir,float64(free)/(1<<30),float64(minimum)/(1<<30))
  }
 }
 return nil
}
