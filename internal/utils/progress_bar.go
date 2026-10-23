package utils

import (
 "fmt"
 "strings"
)

// FormatProgressBar formats the encoded media percentage as a stable,
// terminal- and CI-friendly fixed-width bar.
func FormatProgressBar(percent int) string {
 if percent < 0 { percent = 0 }
 if percent > 100 { percent = 100 }
 const width = 30
 filled := percent * width / 100
 return fmt.Sprintf("[%s%s] %3d%%", strings.Repeat("=",filled),strings.Repeat("-",width-filled),percent)
}
