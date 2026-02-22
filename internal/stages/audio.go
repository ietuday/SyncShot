package stages

import (
	"fmt"
	"os"
	"path/filepath"
)

func PickAudio(dir string) (string, error) {

	files, err := os.ReadDir(dir)
	if err != nil {
		return "", err
	}

	if len(files) == 0 {
		return "", fmt.Errorf("no audio found")
	}

	return filepath.Join(dir, files[0].Name()), nil
}
