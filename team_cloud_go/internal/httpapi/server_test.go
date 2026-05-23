package httpapi_test

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"hermes-agent/team_cloud_go/internal/config"
	"hermes-agent/team_cloud_go/internal/httpapi"
	"hermes-agent/team_cloud_go/internal/store/memory"
)

func newTestServer(t *testing.T) http.Handler {
	t.Helper()
	store := memory.New()
	server, err := httpapi.NewServer(config.Config{
		ServiceName:  "team-cloud-go",
		ServiceToken: "team-token",
	}, store)
	if err != nil {
		t.Fatalf("NewServer() error = %v", err)
	}
	return server
}

func requestJSON(t *testing.T, handler http.Handler, method, path string, body any) *httptest.ResponseRecorder {
	t.Helper()
	var payload bytes.Buffer
	if body != nil {
		if err := json.NewEncoder(&payload).Encode(body); err != nil {
			t.Fatalf("encode request body: %v", err)
		}
	}
	req := httptest.NewRequest(method, path, &payload)
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer team-token")
	rec := httptest.NewRecorder()
	handler.ServeHTTP(rec, req)
	return rec
}

func decodeBody[T any](t *testing.T, rec *httptest.ResponseRecorder) T {
	t.Helper()
	var out T
	if err := json.NewDecoder(rec.Body).Decode(&out); err != nil {
		t.Fatalf("decode response body: %v", err)
	}
	return out
}

func TestHealthReadyAndServiceTokenProtection(t *testing.T) {
	handler := newTestServer(t)

	health := httptest.NewRecorder()
	handler.ServeHTTP(health, httptest.NewRequest(http.MethodGet, "/healthz", nil))
	if health.Code != http.StatusOK {
		t.Fatalf("health status = %d", health.Code)
	}

	missingToken := httptest.NewRecorder()
	handler.ServeHTTP(missingToken, httptest.NewRequest(http.MethodGet, "/api/organizations", nil))
	if missingToken.Code != http.StatusUnauthorized {
		t.Fatalf("missing token status = %d", missingToken.Code)
	}

	ready := requestJSON(t, handler, http.MethodGet, "/readyz", nil)
	if ready.Code != http.StatusOK {
		t.Fatalf("ready status = %d", ready.Code)
	}
}

func TestOrganizationTeamAndMemberLifecycle(t *testing.T) {
	handler := newTestServer(t)

	org := requestJSON(t, handler, http.MethodPost, "/api/organizations", map[string]string{
		"slug": "hermes-labs",
		"name": "Hermes Labs",
	})
	if org.Code != http.StatusCreated {
		t.Fatalf("create org status = %d body=%s", org.Code, org.Body.String())
	}

	team := requestJSON(t, handler, http.MethodPost, "/api/organizations/hermes-labs/teams", map[string]string{
		"slug": "platform",
		"name": "Platform",
	})
	if team.Code != http.StatusCreated {
		t.Fatalf("create team status = %d body=%s", team.Code, team.Body.String())
	}

	member := requestJSON(t, handler, http.MethodPost, "/api/organizations/hermes-labs/members/invite", map[string]string{
		"email":        "alice@example.com",
		"display_name": "Alice",
		"user_id":      "alice",
		"role":         "member",
	})
	if member.Code != http.StatusCreated {
		t.Fatalf("invite member status = %d body=%s", member.Code, member.Body.String())
	}

	disabled := requestJSON(t, handler, http.MethodPatch, "/api/organizations/hermes-labs/members/hermes-labs:alice/disable", nil)
	if disabled.Code != http.StatusOK {
		t.Fatalf("disable member status = %d body=%s", disabled.Code, disabled.Body.String())
	}

	listed := requestJSON(t, handler, http.MethodGet, "/api/organizations/hermes-labs/members", nil)
	if listed.Code != http.StatusOK {
		t.Fatalf("list members status = %d", listed.Code)
	}
	body := decodeBody[map[string][]map[string]any](t, listed)
	if got := body["items"][0]["status"]; got != "suspended" {
		t.Fatalf("member status = %v", got)
	}
}

func TestMemoryPrefetchSeparatesPersonalAndTeamSharedSequences(t *testing.T) {
	handler := newTestServer(t)
	requestJSON(t, handler, http.MethodPost, "/api/organizations", map[string]string{
		"slug": "org-1",
		"name": "Org 1",
	})

	personal := requestJSON(t, handler, http.MethodPost, "/v1/memory", map[string]any{
		"org_id":            "org-1",
		"scope":             "personal",
		"subject_member_id": "alice",
		"content":           "Alice prefers deterministic tests.",
		"memory_type":       "preference",
	})
	if personal.Code != http.StatusCreated {
		t.Fatalf("personal memory status = %d body=%s", personal.Code, personal.Body.String())
	}

	team := requestJSON(t, handler, http.MethodPost, "/v1/memory", map[string]any{
		"org_id":      "org-1",
		"scope":       "team_shared",
		"team_id":     "team-1",
		"project_id":  "project-1",
		"content":     "Team deploys with Helm.",
		"memory_type": "fact",
		"status":      "active",
	})
	if team.Code != http.StatusCreated {
		t.Fatalf("team memory status = %d body=%s", team.Code, team.Body.String())
	}

	prefetch := requestJSON(t, handler, http.MethodPost, "/v1/memory/prefetch", map[string]any{
		"query":            "deploy tests",
		"org_id":           "org-1",
		"member_id":        "alice",
		"team_id":          "team-1",
		"project_id":       "project-1",
		"include_personal": true,
		"limit":            8,
	})
	if prefetch.Code != http.StatusOK {
		t.Fatalf("prefetch status = %d body=%s", prefetch.Code, prefetch.Body.String())
	}
	withPersonal := decodeBody[map[string][]map[string]any](t, prefetch)
	if len(withPersonal["partitions"]) != 2 {
		t.Fatalf("partitions with personal = %#v", withPersonal["partitions"])
	}

	sharedOnly := requestJSON(t, handler, http.MethodPost, "/v1/memory/prefetch", map[string]any{
		"query":            "deploy tests",
		"org_id":           "org-1",
		"member_id":        "alice",
		"team_id":          "team-1",
		"project_id":       "project-1",
		"include_personal": false,
		"limit":            8,
	})
	if sharedOnly.Code != http.StatusOK {
		t.Fatalf("shared-only prefetch status = %d body=%s", sharedOnly.Code, sharedOnly.Body.String())
	}
	withoutPersonal := decodeBody[map[string][]map[string]any](t, sharedOnly)
	if len(withoutPersonal["partitions"]) != 1 || withoutPersonal["partitions"][0]["scope"] != "team_shared" {
		t.Fatalf("partitions without personal = %#v", withoutPersonal["partitions"])
	}
}

func TestMemoryPrefetchRanksByQueryEmbedding(t *testing.T) {
	handler := newTestServer(t)
	requestJSON(t, handler, http.MethodPost, "/api/organizations", map[string]string{
		"slug": "org-1",
		"name": "Org 1",
	})
	first := requestJSON(t, handler, http.MethodPost, "/v1/memory", map[string]any{
		"org_id":            "org-1",
		"scope":             "personal",
		"subject_member_id": "alice",
		"content":           "Kubernetes deployment procedure.",
		"embedding":         []float64{1, 0, 0},
	})
	if first.Code != http.StatusCreated {
		t.Fatalf("first memory status = %d body=%s", first.Code, first.Body.String())
	}
	second := requestJSON(t, handler, http.MethodPost, "/v1/memory", map[string]any{
		"org_id":            "org-1",
		"scope":             "personal",
		"subject_member_id": "alice",
		"content":           "PostgreSQL restore procedure.",
		"embedding":         []float64{0, 1, 0},
	})
	if second.Code != http.StatusCreated {
		t.Fatalf("second memory status = %d body=%s", second.Code, second.Body.String())
	}

	prefetch := requestJSON(t, handler, http.MethodPost, "/v1/memory/prefetch", map[string]any{
		"org_id":           "org-1",
		"member_id":        "alice",
		"include_personal": true,
		"limit":            2,
		"query_embedding":  []float64{0, 1, 0},
	})
	if prefetch.Code != http.StatusOK {
		t.Fatalf("prefetch status = %d body=%s", prefetch.Code, prefetch.Body.String())
	}
	body := decodeBody[map[string][]map[string]any](t, prefetch)
	items := body["partitions"][0]["items"].([]any)
	firstItem := items[0].(map[string]any)
	if firstItem["content"] != "PostgreSQL restore procedure." {
		t.Fatalf("embedding ranking returned %#v", items)
	}
}

func TestTeamSharedMemoryReviewAndPersonalBackupPolicy(t *testing.T) {
	handler := newTestServer(t)
	created := requestJSON(t, handler, http.MethodPost, "/v1/memory", map[string]any{
		"org_id":      "org-1",
		"scope":       "team_shared",
		"team_id":     "team-1",
		"content":     "Shared fact candidate.",
		"memory_type": "fact",
	})
	if created.Code != http.StatusCreated {
		t.Fatalf("create team memory status = %d body=%s", created.Code, created.Body.String())
	}
	memoryBody := decodeBody[map[string]any](t, created)
	if memoryBody["status"] != "pending_review" {
		t.Fatalf("team memory status = %v", memoryBody["status"])
	}

	reviews := requestJSON(t, handler, http.MethodGet, "/v1/memory/review?org_id=org-1", nil)
	if reviews.Code != http.StatusOK {
		t.Fatalf("list reviews status = %d body=%s", reviews.Code, reviews.Body.String())
	}
	reviewBody := decodeBody[map[string][]map[string]any](t, reviews)
	reviewID := reviewBody["items"][0]["id"].(string)

	approved := requestJSON(t, handler, http.MethodPost, "/v1/memory/review/"+reviewID+"/approve", map[string]any{
		"actor_member_id": "reviewer-1",
	})
	if approved.Code != http.StatusOK {
		t.Fatalf("approve review status = %d body=%s", approved.Code, approved.Body.String())
	}
	approvedBody := decodeBody[map[string]any](t, approved)
	if approvedBody["status"] != "approved" || approvedBody["memory_status"] != "active" {
		t.Fatalf("approved body = %#v", approvedBody)
	}

	updatedPolicy := requestJSON(t, handler, http.MethodPut, "/v1/me/memory-backup-policy", map[string]any{
		"org_id":          "org-1",
		"member_id":       "alice",
		"cadence":         "daily",
		"enabled":         true,
		"retention_count": 7,
	})
	if updatedPolicy.Code != http.StatusOK {
		t.Fatalf("update backup policy status = %d body=%s", updatedPolicy.Code, updatedPolicy.Body.String())
	}
	policy := requestJSON(t, handler, http.MethodGet, "/v1/me/memory-backup-policy?org_id=org-1&member_id=alice", nil)
	if policy.Code != http.StatusOK {
		t.Fatalf("get backup policy status = %d body=%s", policy.Code, policy.Body.String())
	}
	policyBody := decodeBody[map[string]any](t, policy)
	if policyBody["cadence"] != "daily" || policyBody["enabled"] != true {
		t.Fatalf("policy body = %#v", policyBody)
	}
}
