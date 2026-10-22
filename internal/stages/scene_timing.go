package stages

import ("fmt"; "math")

// SceneSeconds evenly distributes images across the narration, without repeating
// the slideshow. A positive fallback is used only when narration duration is unknown.
func SceneSeconds(audioSeconds float64, count int, fallback float64) (float64, error) {
 if count < 1 { return 0, fmt.Errorf("image count must be positive") }
 if fallback <= 0 || math.IsNaN(fallback) || math.IsInf(fallback, 0) { return 0, fmt.Errorf("fallback duration must be finite and positive") }
 if audioSeconds > 0 && !math.IsNaN(audioSeconds) && !math.IsInf(audioSeconds, 0) {
  return audioSeconds / float64(count), nil
 }
 return fallback, nil
}
