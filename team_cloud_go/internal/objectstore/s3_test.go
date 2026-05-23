package objectstore

import (
	"io"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestS3StorePutsObjectUsingPathStyleBucket(t *testing.T) {
	var putPath string
	var putBody string
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.Method {
		case http.MethodHead:
			if r.URL.Path != "/personal-backups" {
				t.Fatalf("HEAD path = %s", r.URL.Path)
			}
			w.WriteHeader(http.StatusOK)
		case http.MethodPut:
			putPath = r.URL.Path
			raw, _ := io.ReadAll(r.Body)
			putBody = string(raw)
			if r.Header.Get("Authorization") == "" {
				t.Fatal("missing Authorization header")
			}
			if r.Header.Get("X-Amz-Content-Sha256") == "" {
				t.Fatal("missing payload hash header")
			}
			w.WriteHeader(http.StatusOK)
		default:
			t.Fatalf("unexpected method %s", r.Method)
		}
	}))
	defer server.Close()

	store, err := NewS3(S3Config{
		Endpoint:        server.URL,
		Bucket:          "personal-backups",
		Region:          "us-east-1",
		AccessKeyID:     "minio",
		SecretAccessKey: "secret",
	})
	if err != nil {
		t.Fatalf("NewS3() error = %v", err)
	}
	if err := store.Ping(t.Context()); err != nil {
		t.Fatalf("Ping() error = %v", err)
	}
	if err := store.Put(t.Context(), "org/org-1/member/alice/personal-memory/backup.jsonl.enc", []byte("ciphertext"), "application/octet-stream"); err != nil {
		t.Fatalf("Put() error = %v", err)
	}
	if putPath != "/personal-backups/org/org-1/member/alice/personal-memory/backup.jsonl.enc" {
		t.Fatalf("put path = %s", putPath)
	}
	if putBody != "ciphertext" {
		t.Fatalf("put body = %q", putBody)
	}
}
