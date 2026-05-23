package httpapi_test

import (
	"bytes"
	"crypto"
	"crypto/rand"
	"crypto/rsa"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"math/big"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"hermes-agent/team_cloud_go/internal/config"
	"hermes-agent/team_cloud_go/internal/httpapi"
	"hermes-agent/team_cloud_go/internal/store/memory"
)

func TestCasdoorStyleJWTCanCallProtectedAPI(t *testing.T) {
	privateKey, jwksURL := startJWKS(t)
	handler := newJWTServer(t, jwksURL)
	token := signRS256JWT(t, privateKey, map[string]any{
		"iss":              "https://casdoor.example",
		"aud":              "hermes-team-cloud",
		"sub":              "casdoor-user-alice",
		"email":            "alice@example.com",
		"hermes_org_id":    "hermes-labs",
		"hermes_member_id": "hermes-labs:alice",
		"exp":              time.Now().Add(time.Hour).Unix(),
	})

	rec := requestJSONWithAuth(t, handler, http.MethodPost, "/api/organizations", map[string]string{
		"slug": "hermes-labs",
		"name": "Hermes Labs",
	}, "Bearer "+token)
	if rec.Code != http.StatusCreated {
		t.Fatalf("jwt create org status = %d body=%s", rec.Code, rec.Body.String())
	}

	badToken := signRS256JWT(t, privateKey, map[string]any{
		"iss": "https://casdoor.example",
		"aud": "other-audience",
		"sub": "casdoor-user-alice",
		"exp": time.Now().Add(time.Hour).Unix(),
	})
	denied := requestJSONWithAuth(t, handler, http.MethodGet, "/api/organizations", nil, "Bearer "+badToken)
	if denied.Code != http.StatusUnauthorized {
		t.Fatalf("bad audience status = %d body=%s", denied.Code, denied.Body.String())
	}
}

func TestGovernanceBackupExportDeletionToolPolicyAndAuthzAPIs(t *testing.T) {
	handler := newTestServer(t)
	requestJSON(t, handler, http.MethodPost, "/api/organizations", map[string]string{
		"slug": "org-1",
		"name": "Org 1",
	})
	requestJSON(t, handler, http.MethodPost, "/api/organizations/org-1/teams", map[string]string{
		"slug": "platform",
		"name": "Platform",
	})
	requestJSON(t, handler, http.MethodPost, "/api/organizations/org-1/members/invite", map[string]string{
		"email":        "alice@example.com",
		"display_name": "Alice",
		"user_id":      "alice",
	})
	personal := requestJSON(t, handler, http.MethodPost, "/v1/memory", map[string]any{
		"org_id":            "org-1",
		"scope":             "personal",
		"subject_member_id": "org-1:alice",
		"content":           "Alice backup fact.",
	})
	if personal.Code != http.StatusCreated {
		t.Fatalf("create personal memory status = %d body=%s", personal.Code, personal.Body.String())
	}
	shared := requestJSON(t, handler, http.MethodPost, "/v1/memory", map[string]any{
		"org_id":     "org-1",
		"scope":      "team_shared",
		"team_id":    "org-1:platform",
		"content":    "Shared export fact.",
		"status":     "active",
		"project_id": "project-1",
	})
	if shared.Code != http.StatusCreated {
		t.Fatalf("create shared memory status = %d body=%s", shared.Code, shared.Body.String())
	}

	audit := requestJSON(t, handler, http.MethodGet, "/v1/audit/events?org_id=org-1", nil)
	if audit.Code != http.StatusOK {
		t.Fatalf("list audit status = %d body=%s", audit.Code, audit.Body.String())
	}
	auditBody := decodeBody[map[string][]map[string]any](t, audit)
	if len(auditBody["items"]) == 0 {
		t.Fatal("expected audit events")
	}

	relationship := requestJSON(t, handler, http.MethodPut, "/v1/authz/relationships", map[string]any{
		"org_id":          "org-1",
		"resource_type":   "team",
		"resource_id":     "org-1:platform",
		"relation":        "member",
		"subject_type":    "member",
		"subject_id":      "org-1:alice",
		"idempotency_key": "rel-1",
	})
	if relationship.Code != http.StatusOK {
		t.Fatalf("write relationship status = %d body=%s", relationship.Code, relationship.Body.String())
	}
	check := requestJSON(t, handler, http.MethodPost, "/v1/authz/check", map[string]any{
		"org_id":        "org-1",
		"resource_type": "team",
		"resource_id":   "org-1:platform",
		"permission":    "read",
		"subject_type":  "member",
		"subject_id":    "org-1:alice",
	})
	checkBody := decodeBody[map[string]any](t, check)
	if check.Code != http.StatusOK || checkBody["allowed"] != true {
		t.Fatalf("check body = %#v status=%d", checkBody, check.Code)
	}

	backup := requestJSON(t, handler, http.MethodPost, "/v1/backups/personal/run", map[string]any{
		"org_id":    "org-1",
		"member_id": "org-1:alice",
	})
	if backup.Code != http.StatusCreated {
		t.Fatalf("backup status = %d body=%s", backup.Code, backup.Body.String())
	}
	backupBody := decodeBody[map[string]any](t, backup)
	backupID := backupBody["id"].(string)
	if backupBody["checksum_sha256"] == "" || backupBody["item_count"].(float64) != 1 {
		t.Fatalf("backup body = %#v", backupBody)
	}

	memoryBody := decodeBody[map[string]any](t, personal)
	requestJSON(t, handler, http.MethodDelete, "/v1/memory/"+memoryBody["id"].(string), nil)
	preview := requestJSON(t, handler, http.MethodPost, "/v1/backups/personal/"+backupID+"/restore-preview", map[string]any{
		"member_id": "org-1:alice",
	})
	previewBody := decodeBody[map[string]any](t, preview)
	if preview.Code != http.StatusOK || previewBody["create_count"].(float64) != 1 {
		t.Fatalf("preview body = %#v status=%d", previewBody, preview.Code)
	}
	restore := requestJSON(t, handler, http.MethodPost, "/v1/backups/personal/"+backupID+"/restore-execute", map[string]any{
		"member_id": "org-1:alice",
		"mode":      "merge",
	})
	restoreBody := decodeBody[map[string]any](t, restore)
	if restore.Code != http.StatusOK || restoreBody["restored_count"].(float64) != 1 {
		t.Fatalf("restore body = %#v status=%d", restoreBody, restore.Code)
	}

	exported := requestJSON(t, handler, http.MethodPost, "/v1/exports/org", map[string]any{
		"org_id": "org-1",
	})
	exportBody := decodeBody[map[string]any](t, exported)
	if exported.Code != http.StatusCreated || exportBody["team_shared_count"].(float64) != 1 || exportBody["personal_count"].(float64) != 0 {
		t.Fatalf("export body = %#v status=%d", exportBody, exported.Code)
	}

	tool := requestJSON(t, handler, http.MethodPost, "/v1/tool-policy/evaluate", map[string]any{
		"org_id":     "org-1",
		"member_id":  "org-1:alice",
		"tool_name":  "terminal",
		"risk_level": "destructive",
	})
	toolBody := decodeBody[map[string]any](t, tool)
	if tool.Code != http.StatusOK || toolBody["decision"] != "approval_required" {
		t.Fatalf("tool body = %#v status=%d", toolBody, tool.Code)
	}

	deletion := requestJSON(t, handler, http.MethodPost, "/v1/deletion-requests", map[string]any{
		"org_id":           "org-1",
		"target_member_id": "org-1:alice",
		"requested_by":     "org-1:alice",
		"deletion_scope":   "personal_memory",
		"reason":           "member requested deletion",
	})
	deletionBody := decodeBody[map[string]any](t, deletion)
	if deletion.Code != http.StatusCreated || deletionBody["status"] != "pending" {
		t.Fatalf("deletion body = %#v status=%d", deletionBody, deletion.Code)
	}
	executed := requestJSON(t, handler, http.MethodPost, "/v1/deletion-requests/"+deletionBody["id"].(string)+"/execute", map[string]any{
		"actor_member_id": "org-1:alice",
	})
	executedBody := decodeBody[map[string]any](t, executed)
	if executed.Code != http.StatusOK || executedBody["status"] != "executed" {
		t.Fatalf("executed deletion body = %#v status=%d", executedBody, executed.Code)
	}
}

func TestSpiceDBHTTPAuthzModeFailsReadyzWhenRemoteUnavailable(t *testing.T) {
	remote := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/healthz" {
			t.Fatalf("unexpected remote path %s", r.URL.Path)
		}
		w.WriteHeader(http.StatusServiceUnavailable)
	}))
	defer remote.Close()

	server, err := httpapi.NewServer(config.Config{
		ServiceName:   "team-cloud-go",
		ServiceToken:  "service-token",
		AuthzMode:     "spicedb_http",
		AuthzEndpoint: remote.URL,
		AuthzToken:    "remote-token",
	}, memory.New())
	if err != nil {
		t.Fatalf("NewServer() error = %v", err)
	}

	req := httptest.NewRequest(http.MethodGet, "/readyz", nil)
	rec := httptest.NewRecorder()
	server.ServeHTTP(rec, req)
	if rec.Code != http.StatusServiceUnavailable {
		t.Fatalf("readyz status = %d body=%s", rec.Code, rec.Body.String())
	}
	if !strings.Contains(rec.Body.String(), "authz") {
		t.Fatalf("readyz body should mention authz: %s", rec.Body.String())
	}
}

func TestPersonalBackupUploadsEncryptedJSONLToConfiguredObjectStore(t *testing.T) {
	var uploadedPath string
	var uploadedBody string
	objectStore := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.Method {
		case http.MethodHead:
			w.WriteHeader(http.StatusOK)
		case http.MethodPut:
			uploadedPath = r.URL.Path
			raw := new(bytes.Buffer)
			_, _ = raw.ReadFrom(r.Body)
			uploadedBody = raw.String()
			w.WriteHeader(http.StatusOK)
		default:
			t.Fatalf("unexpected object store method %s", r.Method)
		}
	}))
	defer objectStore.Close()

	server, err := httpapi.NewServer(config.Config{
		ServiceName:                "team-cloud-go",
		ServiceToken:               "team-token",
		BackupObjectMode:           "s3",
		BackupS3Endpoint:           objectStore.URL,
		BackupS3Bucket:             "personal-backups",
		BackupS3Region:             "us-east-1",
		BackupS3AccessKeyID:        "minio",
		BackupS3SecretAccessKey:    "secret",
		BackupEncryptionKey:        "test encryption key",
		BackupRequirePreviewBefore: true,
	}, memory.New())
	if err != nil {
		t.Fatalf("NewServer() error = %v", err)
	}
	requestJSON(t, server, http.MethodPost, "/api/organizations", map[string]string{
		"slug": "org-1",
		"name": "Org 1",
	})
	requestJSON(t, server, http.MethodPost, "/v1/memory", map[string]any{
		"org_id":            "org-1",
		"scope":             "personal",
		"subject_member_id": "org-1:alice",
		"content":           "Alice encrypted backup fact.",
	})

	backup := requestJSON(t, server, http.MethodPost, "/v1/backups/personal/run", map[string]any{
		"org_id":    "org-1",
		"member_id": "org-1:alice",
	})
	body := decodeBody[map[string]any](t, backup)
	if backup.Code != http.StatusCreated {
		t.Fatalf("backup status = %d body=%s", backup.Code, backup.Body.String())
	}
	manifest := body["manifest"].(map[string]any)
	if manifest["object_store"] != "s3" || manifest["encryption"] != "aes-256-gcm" {
		t.Fatalf("manifest = %#v", manifest)
	}
	if uploadedPath == "" || !strings.Contains(uploadedPath, "/personal-backups/org/org-1/member/org-1:alice/personal-memory/") {
		t.Fatalf("uploaded path = %q", uploadedPath)
	}
	if strings.Contains(uploadedBody, "Alice encrypted backup fact") {
		t.Fatalf("uploaded body leaked plaintext: %s", uploadedBody)
	}
}

func TestRestorePreviewValidatesEncryptedObjectStorePayload(t *testing.T) {
	var uploadedBody []byte
	objectStore := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.Method {
		case http.MethodHead:
			w.WriteHeader(http.StatusOK)
		case http.MethodPut:
			raw := new(bytes.Buffer)
			_, _ = raw.ReadFrom(r.Body)
			uploadedBody = raw.Bytes()
			w.WriteHeader(http.StatusOK)
		case http.MethodGet:
			tampered := append([]byte(nil), uploadedBody...)
			if len(tampered) > 0 {
				tampered[len(tampered)-1] ^= 0xff
			}
			_, _ = w.Write(tampered)
		default:
			t.Fatalf("unexpected object store method %s", r.Method)
		}
	}))
	defer objectStore.Close()

	server, err := httpapi.NewServer(config.Config{
		ServiceName:             "team-cloud-go",
		ServiceToken:            "team-token",
		BackupObjectMode:        "s3",
		BackupS3Endpoint:        objectStore.URL,
		BackupS3Bucket:          "personal-backups",
		BackupS3Region:          "us-east-1",
		BackupS3AccessKeyID:     "minio",
		BackupS3SecretAccessKey: "secret",
		BackupEncryptionKey:     "test encryption key",
	}, memory.New())
	if err != nil {
		t.Fatalf("NewServer() error = %v", err)
	}
	requestJSON(t, server, http.MethodPost, "/api/organizations", map[string]string{
		"slug": "org-1",
		"name": "Org 1",
	})
	requestJSON(t, server, http.MethodPost, "/v1/memory", map[string]any{
		"org_id":            "org-1",
		"scope":             "personal",
		"subject_member_id": "org-1:alice",
		"content":           "Alice object restore fact.",
	})
	backup := requestJSON(t, server, http.MethodPost, "/v1/backups/personal/run", map[string]any{
		"org_id":    "org-1",
		"member_id": "org-1:alice",
	})
	backupBody := decodeBody[map[string]any](t, backup)
	backupID := backupBody["id"].(string)

	preview := requestJSON(t, server, http.MethodPost, "/v1/backups/personal/"+backupID+"/restore-preview", map[string]any{
		"member_id": "org-1:alice",
		"mode":      "merge",
	})
	if preview.Code != http.StatusBadRequest || !strings.Contains(preview.Body.String(), "backup_object_checksum_mismatch") {
		t.Fatalf("tampered object preview status = %d body=%s", preview.Code, preview.Body.String())
	}
}

func TestRestoreExecuteRequiresPreviewFirst(t *testing.T) {
	handler := newTestServer(t)
	requestJSON(t, handler, http.MethodPost, "/api/organizations", map[string]string{
		"slug": "org-1",
		"name": "Org 1",
	})
	requestJSON(t, handler, http.MethodPost, "/v1/memory", map[string]any{
		"org_id":            "org-1",
		"scope":             "personal",
		"subject_member_id": "org-1:alice",
		"content":           "Alice restore guard fact.",
	})
	backup := requestJSON(t, handler, http.MethodPost, "/v1/backups/personal/run", map[string]any{
		"org_id":    "org-1",
		"member_id": "org-1:alice",
	})
	backupBody := decodeBody[map[string]any](t, backup)
	backupID := backupBody["id"].(string)

	blocked := requestJSON(t, handler, http.MethodPost, "/v1/backups/personal/"+backupID+"/restore-execute", map[string]any{
		"member_id": "org-1:alice",
		"mode":      "merge",
	})
	if blocked.Code != http.StatusBadRequest {
		t.Fatalf("restore without preview status = %d body=%s", blocked.Code, blocked.Body.String())
	}
	preview := requestJSON(t, handler, http.MethodPost, "/v1/backups/personal/"+backupID+"/restore-preview", map[string]any{
		"member_id": "org-1:alice",
		"mode":      "merge",
	})
	if preview.Code != http.StatusOK {
		t.Fatalf("preview status = %d body=%s", preview.Code, preview.Body.String())
	}
	allowed := requestJSON(t, handler, http.MethodPost, "/v1/backups/personal/"+backupID+"/restore-execute", map[string]any{
		"member_id": "org-1:alice",
		"mode":      "merge",
	})
	if allowed.Code != http.StatusOK {
		t.Fatalf("restore after preview status = %d body=%s", allowed.Code, allowed.Body.String())
	}
}

func TestRestoreModesOverwriteAndArchiveCurrentThenRestore(t *testing.T) {
	t.Run("overwrite replaces current personal memories", func(t *testing.T) {
		handler := newTestServer(t)
		requestJSON(t, handler, http.MethodPost, "/api/organizations", map[string]string{
			"slug": "org-1",
			"name": "Org 1",
		})
		requestJSON(t, handler, http.MethodPost, "/v1/memory", map[string]any{
			"org_id":            "org-1",
			"scope":             "personal",
			"subject_member_id": "org-1:alice",
			"content":           "backup fact",
		})
		backup := requestJSON(t, handler, http.MethodPost, "/v1/backups/personal/run", map[string]any{
			"org_id":    "org-1",
			"member_id": "org-1:alice",
		})
		backupID := decodeBody[map[string]any](t, backup)["id"].(string)
		requestJSON(t, handler, http.MethodPost, "/v1/memory", map[string]any{
			"org_id":            "org-1",
			"scope":             "personal",
			"subject_member_id": "org-1:alice",
			"content":           "current fact",
		})
		requestJSON(t, handler, http.MethodPost, "/v1/backups/personal/"+backupID+"/restore-preview", map[string]any{
			"member_id": "org-1:alice",
			"mode":      "overwrite",
		})
		restore := requestJSON(t, handler, http.MethodPost, "/v1/backups/personal/"+backupID+"/restore-execute", map[string]any{
			"member_id": "org-1:alice",
			"mode":      "overwrite",
		})
		if restore.Code != http.StatusOK {
			t.Fatalf("overwrite restore status = %d body=%s", restore.Code, restore.Body.String())
		}
		list := requestJSON(t, handler, http.MethodGet, "/v1/memory?org_id=org-1&scope=personal&status=active", nil)
		body := decodeBody[map[string][]map[string]any](t, list)
		if len(body["items"]) != 1 || body["items"][0]["content"] != "backup fact" {
			t.Fatalf("overwrite active items = %#v", body["items"])
		}
	})

	t.Run("archive mode preserves current personal memories as archived", func(t *testing.T) {
		handler := newTestServer(t)
		requestJSON(t, handler, http.MethodPost, "/api/organizations", map[string]string{
			"slug": "org-1",
			"name": "Org 1",
		})
		requestJSON(t, handler, http.MethodPost, "/v1/memory", map[string]any{
			"org_id":            "org-1",
			"scope":             "personal",
			"subject_member_id": "org-1:alice",
			"content":           "backup fact",
		})
		backup := requestJSON(t, handler, http.MethodPost, "/v1/backups/personal/run", map[string]any{
			"org_id":    "org-1",
			"member_id": "org-1:alice",
		})
		backupID := decodeBody[map[string]any](t, backup)["id"].(string)
		requestJSON(t, handler, http.MethodPost, "/v1/memory", map[string]any{
			"org_id":            "org-1",
			"scope":             "personal",
			"subject_member_id": "org-1:alice",
			"content":           "current fact",
		})
		requestJSON(t, handler, http.MethodPost, "/v1/backups/personal/"+backupID+"/restore-preview", map[string]any{
			"member_id": "org-1:alice",
			"mode":      "archive_current_then_restore",
		})
		restore := requestJSON(t, handler, http.MethodPost, "/v1/backups/personal/"+backupID+"/restore-execute", map[string]any{
			"member_id": "org-1:alice",
			"mode":      "archive_current_then_restore",
		})
		if restore.Code != http.StatusOK {
			t.Fatalf("archive restore status = %d body=%s", restore.Code, restore.Body.String())
		}
		archived := requestJSON(t, handler, http.MethodGet, "/v1/memory?org_id=org-1&scope=personal&status=archived", nil)
		archivedBody := decodeBody[map[string][]map[string]any](t, archived)
		if len(archivedBody["items"]) != 2 {
			t.Fatalf("archived current items = %#v", archivedBody["items"])
		}
		active := requestJSON(t, handler, http.MethodGet, "/v1/memory?org_id=org-1&scope=personal&status=active", nil)
		activeBody := decodeBody[map[string][]map[string]any](t, active)
		if len(activeBody["items"]) != 1 || activeBody["items"][0]["content"] != "backup fact" {
			t.Fatalf("archive active items = %#v", activeBody["items"])
		}
	})
}

func TestScheduledBackupRunnerRunsEnabledPolicies(t *testing.T) {
	server, err := httpapi.NewServer(config.Config{
		ServiceName:  "team-cloud-go",
		ServiceToken: "team-token",
	}, memory.New())
	if err != nil {
		t.Fatalf("NewServer() error = %v", err)
	}
	requestJSON(t, server, http.MethodPost, "/api/organizations", map[string]string{
		"slug": "org-1",
		"name": "Org 1",
	})
	requestJSON(t, server, http.MethodPost, "/v1/memory", map[string]any{
		"org_id":            "org-1",
		"scope":             "personal",
		"subject_member_id": "org-1:alice",
		"content":           "Scheduled backup fact.",
	})
	requestJSON(t, server, http.MethodPut, "/v1/me/memory-backup-policy", map[string]any{
		"org_id":          "org-1",
		"member_id":       "org-1:alice",
		"cadence":         "daily",
		"enabled":         true,
		"retention_count": 3,
	})

	jobs, err := server.RunScheduledBackups(t.Context())
	if err != nil {
		t.Fatalf("RunScheduledBackups() error = %v", err)
	}
	if len(jobs) != 1 || jobs[0].ItemCount != 1 {
		t.Fatalf("scheduled jobs = %#v", jobs)
	}

	secondRun, err := server.RunScheduledBackups(t.Context())
	if err != nil {
		t.Fatalf("second RunScheduledBackups() error = %v", err)
	}
	if len(secondRun) != 0 {
		t.Fatalf("scheduled backup should respect next_run_at, got %#v", secondRun)
	}
}

func TestBackupRetentionPrunesOlderJobs(t *testing.T) {
	handler := newTestServer(t)
	requestJSON(t, handler, http.MethodPost, "/api/organizations", map[string]string{
		"slug": "org-1",
		"name": "Org 1",
	})
	requestJSON(t, handler, http.MethodPut, "/v1/me/memory-backup-policy", map[string]any{
		"org_id":          "org-1",
		"member_id":       "org-1:alice",
		"cadence":         "daily",
		"enabled":         true,
		"retention_count": 1,
	})
	requestJSON(t, handler, http.MethodPost, "/v1/memory", map[string]any{
		"org_id":            "org-1",
		"scope":             "personal",
		"subject_member_id": "org-1:alice",
		"content":           "first retained fact",
	})
	first := requestJSON(t, handler, http.MethodPost, "/v1/backups/personal/run", map[string]any{
		"org_id":    "org-1",
		"member_id": "org-1:alice",
	})
	firstID := decodeBody[map[string]any](t, first)["id"].(string)
	requestJSON(t, handler, http.MethodPost, "/v1/memory", map[string]any{
		"org_id":            "org-1",
		"scope":             "personal",
		"subject_member_id": "org-1:alice",
		"content":           "second retained fact",
	})
	second := requestJSON(t, handler, http.MethodPost, "/v1/backups/personal/run", map[string]any{
		"org_id":    "org-1",
		"member_id": "org-1:alice",
	})
	if second.Code != http.StatusCreated {
		t.Fatalf("second backup status = %d body=%s", second.Code, second.Body.String())
	}

	firstDetail := requestJSON(t, handler, http.MethodGet, "/v1/backups/personal/"+firstID, nil)
	firstBody := decodeBody[map[string]any](t, firstDetail)
	if firstDetail.Code != http.StatusOK || firstBody["status"] != "pruned" {
		t.Fatalf("first backup should be pruned by retention: status=%d body=%#v", firstDetail.Code, firstBody)
	}
}

func TestJWTBusinessAPIsFailClosedForPayloadSpoofingAndTeamMemory(t *testing.T) {
	privateKey, jwksURL := startJWKS(t)
	handler := newJWTAndServiceServer(t, jwksURL)
	requestJSON(t, handler, http.MethodPost, "/api/organizations", map[string]string{
		"slug": "org-1",
		"name": "Org 1",
	})
	requestJSON(t, handler, http.MethodPost, "/api/organizations", map[string]string{
		"slug": "org-2",
		"name": "Org 2",
	})
	requestJSON(t, handler, http.MethodPost, "/api/organizations/org-1/teams", map[string]string{
		"slug": "platform",
		"name": "Platform",
	})
	requestJSON(t, handler, http.MethodPost, "/v1/memory", map[string]any{
		"org_id":     "org-1",
		"scope":      "team_shared",
		"team_id":    "org-1:platform",
		"project_id": "project-1",
		"content":    "Team-only deployment memory.",
		"status":     "active",
	})

	token := signRS256JWT(t, privateKey, map[string]any{
		"iss":              "https://casdoor.example",
		"aud":              "hermes-team-cloud",
		"sub":              "casdoor-user-alice",
		"email":            "alice@example.com",
		"hermes_org_id":    "org-1",
		"hermes_member_id": "org-1:alice",
		"exp":              time.Now().Add(time.Hour).Unix(),
	})

	spoofed := requestJSONWithAuth(t, handler, http.MethodPost, "/v1/memory", map[string]any{
		"org_id":            "org-2",
		"scope":             "personal",
		"subject_member_id": "org-1:alice",
		"content":           "spoofed memory",
	}, "Bearer "+token)
	if spoofed.Code != http.StatusForbidden {
		t.Fatalf("spoofed memory status = %d body=%s", spoofed.Code, spoofed.Body.String())
	}

	deniedPrefetch := requestJSONWithAuth(t, handler, http.MethodPost, "/v1/memory/prefetch", map[string]any{
		"query":            "deployment",
		"org_id":           "org-1",
		"member_id":        "org-1:alice",
		"team_id":          "org-1:platform",
		"project_id":       "project-1",
		"include_personal": false,
	}, "Bearer "+token)
	if deniedPrefetch.Code != http.StatusOK {
		t.Fatalf("denied prefetch status = %d body=%s", deniedPrefetch.Code, deniedPrefetch.Body.String())
	}
	deniedBody := decodeBody[map[string][]map[string]any](t, deniedPrefetch)
	if len(deniedBody["partitions"]) != 0 {
		t.Fatalf("team_shared should be filtered without authz: %#v", deniedBody["partitions"])
	}

	relationship := requestJSON(t, handler, http.MethodPut, "/v1/authz/relationships", map[string]any{
		"org_id":        "org-1",
		"resource_type": "team",
		"resource_id":   "org-1:platform",
		"relation":      "member",
		"subject_type":  "member",
		"subject_id":    "org-1:alice",
	})
	if relationship.Code != http.StatusOK {
		t.Fatalf("write team relationship status = %d body=%s", relationship.Code, relationship.Body.String())
	}
	allowedPrefetch := requestJSONWithAuth(t, handler, http.MethodPost, "/v1/memory/prefetch", map[string]any{
		"query":            "deployment",
		"org_id":           "org-1",
		"member_id":        "org-1:alice",
		"team_id":          "org-1:platform",
		"project_id":       "project-1",
		"include_personal": false,
	}, "Bearer "+token)
	allowedBody := decodeBody[map[string][]map[string]any](t, allowedPrefetch)
	if allowedPrefetch.Code != http.StatusOK || len(allowedBody["partitions"]) != 1 {
		t.Fatalf("team_shared should pass with authz: status=%d body=%#v", allowedPrefetch.Code, allowedBody)
	}
}

func TestJWTMemberAdministrationRequiresOrgOwnerRelationship(t *testing.T) {
	privateKey, jwksURL := startJWKS(t)
	handler := newJWTAndServiceServer(t, jwksURL)
	requestJSON(t, handler, http.MethodPost, "/api/organizations", map[string]string{
		"slug": "org-1",
		"name": "Org 1",
	})
	token := signRS256JWT(t, privateKey, map[string]any{
		"iss":              "https://casdoor.example",
		"aud":              "hermes-team-cloud",
		"sub":              "casdoor-user-alice",
		"hermes_org_id":    "org-1",
		"hermes_member_id": "org-1:alice",
		"exp":              time.Now().Add(time.Hour).Unix(),
	})

	denied := requestJSONWithAuth(t, handler, http.MethodPost, "/api/organizations/org-1/members/invite", map[string]string{
		"email":   "bob@example.com",
		"user_id": "bob",
	}, "Bearer "+token)
	if denied.Code != http.StatusForbidden {
		t.Fatalf("invite without owner status = %d body=%s", denied.Code, denied.Body.String())
	}

	relationship := requestJSON(t, handler, http.MethodPut, "/v1/authz/relationships", map[string]any{
		"org_id":        "org-1",
		"resource_type": "organization",
		"resource_id":   "org-1",
		"relation":      "owner",
		"subject_type":  "member",
		"subject_id":    "org-1:alice",
	})
	if relationship.Code != http.StatusOK {
		t.Fatalf("write org owner relationship status = %d body=%s", relationship.Code, relationship.Body.String())
	}
	allowed := requestJSONWithAuth(t, handler, http.MethodPost, "/api/organizations/org-1/members/invite", map[string]string{
		"email":   "bob@example.com",
		"user_id": "bob",
	}, "Bearer "+token)
	if allowed.Code != http.StatusCreated {
		t.Fatalf("invite with owner status = %d body=%s", allowed.Code, allowed.Body.String())
	}
}

func TestJWTGovernanceAPIsRequireAdminRelationship(t *testing.T) {
	privateKey, jwksURL := startJWKS(t)
	handler := newJWTAndServiceServer(t, jwksURL)
	requestJSON(t, handler, http.MethodPost, "/api/organizations", map[string]string{
		"slug": "org-1",
		"name": "Org 1",
	})
	team := requestJSON(t, handler, http.MethodPost, "/api/organizations/org-1/teams", map[string]string{
		"slug": "platform",
		"name": "Platform",
	})
	if team.Code != http.StatusCreated {
		t.Fatalf("create team status = %d body=%s", team.Code, team.Body.String())
	}
	created := requestJSON(t, handler, http.MethodPost, "/v1/memory", map[string]any{
		"org_id":     "org-1",
		"scope":      "team_shared",
		"team_id":    "org-1:platform",
		"content":    "Sensitive team memory awaiting review.",
		"status":     "pending_review",
		"project_id": "project-1",
	})
	if created.Code != http.StatusCreated {
		t.Fatalf("create review memory status = %d body=%s", created.Code, created.Body.String())
	}
	reviews := requestJSON(t, handler, http.MethodGet, "/v1/memory/review?org_id=org-1", nil)
	reviewBody := decodeBody[map[string][]map[string]any](t, reviews)
	reviewID := reviewBody["items"][0]["id"].(string)

	memberToken := signRS256JWT(t, privateKey, map[string]any{
		"iss":              "https://casdoor.example",
		"aud":              "hermes-team-cloud",
		"sub":              "casdoor-user-alice",
		"hermes_org_id":    "org-1",
		"hermes_member_id": "org-1:alice",
		"exp":              time.Now().Add(time.Hour).Unix(),
	})

	relationship := requestJSONWithAuth(t, handler, http.MethodPut, "/v1/authz/relationships", map[string]any{
		"org_id":        "org-1",
		"resource_type": "organization",
		"resource_id":   "org-1",
		"relation":      "owner",
		"subject_type":  "member",
		"subject_id":    "org-1:alice",
	}, "Bearer "+memberToken)
	if relationship.Code != http.StatusForbidden {
		t.Fatalf("ordinary member wrote relationship status = %d body=%s", relationship.Code, relationship.Body.String())
	}

	audit := requestJSONWithAuth(t, handler, http.MethodGet, "/v1/audit/events?org_id=org-1", nil, "Bearer "+memberToken)
	if audit.Code != http.StatusForbidden {
		t.Fatalf("ordinary member read audit status = %d body=%s", audit.Code, audit.Body.String())
	}

	reviewList := requestJSONWithAuth(t, handler, http.MethodGet, "/v1/memory/review?org_id=org-1", nil, "Bearer "+memberToken)
	if reviewList.Code != http.StatusForbidden {
		t.Fatalf("ordinary member listed reviews status = %d body=%s", reviewList.Code, reviewList.Body.String())
	}

	reviewApprove := requestJSONWithAuth(t, handler, http.MethodPost, "/v1/memory/review/"+reviewID+"/approve", map[string]any{
		"actor_member_id": "org-1:alice",
	}, "Bearer "+memberToken)
	if reviewApprove.Code != http.StatusForbidden {
		t.Fatalf("ordinary member approved review status = %d body=%s", reviewApprove.Code, reviewApprove.Body.String())
	}

	adminToken := signRS256JWT(t, privateKey, map[string]any{
		"iss":              "https://casdoor.example",
		"aud":              "hermes-team-cloud",
		"sub":              "casdoor-user-admin",
		"hermes_org_id":    "org-1",
		"hermes_member_id": "org-1:admin",
		"exp":              time.Now().Add(time.Hour).Unix(),
	})
	owner := requestJSON(t, handler, http.MethodPut, "/v1/authz/relationships", map[string]any{
		"org_id":        "org-1",
		"resource_type": "organization",
		"resource_id":   "org-1",
		"relation":      "owner",
		"subject_type":  "member",
		"subject_id":    "org-1:admin",
	})
	if owner.Code != http.StatusOK {
		t.Fatalf("seed owner status = %d body=%s", owner.Code, owner.Body.String())
	}
	adminAudit := requestJSONWithAuth(t, handler, http.MethodGet, "/v1/audit/events?org_id=org-1", nil, "Bearer "+adminToken)
	if adminAudit.Code != http.StatusOK {
		t.Fatalf("admin audit status = %d body=%s", adminAudit.Code, adminAudit.Body.String())
	}
	adminReview := requestJSONWithAuth(t, handler, http.MethodGet, "/v1/memory/review?org_id=org-1", nil, "Bearer "+adminToken)
	if adminReview.Code != http.StatusOK {
		t.Fatalf("admin review list status = %d body=%s", adminReview.Code, adminReview.Body.String())
	}
}

func TestJWTTenantBackupDeletionAndRuntimeGuards(t *testing.T) {
	privateKey, jwksURL := startJWKS(t)
	handler := newJWTAndServiceServer(t, jwksURL)
	requestJSON(t, handler, http.MethodPost, "/api/organizations", map[string]string{
		"slug": "org-1",
		"name": "Org 1",
	})
	requestJSON(t, handler, http.MethodPost, "/api/organizations", map[string]string{
		"slug": "org-2",
		"name": "Org 2",
	})
	requestJSON(t, handler, http.MethodPost, "/api/organizations/org-1/teams", map[string]string{
		"slug": "platform",
		"name": "Platform",
	})
	requestJSON(t, handler, http.MethodPost, "/v1/memory", map[string]any{
		"org_id":            "org-1",
		"scope":             "personal",
		"subject_member_id": "org-1:alice",
		"content":           "Alice private backup detail.",
	})
	backup := requestJSON(t, handler, http.MethodPost, "/v1/backups/personal/run", map[string]any{
		"org_id":    "org-1",
		"member_id": "org-1:alice",
	})
	backupBody := decodeBody[map[string]any](t, backup)
	backupID := backupBody["id"].(string)
	deletion := requestJSON(t, handler, http.MethodPost, "/v1/deletion-requests", map[string]any{
		"org_id":           "org-1",
		"target_member_id": "org-1:alice",
		"requested_by":     "org-1:alice",
		"deletion_scope":   "personal_memory",
		"reason":           "privacy request",
	})
	deletionBody := decodeBody[map[string]any](t, deletion)
	session := requestJSON(t, handler, http.MethodPost, "/v1/sessions", map[string]any{
		"org_id":          "org-1",
		"team_id":         "org-1:platform",
		"owner_member_id": "org-1:alice",
		"title":           "Alice session",
	})
	sessionBody := decodeBody[map[string]any](t, session)

	aliceToken := signRS256JWT(t, privateKey, map[string]any{
		"iss":              "https://casdoor.example",
		"aud":              "hermes-team-cloud",
		"sub":              "casdoor-user-alice",
		"hermes_org_id":    "org-1",
		"hermes_member_id": "org-1:alice",
		"exp":              time.Now().Add(time.Hour).Unix(),
	})
	bobToken := signRS256JWT(t, privateKey, map[string]any{
		"iss":              "https://casdoor.example",
		"aud":              "hermes-team-cloud",
		"sub":              "casdoor-user-bob",
		"hermes_org_id":    "org-1",
		"hermes_member_id": "org-1:bob",
		"exp":              time.Now().Add(time.Hour).Unix(),
	})

	orgs := requestJSONWithAuth(t, handler, http.MethodGet, "/api/organizations", nil, "Bearer "+aliceToken)
	orgBody := decodeBody[map[string][]map[string]any](t, orgs)
	if orgs.Code != http.StatusOK || len(orgBody["items"]) != 1 || orgBody["items"][0]["id"] != "org-1" {
		t.Fatalf("tenant scoped org list status=%d body=%#v", orgs.Code, orgBody)
	}

	bobBackup := requestJSONWithAuth(t, handler, http.MethodGet, "/v1/backups/personal/"+backupID, nil, "Bearer "+bobToken)
	if bobBackup.Code != http.StatusForbidden {
		t.Fatalf("bob read alice backup status = %d body=%s", bobBackup.Code, bobBackup.Body.String())
	}
	aliceBackup := requestJSONWithAuth(t, handler, http.MethodGet, "/v1/backups/personal/"+backupID, nil, "Bearer "+aliceToken)
	aliceBackupBody := decodeBody[map[string]any](t, aliceBackup)
	if aliceBackup.Code != http.StatusOK {
		t.Fatalf("alice backup status = %d body=%s", aliceBackup.Code, aliceBackup.Body.String())
	}
	if _, ok := aliceBackupBody["items"]; ok {
		t.Fatalf("backup detail should not expose memory items: %#v", aliceBackupBody)
	}

	bobDelete := requestJSONWithAuth(t, handler, http.MethodPost, "/v1/deletion-requests/"+deletionBody["id"].(string)+"/execute", map[string]any{
		"actor_member_id": "org-1:bob",
	}, "Bearer "+bobToken)
	if bobDelete.Code != http.StatusForbidden {
		t.Fatalf("bob executed alice deletion status = %d body=%s", bobDelete.Code, bobDelete.Body.String())
	}

	bobEvent := requestJSONWithAuth(t, handler, http.MethodPost, "/v1/runtime/events", map[string]any{
		"org_id":     "org-1",
		"session_id": sessionBody["id"].(string),
		"event_type": "tool.start",
		"payload":    map[string]any{"tool": "terminal"},
	}, "Bearer "+bobToken)
	if bobEvent.Code != http.StatusForbidden {
		t.Fatalf("bob wrote alice runtime event status = %d body=%s", bobEvent.Code, bobEvent.Body.String())
	}
	aliceEvent := requestJSONWithAuth(t, handler, http.MethodPost, "/v1/runtime/events", map[string]any{
		"org_id":     "org-1",
		"session_id": sessionBody["id"].(string),
		"event_type": "tool.start",
		"payload":    map[string]any{"tool": "terminal"},
	}, "Bearer "+aliceToken)
	if aliceEvent.Code != http.StatusCreated {
		t.Fatalf("alice runtime event status = %d body=%s", aliceEvent.Code, aliceEvent.Body.String())
	}
}

func newJWTServer(t *testing.T, jwksURL string) http.Handler {
	t.Helper()
	server, err := httpapi.NewServer(config.Config{
		ServiceName:     "team-cloud-go",
		CasdoorIssuer:   "https://casdoor.example",
		CasdoorAudience: "hermes-team-cloud",
		CasdoorJWKSURL:  jwksURL,
	}, memory.New())
	if err != nil {
		t.Fatalf("NewServer() error = %v", err)
	}
	return server
}

func newJWTAndServiceServer(t *testing.T, jwksURL string) http.Handler {
	t.Helper()
	server, err := httpapi.NewServer(config.Config{
		ServiceName:     "team-cloud-go",
		ServiceToken:    "team-token",
		CasdoorIssuer:   "https://casdoor.example",
		CasdoorAudience: "hermes-team-cloud",
		CasdoorJWKSURL:  jwksURL,
	}, memory.New())
	if err != nil {
		t.Fatalf("NewServer() error = %v", err)
	}
	return server
}

func requestJSONWithAuth(t *testing.T, handler http.Handler, method, path string, body any, auth string) *httptest.ResponseRecorder {
	t.Helper()
	var payload bytes.Buffer
	if body != nil {
		if err := json.NewEncoder(&payload).Encode(body); err != nil {
			t.Fatalf("encode request body: %v", err)
		}
	}
	req := httptest.NewRequest(method, path, &payload)
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", auth)
	rec := httptest.NewRecorder()
	handler.ServeHTTP(rec, req)
	return rec
}

func startJWKS(t *testing.T) (*rsa.PrivateKey, string) {
	t.Helper()
	privateKey, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		t.Fatalf("generate rsa key: %v", err)
	}
	jwks := map[string]any{
		"keys": []map[string]any{{
			"kty": "RSA",
			"use": "sig",
			"kid": "test-key",
			"alg": "RS256",
			"n":   base64.RawURLEncoding.EncodeToString(privateKey.PublicKey.N.Bytes()),
			"e":   base64.RawURLEncoding.EncodeToString(big.NewInt(int64(privateKey.PublicKey.E)).Bytes()),
		}},
	}
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		_ = json.NewEncoder(w).Encode(jwks)
	}))
	t.Cleanup(server.Close)
	return privateKey, server.URL
}

func signRS256JWT(t *testing.T, privateKey *rsa.PrivateKey, claims map[string]any) string {
	t.Helper()
	header := map[string]any{"alg": "RS256", "typ": "JWT", "kid": "test-key"}
	encodedHeader := mustBase64JSON(t, header)
	encodedClaims := mustBase64JSON(t, claims)
	signingInput := encodedHeader + "." + encodedClaims
	sum := sha256.Sum256([]byte(signingInput))
	signature, err := rsa.SignPKCS1v15(rand.Reader, privateKey, crypto.SHA256, sum[:])
	if err != nil {
		t.Fatalf("sign jwt: %v", err)
	}
	return signingInput + "." + base64.RawURLEncoding.EncodeToString(signature)
}

func mustBase64JSON(t *testing.T, value any) string {
	t.Helper()
	raw, err := json.Marshal(value)
	if err != nil {
		t.Fatalf("marshal json: %v", err)
	}
	return strings.TrimRight(base64.URLEncoding.EncodeToString(raw), "=")
}
