package pipeline

import (
 "context"
 "os"
 "os/exec"
 "path/filepath"
 "testing"

 "syncshotgo/internal/utils"
)

// A prior pipeline run and legacy processed_images must not affect the next
// render, even if that legacy folder contains valid leftover JPEGs.
func TestRunIgnoresStaleProcessedImages(t *testing.T) {
 if testing.Short(){t.Skip("FFmpeg integration")}
 for _,name:=range []string{"ffmpeg","ffprobe"}{if _,err:=exec.LookPath(name);err!=nil{t.Skip(name+" unavailable")}}
 root:=t.TempDir()
 audioDir:=filepath.Join(root,"audio");imagesDir:=filepath.Join(root,"images")
 for _,dir:=range []string{audioDir,imagesDir}{if err:=os.MkdirAll(dir,0755);err!=nil{t.Fatal(err)}}
 mk:=func(path string,args ...string){params:=append([]string{"-hide_banner","-loglevel","error","-y"},args...);if b,err:=exec.Command("ffmpeg",append(params,path)...).CombinedOutput();err!=nil{t.Fatalf("make %s: %v: %s",path,err,b)}}
 mk(filepath.Join(audioDir,"voice.wav"),"-f","lavfi","-i","sine=frequency=300:duration=1","-c:a","pcm_s16le")
 first:=filepath.Join(imagesDir,"a.png");second:=filepath.Join(imagesDir,"b.png")
 mk(first,"-f","lavfi","-i","color=c=red:s=320x180","-frames:v","1")
 mk(second,"-f","lavfi","-i","color=c=blue:s=320x180","-frames:v","1")
 cfg:=Config{AudioDir:audioDir,ImagesDir:imagesDir,OutVideoPath:filepath.Join(root,"video","final.mp4"),OutShortsDir:filepath.Join(root,"shorts"),WorkDir:filepath.Join(root,"work"),FPS:12,SecondsPerImage:1,MaxWorkers:1,CinematicEnabled:true,CinematicCrossfade:0,PreviewSeconds:1,RenderProfile:"720p"}
 log:=utils.NewLogger()
 if err:=RunContext(context.Background(),log,cfg);err!=nil{t.Fatal(err)}
 legacy:=filepath.Join(cfg.WorkDir,"processed_images")
 if err:=os.MkdirAll(legacy,0755);err!=nil{t.Fatal(err)}
 stale:=filepath.Join(legacy,"img_999999.jpg")
 if err:=os.WriteFile(stale,[]byte("stale"),0600);err!=nil{t.Fatal(err)}
 if err:=os.Remove(second);err!=nil{t.Fatal(err)}
 if err:=RunContext(context.Background(),log,cfg);err!=nil{t.Fatalf("rerun selected stale image: %v",err)}
 if _,err:=os.Stat(stale);err!=nil{t.Fatalf("legacy directory unexpectedly changed: %v",err)}
 runs,err:=filepath.Glob(filepath.Join(cfg.WorkDir,".run-*"));if err!=nil{t.Fatal(err)}
 if len(runs)!=0{t.Fatalf("run workspaces not cleaned: %v",runs)}
}
