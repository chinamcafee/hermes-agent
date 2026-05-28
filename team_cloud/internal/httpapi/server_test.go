package httpapi_test

import (
	"bytes"
	"crypto/rsa"
	"encoding/json"
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

type jwtAuthedTestServer struct {
	http.Handler
	privateKey *rsa.PrivateKey
}

func newTestServer(t *testing.T) http.Handler {
	t.Helper()
	_, handler := newConfiguredTestServer(t, config.Config{ServiceName: "team-cloud-go"}, memory.New())
	return handler
}

func newConfiguredTestServer(t *testing.T, cfg config.Config, backend store.Backend) (*httpapi.Server, http.Handler) {
	t.Helper()
	privateKey, jwksURL := startJWKS(t)
	if cfg.ServiceName == "" {
		cfg.ServiceName = "team-cloud-go"
	}
	cfg.CasdoorIssuer = "https://casdoor.example"
	cfg.CasdoorAudience = "hermes-team-cloud"
	cfg.CasdoorJWKSURL = jwksURL
	server, err := httpapi.NewServer(config.Config{
		ServiceName:                    cfg.ServiceName,
		Version:                        cfg.Version,
		BindAddr:                       cfg.BindAddr,
		DatabaseURL:                    cfg.DatabaseURL,
		RedisAddr:                      cfg.RedisAddr,
		RedisPassword:                  cfg.RedisPassword,
		RedisDB:                        cfg.RedisDB,
		SessionTTLSeconds:              cfg.SessionTTLSeconds,
		AutoMigrate:                    cfg.AutoMigrate,
		CasdoorIssuer:                  cfg.CasdoorIssuer,
		CasdoorAudience:                cfg.CasdoorAudience,
		CasdoorJWKSURL:                 cfg.CasdoorJWKSURL,
		AuthzMode:                      cfg.AuthzMode,
		AuthzEndpoint:                  cfg.AuthzEndpoint,
		AuthzToken:                     cfg.AuthzToken,
		BackupObjectMode:               cfg.BackupObjectMode,
		BackupS3Endpoint:               cfg.BackupS3Endpoint,
		BackupS3Bucket:                 cfg.BackupS3Bucket,
		BackupS3Region:                 cfg.BackupS3Region,
		BackupS3AccessKeyID:            cfg.BackupS3AccessKeyID,
		BackupS3SecretAccessKey:        cfg.BackupS3SecretAccessKey,
		BackupEncryptionKey:            cfg.BackupEncryptionKey,
		BackupRequirePreviewBefore:     cfg.BackupRequirePreviewBefore,
		BackupSchedulerEnabled:         cfg.BackupSchedulerEnabled,
		BackupSchedulerIntervalSeconds: cfg.BackupSchedulerIntervalSeconds,
		DashboardEnabled:               cfg.DashboardEnabled,
		DashboardDir:                   cfg.DashboardDir,
	}, backend)
	if err != nil {
		t.Fatalf("NewServer() error = %v", err)
	}
	return server, jwtAuthedTestServer{Handler: server, privateKey: privateKey}
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
	if authed, ok := handler.(interface {
		authorizationFor(*testing.T, string, string, any) string
	}); ok {
		req.Header.Set("Authorization", authed.authorizationFor(t, method, path, body))
	}
	rec := httptest.NewRecorder()
	handler.ServeHTTP(rec, req)
	return rec
}

func (s jwtAuthedTestServer) authorizationFor(t *testing.T, method, path string, body any) string {
	t.Helper()
	orgID := inferOrgID(path, body)
	if orgID == "" {
		orgID = "org-1"
	}
	memberID := inferMemberID(path, orgID, body)
	return "Bearer " + signRS256JWT(t, s.privateKey, map[string]any{
		"iss":              "https://casdoor.example",
		"aud":              "hermes-team-cloud",
		"sub":              "test-" + strings.ReplaceAll(memberID, ":", "-"),
		"email":            "test@example.com",
		"hermes_org_id":    orgID,
		"hermes_member_id": memberID,
		"exp":              time.Now().Add(time.Hour).Unix(),
	})
}

func inferOrgID(path string, body any) string {
	if value := mapStringValue(body, "org_id"); value != "" {
		return value
	}
	if strings.HasPrefix(path, "/api/organizations/") {
		rest := strings.TrimPrefix(path, "/api/organizations/")
		if rest != "" {
			return strings.Split(rest, "/")[0]
		}
	}
	if strings.HasPrefix(path, "/api/organizations") {
		return mapStringValue(body, "slug")
	}
	if strings.Contains(path, "org-2") {
		return "org-2"
	}
	return "org-1"
}

func inferMemberID(path, orgID string, body any) string {
	for _, key := range []string{"member_id", "subject_member_id"} {
		if value := mapStringValue(body, key); value != "" {
			if key == "member_id" && strings.Contains(path, "/v1/memory/prefetch") {
				break
			}
			return value
		}
	}
	return orgID + ":owner"
}

func mapStringValue(body any, key string) string {
	switch typed := body.(type) {
	case map[string]string:
		return typed[key]
	case map[string]any:
		value, _ := typed[key].(string)
		return value
	default:
		return ""
	}
}

func decodeBody[T any](t *testing.T, rec *httptest.ResponseRecorder) T {
	t.Helper()
	var out T
	if err := json.NewDecoder(rec.Body).Decode(&out); err != nil {
		t.Fatalf("decode response body: %v", err)
	}
	return out
}

func TestHealthReadyAndBearerProtection(t *testing.T) {
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

func TestOrganizationMemberLifecycleAndTeamsEndpointRemoved(t *testing.T) {
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
	if team.Code != http.StatusNotFound {
		t.Fatalf("retired teams endpoint status = %d body=%s", team.Code, team.Body.String())
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

func TestMemoryAPIRetiresPersonalScopeAndPrefetchesTeamSharedOnly(t *testing.T) {
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
	if personal.Code != http.StatusForbidden {
		t.Fatalf("personal memory scope must be retired, status = %d body=%s", personal.Code, personal.Body.String())
	}

	team := requestJSON(t, handler, http.MethodPost, "/v1/memory", map[string]any{
		"org_id":      "org-1",
		"scope":       "team_shared",
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
		"project_id":       "project-1",
		"include_personal": true,
		"limit":            8,
	})
	if prefetch.Code != http.StatusOK {
		t.Fatalf("prefetch status = %d body=%s", prefetch.Code, prefetch.Body.String())
	}
	withPersonal := decodeBody[map[string][]map[string]any](t, prefetch)
	if len(withPersonal["partitions"]) != 1 || withPersonal["partitions"][0]["scope"] != "team_shared" {
		t.Fatalf("prefetch must return only team memory even when include_personal is requested: %#v", withPersonal["partitions"])
	}

	sharedOnly := requestJSON(t, handler, http.MethodPost, "/v1/memory/prefetch", map[string]any{
		"query":            "deploy tests",
		"org_id":           "org-1",
		"member_id":        "alice",
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
		"org_id":    "org-1",
		"scope":     "team_shared",
		"status":    "active",
		"team_id":   "org-1",
		"content":   "Kubernetes deployment procedure.",
		"embedding": []float64{1, 0, 0},
	})
	if first.Code != http.StatusCreated {
		t.Fatalf("first memory status = %d body=%s", first.Code, first.Body.String())
	}
	second := requestJSON(t, handler, http.MethodPost, "/v1/memory", map[string]any{
		"org_id":    "org-1",
		"scope":     "team_shared",
		"status":    "active",
		"team_id":   "org-1",
		"content":   "PostgreSQL restore procedure.",
		"embedding": []float64{0, 1, 0},
	})
	if second.Code != http.StatusCreated {
		t.Fatalf("second memory status = %d body=%s", second.Code, second.Body.String())
	}

	prefetch := requestJSON(t, handler, http.MethodPost, "/v1/memory/prefetch", map[string]any{
		"org_id":           "org-1",
		"member_id":        "alice",
		"team_id":          "org-1",
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
	requestJSON(t, handler, http.MethodPost, "/api/organizations", map[string]string{
		"slug": "org-1",
		"name": "Org 1",
	})
	created := requestJSON(t, handler, http.MethodPost, "/v1/memory", map[string]any{
		"org_id":      "org-1",
		"scope":       "team_shared",
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

	personalPolicy := requestJSON(t, handler, http.MethodPut, "/v1/me/memory-backup-policy", map[string]any{
		"org_id":    "org-1",
		"member_id": "alice",
	})
	if personalPolicy.Code != http.StatusNotFound {
		t.Fatalf("personal memory backup policy endpoint must be retired, status = %d body=%s", personalPolicy.Code, personalPolicy.Body.String())
	}
}

func TestTeamMemoryBackupManagementRestoresByIDWithoutDuplicates(t *testing.T) {
	handler := newTestServer(t)
	requestJSON(t, handler, http.MethodPost, "/api/organizations", map[string]string{
		"slug": "org-1",
		"name": "Org 1",
	})
	created := requestJSON(t, handler, http.MethodPost, "/v1/memory", map[string]any{
		"org_id":      "org-1",
		"scope":       "team_shared",
		"status":      "active",
		"source_type": "admin_created",
		"content":     "团队统一使用回滚预案。",
		"memory_type": "procedure",
	})
	if created.Code != http.StatusCreated {
		t.Fatalf("create memory status = %d body=%s", created.Code, created.Body.String())
	}
	memoryBody := decodeBody[map[string]any](t, created)
	memoryID := memoryBody["id"].(string)

	policy := requestJSON(t, handler, http.MethodPut, "/v1/team-memory-backup-policy", map[string]any{
		"org_id":          "org-1",
		"cadence":         "daily",
		"enabled":         true,
		"retention_count": 3,
	})
	if policy.Code != http.StatusOK {
		t.Fatalf("upsert team backup policy status = %d body=%s", policy.Code, policy.Body.String())
	}

	backup := requestJSON(t, handler, http.MethodPost, "/v1/backups/team/run", map[string]any{
		"org_id": "org-1",
	})
	if backup.Code != http.StatusCreated {
		t.Fatalf("run team backup status = %d body=%s", backup.Code, backup.Body.String())
	}
	backupBody := decodeBody[map[string]any](t, backup)
	backupID := backupBody["id"].(string)
	if backupBody["item_count"] != float64(1) {
		t.Fatalf("backup item_count = %#v", backupBody)
	}

	history := requestJSON(t, handler, http.MethodGet, "/v1/backups/team?org_id=org-1", nil)
	if history.Code != http.StatusOK {
		t.Fatalf("list team backups status = %d body=%s", history.Code, history.Body.String())
	}
	historyBody := decodeBody[map[string][]map[string]any](t, history)
	if len(historyBody["items"]) != 1 || historyBody["items"][0]["id"] != backupID {
		t.Fatalf("backup history = %#v", historyBody)
	}

	deleted := requestJSON(t, handler, http.MethodDelete, "/v1/memory/"+memoryID, nil)
	if deleted.Code != http.StatusOK {
		t.Fatalf("delete memory status = %d body=%s", deleted.Code, deleted.Body.String())
	}

	preview := requestJSON(t, handler, http.MethodPost, "/v1/backups/team/"+backupID+"/restore-preview", map[string]any{
		"org_id": "org-1",
		"mode":   "merge",
	})
	if preview.Code != http.StatusOK {
		t.Fatalf("team restore preview status = %d body=%s", preview.Code, preview.Body.String())
	}
	execute := requestJSON(t, handler, http.MethodPost, "/v1/backups/team/"+backupID+"/restore-execute", map[string]any{
		"org_id": "org-1",
		"mode":   "merge",
	})
	if execute.Code != http.StatusOK {
		t.Fatalf("team restore execute status = %d body=%s", execute.Code, execute.Body.String())
	}
	updated := requestJSON(t, handler, http.MethodPatch, "/v1/memory/"+memoryID, map[string]any{
		"content": "临时改写内容。",
	})
	if updated.Code != http.StatusOK {
		t.Fatalf("update restored memory status = %d body=%s", updated.Code, updated.Body.String())
	}
	secondExecute := requestJSON(t, handler, http.MethodPost, "/v1/backups/team/"+backupID+"/restore-execute", map[string]any{
		"org_id": "org-1",
		"mode":   "merge",
	})
	if secondExecute.Code != http.StatusOK {
		t.Fatalf("second team restore execute status = %d body=%s", secondExecute.Code, secondExecute.Body.String())
	}

	listed := requestJSON(t, handler, http.MethodGet, "/v1/memory?org_id=org-1&scope=team_shared&status=active", nil)
	if listed.Code != http.StatusOK {
		t.Fatalf("list memory status = %d body=%s", listed.Code, listed.Body.String())
	}
	listedBody := decodeBody[map[string][]map[string]any](t, listed)
	if len(listedBody["items"]) != 1 {
		t.Fatalf("expected restore to upsert one memory, got %#v", listedBody)
	}
	if listedBody["items"][0]["id"] != memoryID || listedBody["items"][0]["content"] != "团队统一使用回滚预案。" {
		t.Fatalf("restored memory = %#v", listedBody["items"][0])
	}
}

func TestTeamSoulBackupManagementRequiresPreviewAndRestoresActiveSoul(t *testing.T) {
	handler := newTestServer(t)
	requestJSON(t, handler, http.MethodPost, "/api/organizations", map[string]string{
		"slug": "org-1",
		"name": "Org 1",
	})
	created := requestJSON(t, handler, http.MethodPut, "/v1/team-soul", map[string]any{
		"org_id":  "org-1",
		"team_id": "org-1",
		"content": "团队父人格：先讲边界，再给行动。",
	})
	if created.Code != http.StatusOK {
		t.Fatalf("create team soul status = %d body=%s", created.Code, created.Body.String())
	}

	policy := requestJSON(t, handler, http.MethodPut, "/v1/team-soul-backup-policy", map[string]any{
		"org_id":          "org-1",
		"cadence":         "weekly",
		"enabled":         true,
		"retention_count": 2,
	})
	if policy.Code != http.StatusOK {
		t.Fatalf("upsert team soul backup policy status = %d body=%s", policy.Code, policy.Body.String())
	}

	backup := requestJSON(t, handler, http.MethodPost, "/v1/backups/team-soul/run", map[string]any{
		"org_id":  "org-1",
		"team_id": "org-1",
	})
	if backup.Code != http.StatusCreated {
		t.Fatalf("run team soul backup status = %d body=%s", backup.Code, backup.Body.String())
	}
	backupBody := decodeBody[map[string]any](t, backup)
	backupID := backupBody["id"].(string)
	if backupBody["item_count"] != float64(1) {
		t.Fatalf("team soul backup item_count = %#v", backupBody)
	}

	history := requestJSON(t, handler, http.MethodGet, "/v1/backups/team-soul?org_id=org-1", nil)
	if history.Code != http.StatusOK {
		t.Fatalf("list team soul backups status = %d body=%s", history.Code, history.Body.String())
	}
	historyBody := decodeBody[map[string][]map[string]any](t, history)
	if len(historyBody["items"]) != 1 || historyBody["items"][0]["id"] != backupID {
		t.Fatalf("team soul backup history = %#v", historyBody)
	}

	changed := requestJSON(t, handler, http.MethodPut, "/v1/team-soul", map[string]any{
		"org_id":  "org-1",
		"team_id": "org-1",
		"content": "团队父人格：临时改写。",
	})
	if changed.Code != http.StatusOK {
		t.Fatalf("change team soul status = %d body=%s", changed.Code, changed.Body.String())
	}

	withoutPreview := requestJSON(t, handler, http.MethodPost, "/v1/backups/team-soul/"+backupID+"/restore-execute", map[string]any{
		"org_id": "org-1",
		"mode":   "merge",
	})
	if withoutPreview.Code != http.StatusBadRequest || !strings.Contains(withoutPreview.Body.String(), "restore_preview_required") {
		t.Fatalf("restore without preview status = %d body=%s", withoutPreview.Code, withoutPreview.Body.String())
	}

	preview := requestJSON(t, handler, http.MethodPost, "/v1/backups/team-soul/"+backupID+"/restore-preview", map[string]any{
		"org_id": "org-1",
		"mode":   "merge",
	})
	if preview.Code != http.StatusOK {
		t.Fatalf("team soul restore preview status = %d body=%s", preview.Code, preview.Body.String())
	}
	execute := requestJSON(t, handler, http.MethodPost, "/v1/backups/team-soul/"+backupID+"/restore-execute", map[string]any{
		"org_id": "org-1",
		"mode":   "merge",
	})
	if execute.Code != http.StatusOK {
		t.Fatalf("team soul restore execute status = %d body=%s", execute.Code, execute.Body.String())
	}

	restored := requestJSON(t, handler, http.MethodGet, "/v1/team-soul?org_id=org-1&team_id=org-1", nil)
	restoredBody := decodeBody[map[string]any](t, restored)
	if restored.Code != http.StatusOK || restoredBody["content"] != "团队父人格：先讲边界，再给行动。" {
		t.Fatalf("restored team soul status=%d body=%#v", restored.Code, restoredBody)
	}
}

func TestTeamMemoryGovernanceLifecycleSourcesAndHardDelete(t *testing.T) {
	handler := newTestServer(t)
	requestJSON(t, handler, http.MethodPost, "/api/organizations", map[string]string{
		"slug": "org-1",
		"name": "Org 1",
	})

	auto := requestJSON(t, handler, http.MethodPost, "/v1/memory", map[string]any{
		"org_id":           "org-1",
		"scope":            "team_shared",
		"content":          "Run blue-green deploys through the platform pipeline.",
		"memory_type":      "procedure",
		"status":           "active",
		"source_type":      "auto_extracted",
		"source_member_id": "org-1:alice",
	})
	if auto.Code != http.StatusCreated {
		t.Fatalf("auto extracted memory status = %d body=%s", auto.Code, auto.Body.String())
	}
	autoBody := decodeBody[map[string]any](t, auto)
	if autoBody["source_type"] != "auto_extracted" || autoBody["source_member_id"] != "org-1:alice" {
		t.Fatalf("auto source metadata = %#v", autoBody)
	}

	admin := requestJSON(t, handler, http.MethodPost, "/v1/memory", map[string]any{
		"org_id":      "org-1",
		"scope":       "team_shared",
		"content":     "All production incidents require an owner in the first response.",
		"memory_type": "policy",
		"status":      "active",
		"source_type": "admin_created",
	})
	if admin.Code != http.StatusCreated {
		t.Fatalf("admin memory status = %d body=%s", admin.Code, admin.Body.String())
	}
	adminBody := decodeBody[map[string]any](t, admin)
	if adminBody["source_type"] != "admin_created" || adminBody["created_by_member_id"] != "org-1:owner" {
		t.Fatalf("admin source metadata = %#v", adminBody)
	}

	listed := requestJSON(t, handler, http.MethodGet, "/v1/memory?org_id=org-1&scope=team_shared", nil)
	if listed.Code != http.StatusOK {
		t.Fatalf("list team memories status = %d body=%s", listed.Code, listed.Body.String())
	}
	listedBody := decodeBody[map[string][]map[string]any](t, listed)
	if len(listedBody["items"]) != 2 {
		t.Fatalf("team memory list = %#v", listedBody["items"])
	}

	adminID := adminBody["id"].(string)
	updated := requestJSON(t, handler, http.MethodPatch, "/v1/memory/"+adminID, map[string]any{
		"content": "All production incidents require an accountable owner in the first response.",
	})
	if updated.Code != http.StatusOK {
		t.Fatalf("update memory status = %d body=%s", updated.Code, updated.Body.String())
	}
	updatedBody := decodeBody[map[string]any](t, updated)
	if updatedBody["content"] != "All production incidents require an accountable owner in the first response." || updatedBody["version"].(float64) <= adminBody["version"].(float64) {
		t.Fatalf("updated body = %#v", updatedBody)
	}

	disabled := requestJSON(t, handler, http.MethodPost, "/v1/memory/"+autoBody["id"].(string)+"/disable", nil)
	if disabled.Code != http.StatusOK {
		t.Fatalf("disable memory status = %d body=%s", disabled.Code, disabled.Body.String())
	}
	disabledBody := decodeBody[map[string]any](t, disabled)
	if disabledBody["status"] != "archived" {
		t.Fatalf("disabled body = %#v", disabledBody)
	}

	deleted := requestJSON(t, handler, http.MethodDelete, "/v1/memory/"+adminID, nil)
	if deleted.Code != http.StatusOK {
		t.Fatalf("hard delete memory status = %d body=%s", deleted.Code, deleted.Body.String())
	}

	afterDelete := requestJSON(t, handler, http.MethodGet, "/v1/memory?org_id=org-1&scope=team_shared", nil)
	afterDeleteBody := decodeBody[map[string][]map[string]any](t, afterDelete)
	for _, item := range afterDeleteBody["items"] {
		if item["id"] == adminID {
			t.Fatalf("hard deleted memory still listed: %#v", afterDeleteBody["items"])
		}
	}
}
