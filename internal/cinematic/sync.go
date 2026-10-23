package cinematic

import (
 "fmt"
 "math"
)

// ValidateNarrationSync requires a custom timeline's visual duration to match
// narration within one output frame plus 20ms codec/container tolerance.
// Explicit scene durations are not silently stretched or shortened.
func (t Timeline) ValidateNarrationSync(audioSeconds float64) error {
 if err:=t.Validate();err!=nil {return err}
 if !finite(audioSeconds) || audioSeconds<=0 {return fmt.Errorf("invalid narration duration")}
 tolerance:=1/float64(t.FPS)+0.02
 delta:=math.Abs(t.Duration()-audioSeconds)
 if delta>tolerance {return fmt.Errorf("timeline duration %.3fs differs from narration %.3fs by %.3fs (tolerance %.3fs)",t.Duration(),audioSeconds,delta,tolerance)}
 return nil
}
