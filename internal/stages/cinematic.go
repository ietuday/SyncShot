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
 images,err:=filepath.Glob(filepath.Join(imagesDir,"*.jpg"))
 if err!=nil {return err}
 sort.Strings(images)
 if len(images)==0 {return fmt.Errorf("no processed scenes in %s",imagesDir)}
 duration,err:=utils.ProbeDurationSeconds(audio)
 if err!=nil {return fmt.Errorf("probe narration: %w",err)}
 timeline,err:=cinematic.FromImages(images,float64(duration),fps,1920,1080,fade,motion)
 if err!=nil {return err}
 if err:=recoverPublishedPath(output);err!=nil {return err}
 return cinematic.Render(ctx,log,timeline,audio,output,promoteVideo)
}
