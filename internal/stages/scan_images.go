package stages

import (
	"os"
	"path/filepath"
)

func ScanImages(dir string) ([]string, error) {

	files, err := os.ReadDir(dir)
	if err != nil {
		return nil, err
	}

	var images []string

	for _, f := range files {

		path := filepath.Join(dir, f.Name())

		images = append(images, path)

	}

	return images, nil
}
