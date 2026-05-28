package httpapi_test

import (
	"net/http"
	"testing"
)

func TestCLIAuthLoginAllowsUserMemberAndSessionIntrospection(t *testing.T) {
	handler := initializedDashboardV2Server(t)
	superToken := dashboardLogin(t, handler, "owner", "correct horse battery staple")

	created := requestJSONWithAuth(t, handler, http.MethodPost, "/api/organizations/hermes-labs/members", map[string]any{
		"email":        "alice@example.com",
		"display_name": "Alice",
		"user_id":      "alice",
		"role":         "user",
		"password":     "alice password",
	}, "Bearer "+superToken)
	if created.Code != http.StatusCreated {
		t.Fatalf("create user status = %d body=%s", created.Code, created.Body.String())
	}

	dashboardLogin := requestJSONWithAuth(t, handler, http.MethodPost, "/v1/auth/login", map[string]any{
		"org_id":   "hermes-labs",
		"user_id":  "alice",
		"password": "alice password",
	}, "")
	if dashboardLogin.Code != http.StatusForbidden {
		t.Fatalf("plain dashboard login should reject user role, status = %d body=%s", dashboardLogin.Code, dashboardLogin.Body.String())
	}

	cliLogin := requestJSONWithAuth(t, handler, http.MethodPost, "/v1/auth/login", map[string]any{
		"org_id":   "hermes-labs",
		"user_id":  "alice",
		"password": "alice password",
		"client":   "cli",
	}, "")
	if cliLogin.Code != http.StatusOK {
		t.Fatalf("cli login status = %d body=%s", cliLogin.Code, cliLogin.Body.String())
	}
	body := decodeBody[map[string]any](t, cliLogin)
	token, _ := body["token"].(string)
	if token == "" {
		t.Fatalf("cli login token missing: %#v", body)
	}

	session := requestJSONWithAuth(t, handler, http.MethodGet, "/v1/auth/session", nil, "Bearer "+token)
	if session.Code != http.StatusOK {
		t.Fatalf("session status = %d body=%s", session.Code, session.Body.String())
	}
	sessionBody := decodeBody[map[string]any](t, session)
	if sessionBody["member_id"] != "hermes-labs:alice" || sessionBody["role"] != "user" {
		t.Fatalf("session body = %#v", sessionBody)
	}
}
