//go:build !linux

package pipeline

// Disk free-space checks currently target Linux installations.
const minimumFreeBytes uint64 = 2 * 1024 * 1024 * 1024

func ensureFreeDiskSpace(workDir, output string, minimum uint64) error {
 return nil
}
