package main

import (
 "context"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "io"
 "os"
 "os/exec"
 "os/signal"
 "syscall"
 "time"

 "syncshotgo/internal/pipeline"
 "syncshotgo/internal/utils"
)

func defaultConfig() pipeline.Config {
 return pipeline.Config{
  AudioDir:"./inputs/audio",ImagesDir:"./inputs/images",
  OutVideoPath:"./output/video/final.mp4",OutShortsDir:"./output/shorts",
  WorkDir:"./output/work",FPS:24,SecondsPerImage:3,
  ClipSeconds:50,MaxWorkers:4,CinematicEnabled:true,
  CinematicCrossfade:0.5,CinematicMotion:"zoom_in",
  CinematicAutoSceneSeconds:30,SubscribeOpacity:0.8,NotificationOpacity:0.8,
 }
}

func loadConfig(path string)(pipeline.Config,error){
 c:=defaultConfig()
 if path==""{return c,nil}
 f,err:=os.Open(path);if err!=nil{return c,fmt.Errorf("open config: %w",err)}
 defer f.Close()
 decoder:=json.NewDecoder(f);decoder.DisallowUnknownFields()
 if err:=decoder.Decode(&c);err!=nil{return c,fmt.Errorf("decode JSON config: %w",err)}
 var extra any
 if err:=decoder.Decode(&extra);err!=io.EOF{
  if err==nil{return c,fmt.Errorf("unexpected content after JSON config")}
  return c,fmt.Errorf("extra JSON content: %w",err)
 }
 return c,nil
}

func checkDependencies()error{
 for _,name:=range []string{"ffmpeg","ffprobe"}{
  if _,err:=exec.LookPath(name);err!=nil{return fmt.Errorf("%s is required in PATH: %w",name,err)}
 }
 return nil
}

func run(args []string)error{
 flags:=flag.NewFlagSet("syncshot",flag.ContinueOnError)
 configPath:=flags.String("config","","JSON configuration file")
 dryRun:=flags.Bool("dry-run",false,"validate configuration and media dependencies without rendering")
 audioDir:=flags.String("audio-dir","","override narration directory")
 imagesDir:=flags.String("images-dir","","override images directory")
 output:=flags.String("output","","override output video path")
 fps:=flags.Int("fps",0,"override video frames per second")
 chunkScenes:=flags.Int("chunk-scenes",-1,"scenes per cinematic chunk (0 disables chunking)")
 timeout:=flags.Duration("timeout",0,"overall render timeout, e.g. 2h (0 means no deadline)")
 if err:=flags.Parse(args);err!=nil{return err}
 if flags.NArg()!=0{return fmt.Errorf("unexpected positional arguments: %v",flags.Args())}
 cfg,err:=loadConfig(*configPath);if err!=nil{return err}
 if *audioDir!=""{cfg.AudioDir=*audioDir}
 if *imagesDir!=""{cfg.ImagesDir=*imagesDir}
 if *output!=""{cfg.OutVideoPath=*output}
 if *fps!=0{cfg.FPS=*fps}
 if *chunkScenes>=0{cfg.CinematicChunkScenes=*chunkScenes}
 if *timeout<0{return fmt.Errorf("timeout must not be negative")}
 if err:=cfg.Validate();err!=nil{return fmt.Errorf("invalid configuration: %w",err)}
 if err:=checkDependencies();err!=nil{return err}
 if *dryRun{
  images,err:=os.ReadDir(cfg.ImagesDir);if err!=nil{return err}
  fmt.Printf("Dry run OK: %d image directory entries, FPS=%d, chunk scenes=%d, output=%s (no rendering)\n",len(images),cfg.FPS,cfg.CinematicChunkScenes,cfg.OutVideoPath)
  return nil
 }
 ctx,stop:=signal.NotifyContext(context.Background(),os.Interrupt,syscall.SIGTERM)
 defer stop()
 if *timeout>0 {var cancel context.CancelFunc;ctx,cancel=context.WithTimeout(ctx,*timeout);defer cancel()}
 log:=utils.NewLogger()
 log.Info("Starting SyncShot-Go")
 if err:=pipeline.RunContext(ctx,log,cfg);err!=nil{
  if errors.Is(ctx.Err(),context.DeadlineExceeded){return fmt.Errorf("render exceeded configured timeout %s: %w",timeout.String(),ctx.Err())}
  return err
 }
 log.Info("Pipeline completed successfully")
 return nil
}

func main(){
 if err:=run(os.Args[1:]);err!=nil{fmt.Fprintln(os.Stderr,"SyncShot:",err);os.Exit(1)}
}

// Keep time imported for explicit duration-style command-line usage.
var _ time.Duration
