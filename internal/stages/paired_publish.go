package stages

import (
 "encoding/json"
 "fmt"
 "os"
 "path/filepath"
)

// PublicationJournal records the intended pair update. A restart with an
// unfinished journal restores prior outputs before starting another run.
type publicationJournal struct {
 Video,Shorts string
 VideoHad,ShortsHad bool
}
func journalPath(video string) string { return video+".syncshot-transaction.json" }
func exists(path string)(bool,error){_,err:=os.Lstat(path);if err==nil{return true,nil};if os.IsNotExist(err){return false,nil};return false,err}
func removeOutput(path string)error {return os.RemoveAll(path)}
func writeJournal(path string,j publicationJournal)error{
 b,err:=json.Marshal(j);if err!=nil{return err}
 f,err:=os.OpenFile(path,os.O_WRONLY|os.O_CREATE|os.O_EXCL,0600);if err!=nil{return err}
 if _,err=f.Write(b);err!=nil{f.Close();os.Remove(path);return err}
 if err=f.Sync();err!=nil{f.Close();os.Remove(path);return err}
 return f.Close()
}
// RecoverVideoShortsPublication restores both prior outputs after an
// interrupted, journaled publication. It is safe to call repeatedly.
func RecoverVideoShortsPublication(video,shorts string) error {
 path:=journalPath(video)
 b,err:=os.ReadFile(path)
 if os.IsNotExist(err){return nil}
 if err!=nil{return err}
 var j publicationJournal
 if err:=json.Unmarshal(b,&j);err!=nil{return fmt.Errorf("invalid transaction journal: %w",err)}
 if filepath.Clean(j.Video)!=filepath.Clean(video)||filepath.Clean(j.Shorts)!=filepath.Clean(shorts){return fmt.Errorf("journal output paths mismatch")}
 for _,item:=range []struct{path string;had bool}{{video,j.VideoHad},{shorts,j.ShortsHad}}{
  backup:=item.path+".syncshot-transaction-backup"
  hasBackup,err:=exists(backup);if err!=nil{return err}
  if hasBackup{
   if err:=removeOutput(item.path);err!=nil{return err}
   if err:=os.Rename(backup,item.path);err!=nil{return fmt.Errorf("restore %s: %w",item.path,err)}
  } else if !item.had {
   if err:=removeOutput(item.path);err!=nil{return err}
  } else {
   // The old output might still be in place if interruption preceded backup.
   hasCurrent,err:=exists(item.path);if err!=nil{return err}
   if !hasCurrent{return fmt.Errorf("cannot recover %s: old output and backup missing",item.path)}
  }
 }
 return os.Remove(path)
}
// PublishVideoAndShorts stages both outputs before replacing either of them.
// On errors and interrupted writes, the journal supports rolling back to the
// last paired outputs. Do not run concurrently for the same destinations.
func PublishVideoAndShorts(stageVideo,video,stageShorts,shorts string) error {
 return publishVideoAndShortsWithRename(stageVideo,video,stageShorts,shorts,os.Rename)
}

// rename is injectable for deterministic rollback and failure-injection tests.
func publishVideoAndShortsWithRename(stageVideo,video,stageShorts,shorts string,rename func(string,string)error) (err error) {
 if filepath.Clean(video)==filepath.Clean(shorts) {return fmt.Errorf("video and Shorts destinations collide")}
 for _,item:=range []struct{src,dst string}{{stageVideo,video},{stageShorts,shorts}}{
  a,e:=filepath.Abs(filepath.Dir(item.src));if e!=nil{return e}
  b,e:=filepath.Abs(filepath.Dir(item.dst));if e!=nil{return e}
  if a!=b{return fmt.Errorf("staging and output parent must match for %s",item.dst)}
 }
 if err:=validateRenderedMedia(stageVideo);err!=nil{return err}
 entries,err:=os.ReadDir(stageShorts);if err!=nil{return err}
 if len(entries)==0{return fmt.Errorf("Shorts batch is empty")}
 for _,entry:=range entries{
  if entry.IsDir(){return fmt.Errorf("unexpected Shorts directory: %s",entry.Name())}
  if err:=validateRenderedMedia(filepath.Join(stageShorts,entry.Name()));err!=nil{return err}
 }
 if err:=RecoverVideoShortsPublication(video,shorts);err!=nil{return err}
 j:=publicationJournal{Video:video,Shorts:shorts}
 j.VideoHad,err=exists(video);if err!=nil{return err}
 j.ShortsHad,err=exists(shorts);if err!=nil{return err}
 for _,dst:=range []string{video,shorts}{
  present,e:=exists(dst+".syncshot-transaction-backup");if e!=nil{return e};if present{return fmt.Errorf("unexpected prior transaction backup: %s",dst)}
 }
 if err:=writeJournal(journalPath(video),j);err!=nil{return err}
 committed:=false
 defer func(){
  if !committed {
   if recoveryErr:=RecoverVideoShortsPublication(video,shorts);recoveryErr!=nil {
    if err!=nil{err=fmt.Errorf("%v; rollback failed: %w",err,recoveryErr)}else{err=recoveryErr}
   }
  }
 }()
 for _,item:=range []struct{src,dst string;had bool}{{stageVideo,video,j.VideoHad},{stageShorts,shorts,j.ShortsHad}}{
  if item.had {
   if err:=rename(item.dst,item.dst+".syncshot-transaction-backup");err!=nil{return err}
  }
  if err:=rename(item.src,item.dst);err!=nil{return err}
 }
 // Both outputs are published. Removing the journal commits this pair.
 // Backups remain until commit so failure before this point can roll back.
 if err:=os.Remove(journalPath(video));err!=nil{return err}
 committed=true
 // Cleanup failures after commit are nonfatal; the new pair is already live.
 _=removeOutput(video+".syncshot-transaction-backup")
 _=removeOutput(shorts+".syncshot-transaction-backup")
 return nil
}
