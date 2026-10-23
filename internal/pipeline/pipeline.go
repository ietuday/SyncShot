package pipeline

import (
	"context"
 "fmt"
 "os"
	"path/filepath"

	"syncshotgo/internal/stages"
 "syncshotgo/internal/cinematic"
 "syncshotgo/internal/subtitles"
	"syncshotgo/internal/utils"
)

type Config struct {
 CinematicChunkScenes int
 PreviewSeconds int
 RenderProfile string
 SmartShortsEnabled bool
 SmartShortsCrop string
 MusicPath string
 MusicVolume float64
 MusicFadeSeconds float64
 MusicDucking bool
 SubtitleMode string
 SubtitleSRTPath string
 CinematicEnabled bool
 CinematicTimelinePath string
 CinematicCrossfade float64
 CinematicMotion cinematic.Motion
 CinematicAutoSceneSeconds float64
	AudioDir        string
	ImagesDir       string
	OutVideoPath    string
	OutShortsDir    string
	WorkDir         string
	FPS             int
	SecondsPerImage float64
	ClipSeconds     int
	MaxWorkers      int
	// Overlay settings
	AddSubscribeButton  bool
	AddNotificationBell bool
	SubscribeOpacity    float32 // 0.0-1.0
	NotificationOpacity float32 // 0.0-1.0
}

func Run(log *utils.Logger, cfg Config) error {
 return RunContext(context.Background(), log, cfg)
}

func RunContext(ctx context.Context, log *utils.Logger, cfg Config) error {
 if err:=ctx.Err(); err!=nil { return err }
 if err := cfg.Validate(); err != nil { return fmt.Errorf("invalid configuration: %w", err) }
 release, err := acquireRunLock(cfg.WorkDir)
 if err != nil { return err }
 defer func() { if unlockErr := release(); unlockErr != nil { log.Warn("Failed to remove run lock: "+unlockErr.Error()) } }()

 // A run-specific directory prevents stale images from past runs
 // entering the new video and isolates previews/subtitles.
 if err:=utils.EnsureDirs(cfg.WorkDir,cfg.OutShortsDir,filepath.Dir(cfg.OutVideoPath));err!=nil{return err}
 runDir,err:=os.MkdirTemp(cfg.WorkDir,".run-*")
 if err!=nil{return fmt.Errorf("create run workspace: %w",err)}
 defer os.RemoveAll(runDir)
 workProcessed := filepath.Join(runDir, "processed_images")
 workSubtitles := filepath.Join(runDir, "subtitles")
 if err:=utils.EnsureDirs(workProcessed,workSubtitles);err!=nil{return err}

	// 1) Pick audio
	log.Info("Picking audio")
	audio, err := stages.PickAudio(cfg.AudioDir)
	if err != nil {
		return err
	}
 // Recover any interrupted paired publication before preparing new artifacts.
 paired:=cfg.ClipSeconds>0 && cfg.PreviewSeconds==0
 if paired {
  if err:=stages.RecoverVideoShortsPublication(cfg.OutVideoPath,cfg.OutShortsDir);err!=nil{return fmt.Errorf("recover outputs: %w",err)}
 }
 renderOutput:=cfg.OutVideoPath
 if paired {
  stage,err:=os.CreateTemp(filepath.Dir(cfg.OutVideoPath),".syncshot-video-stage-*.mp4")
  if err!=nil{return err}
  renderOutput=stage.Name()
  if err:=stage.Close();err!=nil{os.Remove(renderOutput);return err}
  os.Remove(renderOutput)
  defer os.Remove(renderOutput)
 }
 if cfg.PreviewSeconds>0 {
  renderOutput=filepath.Join(filepath.Dir(cfg.OutVideoPath),"preview.mp4")
  if filepath.Clean(renderOutput)==filepath.Clean(cfg.OutVideoPath) {return fmt.Errorf("preview output must differ from final video")}
  clipped:=filepath.Join(runDir,"preview-audio.wav")
  if err:=stages.TrimPreviewAudio(ctx,audio,clipped,cfg.PreviewSeconds);err!=nil{return fmt.Errorf("prepare preview: %w",err)}
  defer os.Remove(clipped)
  audio=clipped
  log.Info(fmt.Sprintf("Preview: %ds to %s",cfg.PreviewSeconds,renderOutput))
 }

	// 2) Scan images
	log.Info("Scanning images")
	images, err := stages.ScanImages(cfg.ImagesDir)
	if err != nil {
		return err
	}
	if len(images) == 0 {
		return fmt.Errorf("no images found in %s", cfg.ImagesDir)
	}
	log.Info(fmt.Sprintf("Found %d images", len(images)))

	// 3) Process images (resize/letterbox to 1920x1080)
	log.Info("Processing images")
	processed, err := stages.ProcessImagesWorkerPoolContext(
        ctx,
		log,
		images,
		workProcessed,
		cfg.MaxWorkers,
	)
	if err != nil {
		return err
	}
	log.Info(fmt.Sprintf("Processed %d images into %s", len(processed), workProcessed))

	// 4) Prepare optional, validated subtitles.
	subtitlePath, err := subtitles.Prepare(ctx, audio, cfg.SubtitleSRTPath, cfg.SubtitleMode, workSubtitles)
	if err != nil {
		return fmt.Errorf("prepare subtitles: %w", err)
	}

	// 4.5) Prepare overlays if enabled
	var subscribePath, notificationPath string
	if cfg.AddSubscribeButton || cfg.AddNotificationBell {
		overlayConfig := stages.OverlayConfig{
			EnableSubscribe:     cfg.AddSubscribeButton,
			EnableNotification:  cfg.AddNotificationBell,
			SubscribeOpacity:    cfg.SubscribeOpacity,
			NotificationOpacity: cfg.NotificationOpacity,
		}
		subscribePath, notificationPath, err = stages.PrepareOverlays(log, overlayConfig, cfg.WorkDir)
		if err != nil {
			return err
		}
	}

	// 5) Render YouTube video using PROCESSED images directory (not original)
	log.Info("Creating YouTube video")
 if cfg.CinematicEnabled {
  cinematicOverlays := cinematic.Overlays{MusicPath:cfg.MusicPath,MusicVolume:cfg.MusicVolume,MusicFadeSeconds:cfg.MusicFadeSeconds,MusicDucking:cfg.MusicDucking,SubtitlePath:subtitlePath,SubscribeOpacity:cfg.SubscribeOpacity,NotificationOpacity:cfg.NotificationOpacity}
  if cfg.AddSubscribeButton { cinematicOverlays.SubscribePath=subscribePath }
  if cfg.AddNotificationBell { cinematicOverlays.NotificationPath=notificationPath }
  var cinematicErr error
  if cfg.CinematicTimelinePath != "" {
   cinematicErr = stages.RenderCinematicTimelineWithOverlays(ctx, log, cfg.CinematicTimelinePath, audio, renderOutput,cinematicOverlays)
  } else {
   width,height:=1920,1080
   if cfg.RenderProfile=="720p" {width,height=1280,720}
   cinematicErr = stages.RenderCinematicChunkedProfile(ctx, log, workProcessed, audio, renderOutput, cfg.FPS, cfg.CinematicCrossfade, cfg.CinematicMotion,cfg.CinematicAutoSceneSeconds,width,height,cinematicOverlays,cfg.CinematicChunkScenes)
  }
  if err := cinematicErr; err != nil {
   return fmt.Errorf("cinematic rendering: %w", err)
  }
 } else {
  if subtitlePath!="" {return fmt.Errorf("subtitles currently require cinematic rendering")}
 	if err := stages.RenderYouTubeVideoWithOverlaysContext(
        ctx,
		log,
		workProcessed, // ✅ important: use processed_images folder
		audio,
		renderOutput,
		cfg.SecondsPerImage,
		cfg.FPS,
		subscribePath,
		notificationPath,
		cfg.SubscribeOpacity,
		cfg.NotificationOpacity,
	); err != nil {
		return err
	}

 }

	// 6) Create vertical Shorts only when requested.
 if cfg.ClipSeconds > 0 && cfg.PreviewSeconds == 0 {
  log.Info("Creating Shorts")
  cropMode:=cfg.SmartShortsCrop
  sceneSeconds:=0.0
  if cfg.SmartShortsEnabled {
   if cfg.CinematicTimelinePath=="" {sceneSeconds=cfg.CinematicAutoSceneSeconds}
  }
  parent:=filepath.Dir(cfg.OutShortsDir)
  stagedShorts,err:=os.MkdirTemp(parent,".syncshot-shorts-stage-*")
  if err!=nil{return err}
  if err:=os.Remove(stagedShorts);err!=nil{return err}
  defer os.RemoveAll(stagedShorts)
  if err:=stages.CreateSmartShortsContext(ctx, log, renderOutput, stagedShorts, cfg.ClipSeconds, cfg.MaxWorkers, sceneSeconds, cropMode);err!=nil{
   return fmt.Errorf("create Shorts before publication: %w",err)
  }
  if err:=ctx.Err();err!=nil{return err}
  if err:=stages.PublishVideoAndShorts(renderOutput,cfg.OutVideoPath,stagedShorts,cfg.OutShortsDir);err!=nil{return fmt.Errorf("publish video and Shorts: %w",err)}
 }
 return nil
}
