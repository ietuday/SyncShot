package stages

import (
	"syncshotgo/internal/utils"
)

func ProcessImagesWorkerPool(
	log *utils.Logger,
	images []string,
	outDir string,
	workers int,
) ([]string, error) {

	// currently just return images directly
	// later we will add resize + concurrency

	return images, nil
}
