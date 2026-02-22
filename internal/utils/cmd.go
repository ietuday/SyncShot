package utils

import (
	"bufio"
	"bytes"
	"fmt"
	"io"
	"os/exec"
	"strconv"
	"strings"
	"time"
)

// RunFFmpegWithProgress runs ffmpeg and logs progress based on out_time_ms.
// totalSeconds: if >0, we compute percent. If 0, we just print timestamps.
func RunFFmpegWithProgress(log *Logger, totalSeconds int, args ...string) error {
	cmd := exec.Command("ffmpeg", args...)

	stdout, err := cmd.StdoutPipe()
	if err != nil {
		return err
	}
	stderr, err := cmd.StderrPipe()
	if err != nil {
		return err
	}

	var stderrBuf bytes.Buffer

	if err := cmd.Start(); err != nil {
		return err
	}

	// 1) Read stderr (ffmpeg logs). Keep buffer for errors.
	doneErr := make(chan struct{})
	go func() {
		defer close(doneErr)
		_, _ = io.Copy(io.MultiWriter(&stderrBuf), stderr)
	}()

	// 2) Read stdout progress (because we will pass: -progress pipe:1)
	lastPct := -1
	lastLog := time.Now()

	sc := bufio.NewScanner(stdout)
	for sc.Scan() {
		line := strings.TrimSpace(sc.Text())
		// progress format: key=value
		if strings.HasPrefix(line, "out_time_ms=") {
			msStr := strings.TrimPrefix(line, "out_time_ms=")
			ms, _ := strconv.ParseInt(msStr, 10, 64)
			sec := float64(ms) / 1_000_000.0

			// Throttle logs (avoid spamming)
			if time.Since(lastLog) < 700*time.Millisecond {
				continue
			}
			lastLog = time.Now()

			if totalSeconds > 0 {
				pct := int((sec / float64(totalSeconds)) * 100)
				if pct > 100 {
					pct = 100
				}
				if pct != lastPct {
					lastPct = pct
					log.Info(fmt.Sprintf("ffmpeg progress: %d%%", pct))
				}
			} else {
				log.Info(fmt.Sprintf("ffmpeg progress: %.1fs", sec))
			}
		}

		// ffmpeg sends "progress=end" at end
		if line == "progress=end" && totalSeconds > 0 {
			log.Info("ffmpeg progress: 100%")
		}
	}

	// Wait for ffmpeg
	err = cmd.Wait()
	<-doneErr

	if err != nil {
		log.Error("FFmpeg failed. Full stderr:")
		log.Error(stderrBuf.String())
		return err
	}

	return nil
}
