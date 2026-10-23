package stages

import (
 "context"
 "fmt"
 "path/filepath"
 "sort"

 "syncshotgo/internal/cinematic"
 "syncshotgo/internal/utils"
)

// RenderCinematic uses the Phase 1 output recovery and publish rules.
func RenderCinematic(ctx context.Context,log *utils.Logger,imagesDir,audio,output string,fps int,fade float64,motion cinematic.Motion) error {
 return RenderCinematicWithOverlays(ctx,log,imagesDir,audio,output,fps,fade,motion,cinematic.Overlays{})
}
func RenderCinematicWithOverlays(ctx context.Context,log *utils.Logger,imagesDir,audio,output string,fps int,fade float64,motion cinematic.Motion, overlays cinematic.Overlays) error {
 return RenderCinematicAutoWithOverlays(ctx,log,imagesDir,audio,output,fps,fade,motion,0,overlays)
}

// RenderCinematicAutoWithOverlays optionally splits long narration into scenes,
// rotating the supplied images. A nonpositive target retains Phase 2 behavior.
func RenderCinematicAutoWithOverlays(ctx context.Context,log *utils.Logger,imagesDir,audio,output string,fps int,fade float64,motion cinematic.Motion,targetSceneSeconds float64,overlays cinematic.Overlays) error {
 return RenderCinematicProfileWithOverlays(ctx,log,imagesDir,audio,output,fps,fade,motion,targetSceneSeconds,1920,1080,overlays)
}

func RenderCinematicProfileWithOverlays(ctx context.Context,log *utils.Logger,imagesDir,audio,output string,fps int,fade float64,motion cinematic.Motion,targetSceneSeconds float64,width,height int,overlays cinematic.Overlays) error {
 return RenderCinematicChunkedProfile(ctx,log,imagesDir,audio,output,fps,fade,motion,targetSceneSeconds,width,height,overlays,0)
}

// RenderCinematicChunkedProfile opts into bounded scene groups when chunkScenes > 0.
func RenderCinematicChunkedProfile(ctx context.Context,log *utils.Logger,imagesDir,audio,output string,fps int,fade float64,motion cinematic.Motion,targetSceneSeconds float64,width,height int,overlays cinematic.Overlays,chunkScenes int) error {
 images,err:=filepath.Glob(filepath.Join(imagesDir,"*.jpg"))
 if err!=nil {return err}
 sort.Strings(images)
 if len(images)==0 {return fmt.Errorf("no processed scenes in %s",imagesDir)}
 duration,err:=utils.ProbeDurationPrecise(ctx,audio)
 if err!=nil {return fmt.Errorf("probe narration: %w",err)}
 var timeline cinematic.Timeline
 if targetSceneSeconds>0 {
  timeline,err=cinematic.PlanScenes(images,duration,fps,width,height,fade,motion,targetSceneSeconds)
 } else {
  timeline,err=cinematic.FromImages(images,duration,fps,width,height,fade,motion)
 }
 if err!=nil {return err}
 log.Info(fmt.Sprintf("Scene plan: %d scene(s) from %d image(s), narration %.2fs, planned %.2fs, fade %.2fs",len(timeline.Scenes),len(images),duration,timeline.Duration(),fade))
 if err:=recoverPublishedPath(output);err!=nil {return err}
 if chunkScenes>0 {return cinematic.RenderChunked(ctx,log,timeline,audio,output,chunkScenes,promoteVideo)}
 return cinematic.RenderWithOverlays(ctx,log,timeline,audio,output,overlays,promoteVideo)
}

 
// RenderCinematicTimeline renders a user-authored JSON timeline.
func RenderCinematicTimeline(ctx context.Context, log *utils.Logger, configPath, audio, output string) error {
 return RenderCinematicTimelineWithOverlays(ctx,log,configPath,audio,output,cinematic.Overlays{})
}
func RenderCinematicTimelineWithOverlays(ctx context.Context, log *utils.Logger, configPath, audio, output string, overlays cinematic.Overlays) error {
 timeline, err := cinematic.LoadTimeline(configPath)
 if err != nil { return err }
 duration, err := utils.ProbeDurationPrecise(ctx,audio)
 if err != nil { return fmt.Errorf("probe narration: %w",err) }
 if err := timeline.ValidateNarrationSync(duration); err != nil { return err }
 if err := recoverPublishedPath(output); err != nil { return err }
 return cinematic.RenderWithOverlays(ctx, log, timeline, audio, output, overlays, promoteVideo)
}
