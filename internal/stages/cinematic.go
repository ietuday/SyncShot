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
 images,err:=filepath.Glob(filepath.Join(imagesDir,"*.jpg"))
 if err!=nil {return err}
 sort.Strings(images)
 if len(images)==0 {return fmt.Errorf("no processed scenes in %s",imagesDir)}
 duration,err:=utils.ProbeDurationPrecise(ctx,audio)
 if err!=nil {return fmt.Errorf("probe narration: %w",err)}
 var timeline cinematic.Timeline
 if targetSceneSeconds>0 {
  timeline,err=cinematic.PlanScenes(images,duration,fps,1920,1080,fade,motion,targetSceneSeconds)
 } else {
  timeline,err=cinematic.FromImages(images,duration,fps,1920,1080,fade,motion)
 }
 if err!=nil {return err}
 if err:=recoverPublishedPath(output);err!=nil {return err}
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
