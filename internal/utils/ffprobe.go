package utils

import (
	"fmt"
	"os/exec"
	"strconv"
	"strings"
)

// ProbeDurationSeconds returns rounded duration (seconds) for any media file.
func ProbeDurationSeconds(path string) (int, error) {
	_, err := exec.LookPath("ffprobe")
	if err != nil {
		return 0, fmt.Errorf("ffprobe not found")
	}

	cmd := exec.Command(
		"ffprobe",
		"-v", "error",
		"-show_entries", "format=duration",
		"-of", "default=noprint_wrappers=1:nokey=1",
		path,
	)

	out, err := cmd.Output()
	if err != nil {
		return 0, err
	}

	s := strings.TrimSpace(string(out))
	f, err := strconv.ParseFloat(s, 64)
	if err != nil {
		return 0, err
	}
	if f < 0 {
		f = 0
	}
	return int(f + 0.5), nil
}
