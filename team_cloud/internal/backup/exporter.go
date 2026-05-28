package backup

import (
	"bytes"
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"strings"
	"time"

	"hermes-agent/team_cloud/internal/store"
)

const encryptedJSONLHeader = "HERMES-TEAM-MEMORY-BACKUP-V1"

type Manifest struct {
	Format         string `json:"format"`
	Encryption     string `json:"encryption"`
	OrgID          string `json:"org_id"`
	MemberID       string `json:"member_id"`
	ItemCount      int    `json:"item_count"`
	ChecksumSHA256 string `json:"checksum_sha256"`
	CreatedAt      string `json:"created_at"`
}

func EncodeEncryptedJSONL(orgID, memberID string, items []store.MemoryItem, secret string) ([]byte, Manifest, error) {
	if strings.TrimSpace(secret) == "" {
		return nil, Manifest{}, fmt.Errorf("backup encryption key is required")
	}
	plaintext, err := encodeJSONL(items)
	if err != nil {
		return nil, Manifest{}, err
	}
	key := sha256.Sum256([]byte(secret))
	block, err := aes.NewCipher(key[:])
	if err != nil {
		return nil, Manifest{}, err
	}
	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return nil, Manifest{}, err
	}
	nonce := make([]byte, gcm.NonceSize())
	if _, err := rand.Read(nonce); err != nil {
		return nil, Manifest{}, err
	}
	ciphertext := gcm.Seal(nil, nonce, plaintext, []byte(orgID+"|"+memberID))
	payload := []byte(encryptedJSONLHeader + "\n")
	payload = append(payload, []byte(base64.RawURLEncoding.EncodeToString(nonce))...)
	payload = append(payload, '\n')
	payload = append(payload, ciphertext...)
	sum := sha256.Sum256(payload)
	return payload, Manifest{
		Format:         "jsonl.enc",
		Encryption:     "aes-256-gcm",
		OrgID:          orgID,
		MemberID:       memberID,
		ItemCount:      len(items),
		ChecksumSHA256: hex.EncodeToString(sum[:]),
		CreatedAt:      time.Now().UTC().Format(time.RFC3339),
	}, nil
}

func DecodeEncryptedJSONL(orgID, memberID string, payload []byte, secret string) ([]store.MemoryItem, error) {
	if strings.TrimSpace(secret) == "" {
		return nil, fmt.Errorf("backup encryption key is required")
	}
	firstNewline := bytes.IndexByte(payload, '\n')
	if firstNewline < 0 || string(payload[:firstNewline]) != encryptedJSONLHeader {
		return nil, fmt.Errorf("invalid_backup_payload_header")
	}
	rest := payload[firstNewline+1:]
	secondNewline := bytes.IndexByte(rest, '\n')
	if secondNewline < 0 {
		return nil, fmt.Errorf("invalid_backup_payload_nonce")
	}
	nonce, err := base64.RawURLEncoding.DecodeString(string(rest[:secondNewline]))
	if err != nil {
		return nil, fmt.Errorf("decode_backup_nonce: %w", err)
	}
	ciphertext := rest[secondNewline+1:]
	key := sha256.Sum256([]byte(secret))
	block, err := aes.NewCipher(key[:])
	if err != nil {
		return nil, err
	}
	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return nil, err
	}
	plaintext, err := gcm.Open(nil, nonce, ciphertext, []byte(orgID+"|"+memberID))
	if err != nil {
		return nil, fmt.Errorf("decrypt_backup_payload: %w", err)
	}
	items := []store.MemoryItem{}
	decoder := json.NewDecoder(bytes.NewReader(plaintext))
	for {
		var item store.MemoryItem
		if err := decoder.Decode(&item); errors.Is(err, io.EOF) {
			break
		} else if err != nil {
			return nil, fmt.Errorf("decode_backup_jsonl: %w", err)
		}
		items = append(items, item)
	}
	return items, nil
}

func ManifestMap(manifest Manifest, extra map[string]any) map[string]any {
	raw, _ := json.Marshal(manifest)
	out := map[string]any{}
	_ = json.Unmarshal(raw, &out)
	for key, value := range extra {
		out[key] = value
	}
	return out
}

func encodeJSONL(items []store.MemoryItem) ([]byte, error) {
	var builder strings.Builder
	encoder := json.NewEncoder(&builder)
	for _, item := range items {
		if err := encoder.Encode(item); err != nil {
			return nil, err
		}
	}
	return []byte(builder.String()), nil
}
