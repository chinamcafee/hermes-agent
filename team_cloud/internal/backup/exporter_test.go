package backup

import (
	"strings"
	"testing"

	"hermes-agent/team_cloud/internal/store"
)

func TestEncodeEncryptedJSONLBackupProducesManifestAndCiphertext(t *testing.T) {
	payload, manifest, err := EncodeEncryptedJSONL("org-1", store.TeamBackupMemberID, []store.MemoryItem{{
		ID:      "mem-1",
		OrgID:   "org-1",
		Scope:   "team_shared",
		Status:  "active",
		Content: "confidential team memory",
		Version: 1,
	}}, "test encryption key")
	if err != nil {
		t.Fatalf("EncodeEncryptedJSONL() error = %v", err)
	}
	if len(payload) == 0 {
		t.Fatal("expected encrypted payload")
	}
	if !strings.HasPrefix(string(payload), "HERMES-TEAM-MEMORY-BACKUP-V1\n") {
		t.Fatalf("payload should use team memory header: %s", string(payload))
	}
	if strings.Contains(string(payload), "confidential team memory") {
		t.Fatalf("ciphertext leaked plaintext: %s", string(payload))
	}
	if manifest.Format != "jsonl.enc" || manifest.Encryption != "aes-256-gcm" {
		t.Fatalf("manifest = %#v", manifest)
	}
	if manifest.ItemCount != 1 || manifest.ChecksumSHA256 == "" {
		t.Fatalf("manifest counts/checksum = %#v", manifest)
	}
	if manifest.MemberID != store.TeamBackupMemberID {
		t.Fatalf("manifest should identify team memory backup sentinel, got %#v", manifest)
	}
}
