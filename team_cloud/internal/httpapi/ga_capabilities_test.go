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

	"hermes-agent/team_cloud/internal/config"
	"hermes-agent/team_cloud/internal/httpapi"
	"hermes-agent/team_cloud/internal/store"
	"hermes-agent/team_cloud/internal/store/memory"
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
	requestJSON(t, handler, http.MethodPost, "/api/organizations/org-1/members/invite", map[string]string{
		"email":        "alice@example.com",
		"display_name": "Alice",
		"user_id":      "alice",
	})
	shared := requestJSON(t, handler, http.MethodPost, "/v1/memory", map[string]any{
		"org_id":     "org-1",
		"scope":      "team_shared",
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
		"resource_type":   "organization",
		"resource_id":     "org-1",
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
		"resource_type": "organization",
		"resource_id":   "org-1",
		"permission":    "read",
		"subject_type":  "member",
		"subject_id":    "org-1:alice",
	})
	checkBody := decodeBody[map[string]any](t, check)
	if check.Code != http.StatusOK || checkBody["allowed"] != true {
		t.Fatalf("check body = %#v status=%d", checkBody, check.Code)
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

	for _, scope := range []string{"personal_memory", " personal_memory ", "PERSONAL_MEMORY", "arbitrary_scope"} {
		deletion := requestJSON(t, handler, http.MethodPost, "/v1/deletion-requests", map[string]any{
			"org_id":           "org-1",
			"target_member_id": "org-1:alice",
			"requested_by":     "org-1:alice",
			"deletion_scope":   scope,
			"reason":           "member requested deletion",
		})
		if deletion.Code != http.StatusBadRequest || !strings.Contains(deletion.Body.String(), "unsupported_deletion_scope") {
			t.Fatalf("personal or unknown deletion scope %q must be retired, status=%d body=%s", scope, deletion.Code, deletion.Body.String())
		}
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

func TestScheduledBackupRunnerRunsEnabledPolicies(t *testing.T) {
	server, handler := newConfiguredTestServer(t, config.Config{
		ServiceName: "team-cloud-go",
	}, memory.New())
	requestJSON(t, handler, http.MethodPost, "/api/organizations", map[string]string{
		"slug": "org-1",
		"name": "Org 1",
	})
	requestJSON(t, handler, http.MethodPost, "/v1/memory", map[string]any{
		"org_id":      "org-1",
		"scope":       "team_shared",
		"team_id":     "org-1",
		"status":      "active",
		"source_type": "admin_created",
		"content":     "Scheduled backup fact.",
	})
	requestJSON(t, handler, http.MethodPut, "/v1/team-memory-backup-policy", map[string]any{
		"org_id":          "org-1",
		"cadence":         "daily",
		"enabled":         true,
		"retention_count": 3,
	})
	requestJSON(t, handler, http.MethodPut, "/v1/team-soul", map[string]any{
		"org_id":  "org-1",
		"team_id": "org-1",
		"content": "Scheduled team soul.",
	})
	requestJSON(t, handler, http.MethodPut, "/v1/team-soul-backup-policy", map[string]any{
		"org_id":          "org-1",
		"cadence":         "daily",
		"enabled":         true,
		"retention_count": 3,
	})

	jobs, err := server.RunScheduledBackups(t.Context())
	if err != nil {
		t.Fatalf("RunScheduledBackups() error = %v", err)
	}
	if len(jobs) != 2 {
		t.Fatalf("scheduled jobs = %#v", jobs)
	}
	counts := map[string]int{}
	for _, job := range jobs {
		counts[job.MemberID] = job.ItemCount
	}
	if counts[store.TeamBackupMemberID] != 1 || counts[store.TeamSoulBackupMemberID] != 1 {
		t.Fatalf("scheduled job counts = %#v jobs=%#v", counts, jobs)
	}

	secondRun, err := server.RunScheduledBackups(t.Context())
	if err != nil {
		t.Fatalf("second RunScheduledBackups() error = %v", err)
	}
	if len(secondRun) != 0 {
		t.Fatalf("scheduled backup should respect next_run_at, got %#v", secondRun)
	}
}

func TestTeamBackupRetentionPrunesOlderJobs(t *testing.T) {
	handler := newTestServer(t)
	requestJSON(t, handler, http.MethodPost, "/api/organizations", map[string]string{
		"slug": "org-1",
		"name": "Org 1",
	})
	requestJSON(t, handler, http.MethodPut, "/v1/team-memory-backup-policy", map[string]any{
		"org_id":          "org-1",
		"cadence":         "daily",
		"enabled":         true,
		"retention_count": 1,
	})
	requestJSON(t, handler, http.MethodPost, "/v1/memory", map[string]any{
		"org_id":  "org-1",
		"scope":   "team_shared",
		"status":  "active",
		"content": "first retained fact",
	})
	first := requestJSON(t, handler, http.MethodPost, "/v1/backups/team/run", map[string]any{
		"org_id": "org-1",
	})
	firstID := decodeBody[map[string]any](t, first)["id"].(string)
	requestJSON(t, handler, http.MethodPost, "/v1/memory", map[string]any{
		"org_id":  "org-1",
		"scope":   "team_shared",
		"status":  "active",
		"content": "second retained fact",
	})
	second := requestJSON(t, handler, http.MethodPost, "/v1/backups/team/run", map[string]any{
		"org_id": "org-1",
	})
	if second.Code != http.StatusCreated {
		t.Fatalf("second backup status = %d body=%s", second.Code, second.Body.String())
	}

	firstDetail := requestJSON(t, handler, http.MethodGet, "/v1/backups/team/"+firstID, nil)
	firstBody := decodeBody[map[string]any](t, firstDetail)
	if firstDetail.Code != http.StatusOK || firstBody["status"] != "pruned" {
		t.Fatalf("first backup should be pruned by retention: status=%d body=%#v", firstDetail.Code, firstBody)
	}
}

func TestJWTBusinessAPIsFailClosedForPayloadSpoofingAndTeamMemory(t *testing.T) {
	privateKey, jwksURL := startJWKS(t)
	handler := newJWTAndServiceServer(t, privateKey, jwksURL)
	requestJSON(t, handler, http.MethodPost, "/api/organizations", map[string]string{
		"slug": "org-1",
		"name": "Org 1",
	})
	requestJSON(t, handler, http.MethodPost, "/api/organizations", map[string]string{
		"slug": "org-2",
		"name": "Org 2",
	})
	requestJSON(t, handler, http.MethodPost, "/v1/memory", map[string]any{
		"org_id":     "org-1",
		"scope":      "team_shared",
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
		"resource_type": "organization",
		"resource_id":   "org-1",
		"relation":      "member",
		"subject_type":  "member",
		"subject_id":    "org-1:alice",
	})
	if relationship.Code != http.StatusOK {
		t.Fatalf("write organization member relationship status = %d body=%s", relationship.Code, relationship.Body.String())
	}
	allowedPrefetch := requestJSONWithAuth(t, handler, http.MethodPost, "/v1/memory/prefetch", map[string]any{
		"query":            "deployment",
		"org_id":           "org-1",
		"member_id":        "org-1:alice",
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
	handler := newJWTAndServiceServer(t, privateKey, jwksURL)
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
	handler := newJWTAndServiceServer(t, privateKey, jwksURL)
	requestJSON(t, handler, http.MethodPost, "/api/organizations", map[string]string{
		"slug": "org-1",
		"name": "Org 1",
	})
	created := requestJSON(t, handler, http.MethodPost, "/v1/memory", map[string]any{
		"org_id":     "org-1",
		"scope":      "team_shared",
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
	handler := newJWTAndServiceServer(t, privateKey, jwksURL)
	requestJSON(t, handler, http.MethodPost, "/api/organizations", map[string]string{
		"slug": "org-1",
		"name": "Org 1",
	})
	requestJSON(t, handler, http.MethodPost, "/api/organizations", map[string]string{
		"slug": "org-2",
		"name": "Org 2",
	})
	for _, scope := range []string{"personal_memory", " PERSONAL_MEMORY ", "arbitrary_scope"} {
		personalDeletion := requestJSON(t, handler, http.MethodPost, "/v1/deletion-requests", map[string]any{
			"org_id":           "org-1",
			"target_member_id": "org-1:alice",
			"requested_by":     "org-1:alice",
			"deletion_scope":   scope,
			"reason":           "privacy request",
		})
		if personalDeletion.Code != http.StatusBadRequest || !strings.Contains(personalDeletion.Body.String(), "unsupported_deletion_scope") {
			t.Fatalf("personal or unknown deletion scope %q must be retired, status=%d body=%s", scope, personalDeletion.Code, personalDeletion.Body.String())
		}
	}
	session := requestJSON(t, handler, http.MethodPost, "/v1/sessions", map[string]any{
		"org_id":          "org-1",
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

	personalRun := requestJSONWithAuth(t, handler, http.MethodPost, "/v1/backups/personal/run", map[string]any{
		"org_id":    "org-1",
		"member_id": "org-1:alice",
	}, "Bearer "+aliceToken)
	if personalRun.Code != http.StatusNotFound {
		t.Fatalf("personal backup run endpoint must be retired, status = %d body=%s", personalRun.Code, personalRun.Body.String())
	}
	personalRead := requestJSONWithAuth(t, handler, http.MethodGet, "/v1/backups/personal/backup-1", nil, "Bearer "+aliceToken)
	if personalRead.Code != http.StatusNotFound {
		t.Fatalf("personal backup read endpoint must be retired, status = %d body=%s", personalRead.Code, personalRead.Body.String())
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

func newJWTAndServiceServer(t *testing.T, privateKey *rsa.PrivateKey, jwksURL string) http.Handler {
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
	return jwtAuthedTestServer{Handler: server, privateKey: privateKey}
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
