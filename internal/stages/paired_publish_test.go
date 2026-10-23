package stages

import (
 "os"
 "fmt"
 "os/exec"
 "path/filepath"
 "testing"
)

func testMP4(t *testing.T,path string){
 t.Helper()
 if _,err:=exec.LookPath("ffmpeg");err!=nil{t.Skip("FFmpeg missing")}
 args:=[]string{"-hide_banner","-loglevel","error","-y","-f","lavfi","-i","color=c=blue:s=160x90:r=12:d=1","-f","lavfi","-i","sine=frequency=440:duration=1","-c:v","libx264","-pix_fmt","yuv420p","-c:a","aac","-shortest",path}
 if b,err:=exec.Command("ffmpeg",args...).CombinedOutput();err!=nil{t.Fatalf("ffmpeg: %v %s",err,b)}
}
func TestPublishVideoAndShorts(t *testing.T){
 root:=t.TempDir()
 video:=filepath.Join(root,"final.mp4")
 shorts:=filepath.Join(root,"shorts")
 stageVideo:=filepath.Join(root,"new.mp4")
 stageShorts:=filepath.Join(root,"new-shorts")
 if err:=os.Mkdir(stageShorts,0755);err!=nil{t.Fatal(err)}
 testMP4(t,stageVideo)
 testMP4(t,filepath.Join(stageShorts,"short_000.mp4"))
 if err:=os.WriteFile(video,[]byte("OLD_VIDEO"),0600);err!=nil{t.Fatal(err)}
 if err:=os.Mkdir(shorts,0755);err!=nil{t.Fatal(err)}
 if err:=os.WriteFile(filepath.Join(shorts,"previous"),[]byte("OLD_SHORTS"),0600);err!=nil{t.Fatal(err)}
 if err:=PublishVideoAndShorts(stageVideo,video,stageShorts,shorts);err!=nil{t.Fatal(err)}
 if err:=validateRenderedMedia(video);err!=nil{t.Fatal(err)}
 if err:=validateRenderedMedia(filepath.Join(shorts,"short_000.mp4"));err!=nil{t.Fatal(err)}
 if _,err:=os.Stat(filepath.Join(shorts,"previous"));!os.IsNotExist(err){t.Fatal("old Shorts survived")}
 if _,err:=os.Stat(journalPath(video));!os.IsNotExist(err){t.Fatal("journal not cleaned")}
 if _,err:=os.Stat(video+".syncshot-transaction-backup");!os.IsNotExist(err){t.Fatal("backup not cleaned")}
}
func TestInvalidStagedShortPreservesPair(t *testing.T){
 root:=t.TempDir()
 video:=filepath.Join(root,"video.mp4")
 shorts:=filepath.Join(root,"shorts")
 stageVideo:=filepath.Join(root,"new.mp4")
 stageShorts:=filepath.Join(root,"incoming")
 for _,dir:=range []string{shorts,stageShorts}{if err:=os.Mkdir(dir,0755);err!=nil{t.Fatal(err)}}
 if err:=os.WriteFile(video,[]byte("old-video"),0600);err!=nil{t.Fatal(err)}
 if err:=os.WriteFile(filepath.Join(shorts,"old"),[]byte("old-shorts"),0600);err!=nil{t.Fatal(err)}
 testMP4(t,stageVideo)
 if err:=os.WriteFile(filepath.Join(stageShorts,"short_000.mp4"),[]byte("broken"),0600);err!=nil{t.Fatal(err)}
 if err:=PublishVideoAndShorts(stageVideo,video,stageShorts,shorts);err==nil{t.Fatal("expected validation failure")}
 b,err:=os.ReadFile(video);if err!=nil||string(b)!="old-video"{t.Fatal("video changed")}
 b,err=os.ReadFile(filepath.Join(shorts,"old"));if err!=nil||string(b)!="old-shorts"{t.Fatal("Shorts changed")}
}
func TestRecoverInterruptedPairPublication(t *testing.T){
 root:=t.TempDir()
 video:=filepath.Join(root,"video.mp4")
 shorts:=filepath.Join(root,"shorts")
 if err:=os.WriteFile(video+".syncshot-transaction-backup",[]byte("previous video"),0600);err!=nil{t.Fatal(err)}
 if err:=os.Mkdir(shorts+".syncshot-transaction-backup",0755);err!=nil{t.Fatal(err)}
 if err:=os.WriteFile(filepath.Join(shorts+".syncshot-transaction-backup","previous"),[]byte("previous shorts"),0600);err!=nil{t.Fatal(err)}
 if err:=os.WriteFile(video,[]byte("partial new video"),0600);err!=nil{t.Fatal(err)}
 if err:=writeJournal(journalPath(video),publicationJournal{Video:video,Shorts:shorts,VideoHad:true,ShortsHad:true});err!=nil{t.Fatal(err)}
 if err:=RecoverVideoShortsPublication(video,shorts);err!=nil{t.Fatal(err)}
 if err:=RecoverVideoShortsPublication(video,shorts);err!=nil{t.Fatal(err)}
 b,err:=os.ReadFile(video);if err!=nil||string(b)!="previous video"{t.Fatal("video not restored")}
 b,err=os.ReadFile(filepath.Join(shorts,"previous"));if err!=nil||string(b)!="previous shorts"{t.Fatal("Shorts not restored")}
}

func TestRenameFailureRollsBackBothOutputs(t *testing.T){
 root:=t.TempDir()
 video:=filepath.Join(root,"final.mp4")
 shorts:=filepath.Join(root,"shorts")
 stagedVideo:=filepath.Join(root,"staged.mp4")
 stagedShorts:=filepath.Join(root,"staged-shorts")
 if err:=os.Mkdir(shorts,0755);err!=nil{t.Fatal(err)}
 if err:=os.Mkdir(stagedShorts,0755);err!=nil{t.Fatal(err)}
 if err:=os.WriteFile(video,[]byte("old video"),0600);err!=nil{t.Fatal(err)}
 if err:=os.WriteFile(filepath.Join(shorts,"old"),[]byte("old shorts"),0600);err!=nil{t.Fatal(err)}
 testMP4(t,stagedVideo)
 testMP4(t,filepath.Join(stagedShorts,"short_000.mp4"))
 rename:=func(from,to string)error{
  if from==stagedShorts&&to==shorts{return fmt.Errorf("injected Shorts publish failure")}
  return os.Rename(from,to)
 }
 if err:=publishVideoAndShortsWithRename(stagedVideo,video,stagedShorts,shorts,rename);err==nil{t.Fatal("expected injected failure")}
 b,err:=os.ReadFile(video);if err!=nil||string(b)!="old video"{t.Fatal("video rollback failed")}
 b,err=os.ReadFile(filepath.Join(shorts,"old"));if err!=nil||string(b)!="old shorts"{t.Fatal("Shorts rollback failed")}
 if _,err:=os.Stat(journalPath(video));!os.IsNotExist(err){t.Fatalf("transaction journal remains: %v",err)}
}
