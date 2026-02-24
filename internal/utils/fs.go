package utils

import (
	"os"
	"path/filepath"
)

// EnsureDirs creates directories if not exist
func EnsureDirs(dirs ...string) error {
	for _, d := range dirs {
		err := os.MkdirAll(d, os.ModePerm)
		if err != nil {
			return err
		}
	}
	return nil
}

// CleanDir removes all files inside a directory but keeps the directory itself
func CleanDir(dir string) error {

	// ensure directory exists
	err := os.MkdirAll(dir, os.ModePerm)
	if err != nil {
		return err
	}

	entries, err := os.ReadDir(dir)
	if err != nil {
		return err
	}

	for _, entry := range entries {

		name := entry.Name()

		// skip gitkeep
		if name == ".gitkeep" {
			continue
		}

		fullPath := filepath.Join(dir, name)

		err := os.RemoveAll(fullPath)
		if err != nil {
			return err
		}
	}

	return nil
}

// CleanOutput removes previous run outputs safely
func CleanOutput(workDir, shortsDir, videoPath string) error {

	videoDir := filepath.Dir(videoPath)

	err := CleanDir(workDir)
	if err != nil {
		return err
	}

	err = CleanDir(shortsDir)
	if err != nil {
		return err
	}

	err = CleanDir(videoDir)
	if err != nil {
		return err
	}

	return nil
}
