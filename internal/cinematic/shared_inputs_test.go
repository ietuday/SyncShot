package cinematic

import (
 "context"
 "os"
 "os/exec"
 "path/filepath"
 "strings"
 "testing"
 "syncshotgo/internal/utils"
)

func TestSharedSceneInputs(t *testing.T) {
 timeline:=Timeline{FPS:12,Width:320,Height:180,Scenes:[]Scene{{Image:"same.png",Duration:2},{Image:"other.png",Duration:2},{Image:"same.png",Duration:2}}}
 paths,refs,prefix:=sharedSceneInputs(timeline)
 if len(paths)!=2 || len(refs)!=3 {t.Fatalf("paths=%v refs=%v",paths,refs)}
 if paths[0]!="same.png"||paths[1]!="other.png" {t.Fatalf("wrong input order %v",paths)}
 if refs[0]!="[shared_0]"||refs[1]!="[1:v]"||refs[2]!="[shared_2]" {t.Fatalf("wrong scene streams %v",refs)}
 if !strings.Contains(prefix,"[0:v]split=2[shared_0][shared_2]"){t.Fatalf("wrong split: %s",prefix)}
 filter,label,err:=timeline.buildFilterInputs(refs)
 if err!=nil||label==""||!strings.Contains(filter,"[shared_2]"){t.Fatalf("invalid filter: %q %v",filter,err)}
}
func TestSharedImageRenderWithMusicAndSubtitles(t *testing.T) {
 if testing.Short(){t.Skip("FFmpeg integration")}
 for _,bin:=range []string{"ffmpeg","ffprobe"} {if _,err:=exec.LookPath(bin);err!=nil{t.Skip(bin+" unavailable")}}
 dir:=t.TempDir()
 still:=filepath.Join(dir,"same.png")
 audio:=filepath.Join(dir,"audio.wav")
 music:=filepath.Join(dir,"music.wav")
 srt:=filepath.Join(dir,"sub.srt")
 for _,tc:=range []struct{output string;args []string}{
 {still,[]string{"-f","lavfi","-i","color=c=blue:s=320x180","-frames:v","1"}},
 {audio,[]string{"-f","lavfi","-i","sine=frequency=440:duration=4","-c:a","pcm_s16le"}},
 {music,[]string{"-f","lavfi","-i","sine=frequency=220:duration=1","-c:a","pcm_s16le"}},
 } {
  args:=append([]string{"-hide_banner","-loglevel","error","-y"},tc.args...)
  args=append(args,tc.output)
  if out,err:=exec.Command("ffmpeg",args...).CombinedOutput();err!=nil{t.Fatalf("create input: %v %s",err,out)}
 }
 if err:=os.WriteFile(srt,[]byte("1\n00:00:00,000 --> 00:00:01,000\nHello\n"),0600);err!=nil{t.Fatal(err)}
 timeline,err:=FromImages([]string{still,still},4,12,320,180,0.25,Static)
 if err!=nil{t.Fatal(err)}
 target:=filepath.Join(dir,"out.mp4")
 opts:=Overlays{MusicPath:music,MusicVolume:.12,MusicDucking:true,SubtitlePath:srt}
 if err:=RenderWithOverlays(context.Background(),utils.NewLogger(),timeline,audio,target,opts,os.Rename);err!=nil{t.Fatal(err)}
 if info,err:=os.Stat(target);err!=nil||info.Size()==0{t.Fatalf("render missing: %v",err)}
}
