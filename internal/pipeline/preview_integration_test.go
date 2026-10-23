package pipeline

import (
 "context"
 "image"
 "image/color"
 "image/png"
 "os"
 "os/exec"
 "path/filepath"
 "testing"

 "syncshotgo/internal/utils"
)

// Ensure the preview render keeps an existing final video and Shorts untouched.
func TestPreviewDoesNotReplaceFinalOrShorts(t *testing.T) {
 if testing.Short() {t.Skip("FFmpeg integration")}
 for _,bin:=range []string{"ffmpeg","ffprobe"} {if _,err:=exec.LookPath(bin);err!=nil {t.Skip(bin+" unavailable")}}
 root:=t.TempDir()
 audioDir,imagesDir:=filepath.Join(root,"audio"),filepath.Join(root,"images")
 for _,p:=range []string{audioDir,imagesDir}{if err:=os.MkdirAll(p,0755);err!=nil{t.Fatal(err)}}
 img:=image.NewRGBA(image.Rect(0,0,320,180))
 for y:=0;y<180;y++{for x:=0;x<320;x++{img.Set(x,y,color.RGBA{B:255,A:255})}}
 f,err:=os.Create(filepath.Join(imagesDir,"frame.png"));if err!=nil{t.Fatal(err)}
 if err:=png.Encode(f,img);err!=nil{t.Fatal(err)}
 if err:=f.Close();err!=nil{t.Fatal(err)}
 a:=filepath.Join(audioDir,"narration.wav")
 if out,err:=exec.Command("ffmpeg","-hide_banner","-loglevel","error","-y","-f","lavfi","-i","sine=frequency=440:duration=4","-c:a","pcm_s16le",a).CombinedOutput();err!=nil{t.Fatalf("audio: %v %s",err,out)}
 final:=filepath.Join(root,"video","final.mp4")
 shorts:=filepath.Join(root,"shorts")
 if err:=os.MkdirAll(filepath.Dir(final),0755);err!=nil{t.Fatal(err)}
 if err:=os.MkdirAll(shorts,0755);err!=nil{t.Fatal(err)}
 original:=[]byte("original-final-video")
 if err:=os.WriteFile(final,original,0600);err!=nil{t.Fatal(err)}
 marker:=filepath.Join(shorts,"keep.txt")
 if err:=os.WriteFile(marker,[]byte("keep"),0600);err!=nil{t.Fatal(err)}
 cfg:=Config{AudioDir:audioDir,ImagesDir:imagesDir,OutVideoPath:final,OutShortsDir:shorts,WorkDir:filepath.Join(root,"work"),FPS:12,SecondsPerImage:2,ClipSeconds:2,MaxWorkers:1,CinematicEnabled:true,CinematicAutoSceneSeconds:30,CinematicCrossfade:0.5,PreviewSeconds:2,RenderProfile:"720p"}
 if err:=RunContext(context.Background(),utils.NewLogger(),cfg);err!=nil{t.Fatal(err)}
 if b,err:=os.ReadFile(final);err!=nil||string(b)!=string(original){t.Fatalf("final changed: %v",err)}
 if b,err:=os.ReadFile(marker);err!=nil||string(b)!="keep"{t.Fatalf("Shorts changed: %v",err)}
 preview:=filepath.Join(filepath.Dir(final),"preview.mp4")
 info,err:=os.Stat(preview);if err!=nil||info.Size()==0{t.Fatalf("preview missing: %v",err)}
 if _,err:=os.Stat(filepath.Join(cfg.WorkDir,"preview-audio.wav"));!os.IsNotExist(err){t.Fatalf("temporary audio not cleaned: %v",err)}
}
