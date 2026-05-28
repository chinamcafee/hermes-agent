package httpapi_test

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"hermes-agent/team_cloud/internal/config"
	"hermes-agent/team_cloud/internal/httpapi"
	"hermes-agent/team_cloud/internal/store/memory"
)

func newBootstrapV2Server(t *testing.T, cfg config.Config) http.Handler {
	t.Helper()
	if cfg.ServiceName == "" {
		cfg.ServiceName = "team-cloud-go"
	}
	server, err := httpapi.NewServer(cfg, memory.New())
	if err != nil {
		t.Fatalf("NewServer() error = %v", err)
	}
	return server
}

func TestBootstrapStatusReportsUninitializedAndReadyChecks(t *testing.T) {
	handler := newTestServer(t)
	rec := httptest.NewRecorder()

	handler.ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/v1/bootstrap/status", nil))

	if rec.Code != http.StatusOK {
		t.Fatalf("bootstrap status code = %d body=%s", rec.Code, rec.Body.String())
	}
	body := decodeBody[map[string]any](t, rec)
	if body["initialized"] != false {
		t.Fatalf("initialized = %#v", body["initialized"])
	}
	if body["service"] != "team-cloud-go" {
		t.Fatalf("service = %#v", body["service"])
	}
	if body["organization_count"].(float64) != 0 || body["owner_count"].(float64) != 0 {
		t.Fatalf("unexpected counts: %#v", body)
	}
	checks, ok := body["checks"].(map[string]any)
	if !ok || checks["backend"] != true || checks["authz"] != true {
		t.Fatalf("checks = %#v", body["checks"])
	}
}

func TestBootstrapStatusReportsDashboardV2RequiredConfiguration(t *testing.T) {
	handler := newBootstrapV2Server(t, config.Config{
		ServiceName:      "team-cloud-go",
		DashboardEnabled: true,
		DashboardDir:     "dashboard/out",
	})

	rec := httptest.NewRecorder()
	handler.ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/v1/bootstrap/status", nil))

	if rec.Code != http.StatusOK {
		t.Fatalf("bootstrap status code = %d body=%s", rec.Code, rec.Body.String())
	}
	body := decodeBody[map[string]any](t, rec)
	checks := body["checks"].(map[string]any)
	if _, ok := checks["service_token_configured"]; ok {
		t.Fatalf("bootstrap status must not expose service token checks: %#v", checks)
	}
	if checks["postgres_configured"] != false {
		t.Fatalf("postgres_configured = %#v", checks["postgres_configured"])
	}
	if checks["minio_configured"] != false {
		t.Fatalf("minio_configured = %#v", checks["minio_configured"])
	}
	if checks["backup_object_store"] != true {
		t.Fatalf("database-mode backup object store must be optional, got %#v", checks["backup_object_store"])
	}
	if _, ok := body["team_count"]; ok {
		t.Fatalf("bootstrap status must not expose retired workgroup counts: %#v", body)
	}
	if body["super_admin_count"].(float64) != 0 {
		t.Fatalf("unexpected bootstrap v2 counts: %#v", body)
	}
	if body["initialized"] != false {
		t.Fatalf("initialized should stay false until config, team space, and super admin are complete: %#v", body)
	}
}

func TestBootstrapSuperAdminCreatesOwnerWithoutServiceTokenAndRejectsRepeatedInitialization(t *testing.T) {
	minio := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodHead || r.URL.Path != "/personal-backups" {
			t.Fatalf("unexpected minio probe %s %s", r.Method, r.URL.Path)
		}
		w.WriteHeader(http.StatusOK)
	}))
	defer minio.Close()
	handler := newBootstrapV2Server(t, config.Config{
		ServiceName:                "team-cloud-go",
		DatabaseURL:                "postgres://hermes:secret@postgres:5432/hermes_team_cloud?sslmode=disable",
		BackupObjectMode:           "minio",
		BackupS3Endpoint:           minio.URL,
		BackupS3Bucket:             "personal-backups",
		BackupS3AccessKeyID:        "minio",
		BackupS3SecretAccessKey:    "secret",
		BackupEncryptionKey:        "backup-key",
		DashboardEnabled:           true,
		DashboardDir:               "dashboard/out",
		BackupSchedulerEnabled:     true,
		BackupRequirePreviewBefore: true,
	})

	created := requestJSONWithAuth(t, handler, http.MethodPost, "/v1/bootstrap/super-admin", map[string]any{
		"org_slug":           "hermes-labs",
		"org_name":           "Hermes Labs",
		"admin_email":        "owner@example.com",
		"admin_display_name": "Owner Example",
		"admin_user_id":      "owner",
		"admin_password":     "correct horse battery staple",
	}, "")
	if created.Code != http.StatusCreated {
		t.Fatalf("bootstrap create status = %d body=%s", created.Code, created.Body.String())
	}
	createdBody := decodeBody[map[string]any](t, created)
	org := createdBody["organization"].(map[string]any)
	member := createdBody["member"].(map[string]any)
	if _, ok := createdBody["team"]; ok {
		t.Fatalf("bootstrap response must not create a default workgroup: %#v", createdBody)
	}
	if org["id"] != "hermes-labs" || member["role"] != "super_admin" || member["id"] != "hermes-labs:owner" || member["status"] != "active" {
		t.Fatalf("bootstrap create body = %#v", createdBody)
	}
	if _, ok := member["password_hash"]; ok {
		t.Fatalf("bootstrap response leaked password hash: %#v", member)
	}

	status := httptest.NewRecorder()
	handler.ServeHTTP(status, httptest.NewRequest(http.MethodGet, "/v1/bootstrap/status", nil))
	statusBody := decodeBody[map[string]any](t, status)
	if _, ok := statusBody["team_count"]; ok {
		t.Fatalf("bootstrap status must not expose retired workgroup counts after create: %#v", statusBody)
	}
	if status.Code != http.StatusOK || statusBody["initialized"] != true || statusBody["super_admin_count"].(float64) != 1 {
		t.Fatalf("bootstrap status after create = %#v status=%d", statusBody, status.Code)
	}

	token := dashboardLogin(t, handler, "owner", "correct horse battery staple")
	check := requestJSONWithAuth(t, handler, http.MethodPost, "/v1/authz/check", map[string]any{
		"org_id":        "hermes-labs",
		"resource_type": "organization",
		"resource_id":   "hermes-labs",
		"permission":    "manage",
		"subject_type":  "member",
		"subject_id":    "hermes-labs:owner",
	}, "Bearer "+token)
	checkBody := decodeBody[map[string]any](t, check)
	if check.Code != http.StatusOK || checkBody["allowed"] != true {
		t.Fatalf("owner relationship check body = %#v status=%d", checkBody, check.Code)
	}

	repeated := requestJSONWithAuth(t, handler, http.MethodPost, "/v1/bootstrap/super-admin", map[string]any{
		"org_slug":           "other",
		"org_name":           "Other",
		"admin_email":        "other@example.com",
		"admin_display_name": "Other Owner",
		"admin_user_id":      "other",
		"admin_password":     "correct horse battery staple",
	}, "")
	if repeated.Code != http.StatusConflict {
		t.Fatalf("repeated bootstrap status = %d body=%s", repeated.Code, repeated.Body.String())
	}
}

func TestBootstrapRemoteAuthzFailureDoesNotPersistInitializedData(t *testing.T) {
	authz := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/healthz":
			w.WriteHeader(http.StatusOK)
		case "/v1/relationships/write":
			http.Error(w, "remote_validation_failed", http.StatusBadRequest)
		default:
			t.Fatalf("unexpected authz path %s", r.URL.Path)
		}
	}))
	defer authz.Close()
	handler := newBootstrapV2Server(t, config.Config{
		ServiceName:                "team-cloud-go",
		DatabaseURL:                "postgres://hermes:secret@postgres:5432/hermes_team_cloud?sslmode=disable",
		AuthzMode:                  "spicedb_http",
		AuthzEndpoint:              authz.URL,
		AuthzToken:                 "token",
		BackupObjectMode:           "database",
		DashboardEnabled:           true,
		DashboardDir:               "dashboard/out",
		BackupSchedulerEnabled:     true,
		BackupRequirePreviewBefore: true,
	})

	failed := requestJSONWithAuth(t, handler, http.MethodPost, "/v1/bootstrap/super-admin", map[string]any{
		"org_name":           "Hermes Labs",
		"admin_email":        "owner@example.com",
		"admin_display_name": "Owner Example",
		"admin_user_id":      "owner",
		"admin_password":     "correct horse battery staple",
	}, "")
	if failed.Code != http.StatusServiceUnavailable || !strings.Contains(failed.Body.String(), "remote_validation_failed") {
		t.Fatalf("bootstrap authz failure status = %d body=%s", failed.Code, failed.Body.String())
	}

	status := httptest.NewRecorder()
	handler.ServeHTTP(status, httptest.NewRequest(http.MethodGet, "/v1/bootstrap/status", nil))
	statusBody := decodeBody[map[string]any](t, status)
	if statusBody["initialized"] != false || statusBody["organization_count"].(float64) != 0 || statusBody["super_admin_count"].(float64) != 0 {
		t.Fatalf("remote authz failure persisted initialized data: %#v", statusBody)
	}
}
