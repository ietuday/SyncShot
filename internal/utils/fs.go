package utils

import "os"

func EnsureDirs(dirs ...string) error {

	for _, d := range dirs {

		err := os.MkdirAll(d, os.ModePerm)

		if err != nil {
			return err
		}

	}

	return nil
}
