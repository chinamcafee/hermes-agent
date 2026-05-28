package store

import (
	"fmt"
	"strings"
)

func NormalizeDeletionScope(scope string) (string, error) {
	normalized := strings.ToLower(strings.TrimSpace(scope))
	switch normalized {
	case "team_memory", "team_soul":
		return normalized, nil
	case "personal_memory":
		return "", fmt.Errorf("unsupported_deletion_scope")
	default:
		return "", fmt.Errorf("unsupported_deletion_scope")
	}
}
