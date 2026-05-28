package httpapi_test

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"hermes-agent/team_cloud/internal/config"
)

func initializedDashboardV2Server(t *testing.T) http.Handler {
	t.Helper()
	minio := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodHead || r.URL.Path != "/personal-backups" {
			t.Fatalf("unexpected minio probe %s %s", r.Method, r.URL.Path)
		}
		w.WriteHeader(http.StatusOK)
	}))
	t.Cleanup(minio.Close)
	handler := newBootstrapV2Server(t, config.Config{
		ServiceName:             "team-cloud-go",
		DatabaseURL:             "postgres://hermes:secret@postgres:5432/hermes_team_cloud?sslmode=disable",
		BackupObjectMode:        "minio",
		BackupS3Endpoint:        minio.URL,
		BackupS3Bucket:          "personal-backups",
		BackupS3AccessKeyID:     "minio",
		BackupS3SecretAccessKey: "secret",
		BackupEncryptionKey:     "backup-key",
		DashboardEnabled:        true,
		DashboardDir:            "dashboard/out",
	})
	created := requestJSON(t, handler, http.MethodPost, "/v1/bootstrap/super-admin", map[string]any{
		"org_slug":           "hermes-labs",
		"org_name":           "Hermes Labs",
		"admin_email":        "owner@example.com",
		"admin_display_name": "Owner Example",
		"admin_user_id":      "owner",
		"admin_password":     "correct horse battery staple",
	})
	if created.Code != http.StatusCreated {
		t.Fatalf("bootstrap create status = %d body=%s", created.Code, created.Body.String())
	}
	return handler
}

func dashboardLogin(t *testing.T, handler http.Handler, userID, password string) string {
	t.Helper()
	login := requestJSONWithAuth(t, handler, http.MethodPost, "/v1/auth/login", map[string]any{
		"org_id":   "hermes-labs",
		"user_id":  userID,
		"password": password,
	}, "")
	if login.Code != http.StatusOK {
		t.Fatalf("login status = %d body=%s", login.Code, login.Body.String())
	}
	body := decodeBody[map[string]any](t, login)
	token, _ := body["token"].(string)
	if token == "" || strings.HasPrefix(token, "hermes-dashboard-v1.") || strings.Contains(token, ".") {
		t.Fatalf("dashboard token should be opaque session token, got %q", token)
	}
	return token
}

func TestDashboardSessionTokenIsRequiredForProtectedAPIs(t *testing.T) {
	handler := initializedDashboardV2Server(t)

	missing := requestJSONWithAuth(t, handler, http.MethodGet, "/api/organizations", nil, "")
	if missing.Code != http.StatusUnauthorized {
		t.Fatalf("missing token status = %d body=%s", missing.Code, missing.Body.String())
	}

	random := requestJSONWithAuth(t, handler, http.MethodGet, "/api/organizations", nil, "Bearer hcs_random")
	if random.Code != http.StatusUnauthorized {
		t.Fatalf("random token status = %d body=%s", random.Code, random.Body.String())
	}

	token := dashboardLogin(t, handler, "owner", "correct horse battery staple")
	allowed := requestJSONWithAuth(t, handler, http.MethodGet, "/api/organizations", nil, "Bearer "+token)
	if allowed.Code != http.StatusOK {
		t.Fatalf("session token status = %d body=%s", allowed.Code, allowed.Body.String())
	}
}

func TestDashboardLoginAndDirectMemberCreationRoleLimits(t *testing.T) {
	handler := initializedDashboardV2Server(t)
	superToken := dashboardLogin(t, handler, "owner", "correct horse battery staple")

	admin := requestJSONWithAuth(t, handler, http.MethodPost, "/api/organizations/hermes-labs/members", map[string]any{
		"email":        "admin@example.com",
		"display_name": "Admin Example",
		"user_id":      "admin",
		"role":         "admin",
		"password":     "admin password",
	}, "Bearer "+superToken)
	if admin.Code != http.StatusCreated {
		t.Fatalf("super admin create admin status = %d body=%s", admin.Code, admin.Body.String())
	}
	adminBody := decodeBody[map[string]any](t, admin)
	if adminBody["role"] != "admin" || adminBody["status"] != "active" {
		t.Fatalf("admin member body = %#v", adminBody)
	}
	if _, ok := adminBody["password_hash"]; ok {
		t.Fatalf("member response leaked password hash: %#v", adminBody)
	}

	adminToken := dashboardLogin(t, handler, "admin", "admin password")
	denied := requestJSONWithAuth(t, handler, http.MethodPost, "/api/organizations/hermes-labs/members", map[string]any{
		"email":        "second-admin@example.com",
		"display_name": "Second Admin",
		"user_id":      "second-admin",
		"role":         "admin",
		"password":     "admin password",
	}, "Bearer "+adminToken)
	if denied.Code != http.StatusForbidden {
		t.Fatalf("admin creating admin status = %d body=%s", denied.Code, denied.Body.String())
	}

	user := requestJSONWithAuth(t, handler, http.MethodPost, "/api/organizations/hermes-labs/members", map[string]any{
		"email":        "alice@example.com",
		"display_name": "Alice",
		"user_id":      "alice",
		"role":         "user",
		"password":     "alice password",
	}, "Bearer "+adminToken)
	if user.Code != http.StatusCreated {
		t.Fatalf("admin create user status = %d body=%s", user.Code, user.Body.String())
	}
	userBody := decodeBody[map[string]any](t, user)
	if userBody["role"] != "user" || userBody["status"] != "active" {
		t.Fatalf("user member body = %#v", userBody)
	}

	updated := requestJSONWithAuth(t, handler, http.MethodPatch, "/api/organizations/hermes-labs/members/hermes-labs:alice", map[string]any{
		"email":        "alice.ops@example.com",
		"display_name": "Alice Ops",
	}, "Bearer "+adminToken)
	if updated.Code != http.StatusOK {
		t.Fatalf("admin update user status = %d body=%s", updated.Code, updated.Body.String())
	}
	updatedBody := decodeBody[map[string]any](t, updated)
	if updatedBody["email"] != "alice.ops@example.com" || updatedBody["display_name"] != "Alice Ops" {
		t.Fatalf("updated member body = %#v", updatedBody)
	}

	disableSuperAdmin := requestJSONWithAuth(t, handler, http.MethodPatch, "/api/organizations/hermes-labs/members/hermes-labs:owner/disable", nil, "Bearer "+superToken)
	if disableSuperAdmin.Code != http.StatusForbidden {
		t.Fatalf("disable super admin status = %d body=%s", disableSuperAdmin.Code, disableSuperAdmin.Body.String())
	}
}
