package httpapi_test

import (
	"net/http"
	"net/http/httptest"
	"testing"
)

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

func TestBootstrapSuperAdminRequiresServiceToken(t *testing.T) {
	handler := newTestServer(t)
	rec := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodPost, "/v1/bootstrap/super-admin", nil)
	req.Header.Set("Content-Type", "application/json")

	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusUnauthorized {
		t.Fatalf("missing service token status = %d body=%s", rec.Code, rec.Body.String())
	}
}

func TestBootstrapSuperAdminCreatesOwnerAndRejectsRepeatedInitialization(t *testing.T) {
	handler := newTestServer(t)

	created := requestJSON(t, handler, http.MethodPost, "/v1/bootstrap/super-admin", map[string]any{
		"org_slug":           "hermes-labs",
		"org_name":           "Hermes Labs",
		"admin_email":        "owner@example.com",
		"admin_display_name": "Owner Example",
		"admin_user_id":      "owner",
	})
	if created.Code != http.StatusCreated {
		t.Fatalf("bootstrap create status = %d body=%s", created.Code, created.Body.String())
	}
	createdBody := decodeBody[map[string]any](t, created)
	org := createdBody["organization"].(map[string]any)
	member := createdBody["member"].(map[string]any)
	if org["id"] != "hermes-labs" || member["role"] != "owner" || member["id"] != "hermes-labs:owner" {
		t.Fatalf("bootstrap create body = %#v", createdBody)
	}

	status := httptest.NewRecorder()
	handler.ServeHTTP(status, httptest.NewRequest(http.MethodGet, "/v1/bootstrap/status", nil))
	statusBody := decodeBody[map[string]any](t, status)
	if status.Code != http.StatusOK || statusBody["initialized"] != true || statusBody["owner_count"].(float64) != 1 {
		t.Fatalf("bootstrap status after create = %#v status=%d", statusBody, status.Code)
	}

	check := requestJSON(t, handler, http.MethodPost, "/v1/authz/check", map[string]any{
		"org_id":        "hermes-labs",
		"resource_type": "organization",
		"resource_id":   "hermes-labs",
		"permission":    "admin",
		"subject_type":  "member",
		"subject_id":    "hermes-labs:owner",
	})
	checkBody := decodeBody[map[string]any](t, check)
	if check.Code != http.StatusOK || checkBody["allowed"] != true {
		t.Fatalf("owner relationship check body = %#v status=%d", checkBody, check.Code)
	}

	repeated := requestJSON(t, handler, http.MethodPost, "/v1/bootstrap/super-admin", map[string]any{
		"org_slug":           "other",
		"org_name":           "Other",
		"admin_email":        "other@example.com",
		"admin_display_name": "Other Owner",
		"admin_user_id":      "other",
	})
	if repeated.Code != http.StatusConflict {
		t.Fatalf("repeated bootstrap status = %d body=%s", repeated.Code, repeated.Body.String())
	}
}
