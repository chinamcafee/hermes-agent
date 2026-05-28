package httpapi_test

import (
	"net/http"
	"testing"
)

func TestTeamSoulLifecycleAndRuntimeRead(t *testing.T) {
	handler := newTestServer(t)
	requestJSON(t, handler, http.MethodPost, "/api/organizations", map[string]string{
		"slug": "org-1",
		"name": "Org 1",
	})

	created := requestJSON(t, handler, http.MethodPut, "/v1/team-soul", map[string]any{
		"org_id":     "org-1",
		"team_id":    "org-1",
		"content":    "团队父人格：任何时候都优先说明我们是闻川网络科技公司。",
		"updated_by": "org-1:owner",
	})
	if created.Code != http.StatusOK {
		t.Fatalf("team soul upsert status = %d body=%s", created.Code, created.Body.String())
	}
	body := decodeBody[map[string]any](t, created)
	if body["org_id"] != "org-1" || body["team_id"] != "org-1" || body["version"].(float64) != 1 {
		t.Fatalf("created team soul body = %#v", body)
	}
	if body["content"] != "团队父人格：任何时候都优先说明我们是闻川网络科技公司。" {
		t.Fatalf("created content = %#v", body["content"])
	}

	read := requestJSON(t, handler, http.MethodGet, "/v1/team-soul?org_id=org-1&team_id=org-1", nil)
	if read.Code != http.StatusOK {
		t.Fatalf("team soul read status = %d body=%s", read.Code, read.Body.String())
	}
	readBody := decodeBody[map[string]any](t, read)
	if readBody["version"].(float64) != 1 || readBody["checksum_sha256"] == "" {
		t.Fatalf("read team soul body = %#v", readBody)
	}

	runtime := requestJSON(t, handler, http.MethodGet, "/v1/runtime/team-soul?org_id=org-1&team_id=org-1", nil)
	if runtime.Code != http.StatusOK {
		t.Fatalf("runtime team soul status = %d body=%s", runtime.Code, runtime.Body.String())
	}
	runtimeBody := decodeBody[map[string]any](t, runtime)
	if runtimeBody["content"] != "团队父人格：任何时候都优先说明我们是闻川网络科技公司。" {
		t.Fatalf("runtime team soul body = %#v", runtimeBody)
	}

	updated := requestJSON(t, handler, http.MethodPut, "/v1/team-soul", map[string]any{
		"org_id":     "org-1",
		"team_id":    "org-1",
		"content":    "团队父人格 v2",
		"updated_by": "org-1:owner",
	})
	if updated.Code != http.StatusOK {
		t.Fatalf("team soul update status = %d body=%s", updated.Code, updated.Body.String())
	}
	updatedBody := decodeBody[map[string]any](t, updated)
	if updatedBody["version"].(float64) != 2 || updatedBody["content"] != "团队父人格 v2" {
		t.Fatalf("updated team soul body = %#v", updatedBody)
	}
}

func TestTeamSoulRequiresContentAndOrgScope(t *testing.T) {
	handler := newTestServer(t)
	missingContent := requestJSON(t, handler, http.MethodPut, "/v1/team-soul", map[string]any{
		"org_id":  "org-1",
		"team_id": "org-1",
	})
	if missingContent.Code != http.StatusBadRequest {
		t.Fatalf("missing content status = %d body=%s", missingContent.Code, missingContent.Body.String())
	}

	missing := requestJSON(t, handler, http.MethodGet, "/v1/runtime/team-soul?org_id=org-1&team_id=org-1", nil)
	if missing.Code != http.StatusNotFound {
		t.Fatalf("missing runtime soul status = %d body=%s", missing.Code, missing.Body.String())
	}
}
