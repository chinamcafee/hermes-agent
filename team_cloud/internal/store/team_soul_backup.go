package store

import (
	"fmt"
	"strconv"
)

func TeamSoulBackupManifest(soul TeamSoul) map[string]any {
	return map[string]any{
		"org_id":          soul.OrgID,
		"team_id":         soul.TeamID,
		"content":         soul.Content,
		"version":         soul.Version,
		"checksum_sha256": soul.ChecksumSHA256,
		"updated_by":      soul.UpdatedBy,
		"updated_at":      soul.UpdatedAt,
	}
}

func TeamSoulFromBackupManifest(manifest map[string]any) (TeamSoul, error) {
	raw, ok := manifest["team_soul"].(map[string]any)
	if !ok {
		return TeamSoul{}, fmt.Errorf("team_soul_snapshot_required")
	}
	soul := TeamSoul{
		OrgID:          stringFromAny(raw["org_id"]),
		TeamID:         stringFromAny(raw["team_id"]),
		Content:        stringFromAny(raw["content"]),
		ChecksumSHA256: stringFromAny(raw["checksum_sha256"]),
		UpdatedBy:      stringFromAny(raw["updated_by"]),
		UpdatedAt:      stringFromAny(raw["updated_at"]),
	}
	if soul.TeamID == "" {
		soul.TeamID = soul.OrgID
	}
	switch version := raw["version"].(type) {
	case int:
		soul.Version = version
	case int64:
		soul.Version = int(version)
	case float64:
		soul.Version = int(version)
	case string:
		parsed, _ := strconv.Atoi(version)
		soul.Version = parsed
	}
	if soul.OrgID == "" || soul.TeamID == "" || soul.Content == "" {
		return TeamSoul{}, fmt.Errorf("team_soul_snapshot_required")
	}
	return soul, nil
}

func stringFromAny(value any) string {
	if value == nil {
		return ""
	}
	if typed, ok := value.(string); ok {
		return typed
	}
	return fmt.Sprint(value)
}
