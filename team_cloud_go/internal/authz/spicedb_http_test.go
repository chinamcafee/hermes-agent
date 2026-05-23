package authz

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"hermes-agent/team_cloud_go/internal/store"
)

func TestSpiceDBHTTPAdapterWritesRelationshipAndChecksPermission(t *testing.T) {
	var wroteRelationship bool
	var checkedPermission bool
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Header.Get("Authorization") != "Bearer spicedb-token" {
			t.Fatalf("Authorization header = %q", r.Header.Get("Authorization"))
		}
		switch r.URL.Path {
		case "/healthz":
			w.WriteHeader(http.StatusOK)
		case "/v1/relationships/write":
			if r.Method != http.MethodPost {
				t.Fatalf("write method = %s", r.Method)
			}
			var body map[string][]map[string]any
			if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
				t.Fatalf("decode write body: %v", err)
			}
			updates := body["updates"]
			if len(updates) != 1 {
				t.Fatalf("updates length = %d", len(updates))
			}
			if updates[0]["operation"] != "OPERATION_CREATE_OR_TOUCH" {
				t.Fatalf("operation = %#v", updates[0]["operation"])
			}
			relationship := updates[0]["relationship"].(map[string]any)
			resource := relationship["resource"].(map[string]any)
			subject := relationship["subject"].(map[string]any)
			subjectObject := subject["object"].(map[string]any)
			if resource["object_type"] != "team" || resource["object_id"] != "org-1:platform" {
				t.Fatalf("resource = %#v", resource)
			}
			if relationship["relation"] != "member" {
				t.Fatalf("relation = %#v", relationship["relation"])
			}
			if subjectObject["object_type"] != "member" || subjectObject["object_id"] != "org-1:alice" {
				t.Fatalf("subject = %#v", subjectObject)
			}
			wroteRelationship = true
			_ = json.NewEncoder(w).Encode(map[string]any{"written_at": "test"})
		case "/v1/permissions/check":
			if r.Method != http.MethodPost {
				t.Fatalf("check method = %s", r.Method)
			}
			var body map[string]any
			if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
				t.Fatalf("decode check body: %v", err)
			}
			resource := body["resource"].(map[string]any)
			subject := body["subject"].(map[string]any)
			subjectObject := subject["object"].(map[string]any)
			if resource["object_type"] != "team" || resource["object_id"] != "org-1:platform" {
				t.Fatalf("check resource = %#v", resource)
			}
			if body["permission"] != "read" {
				t.Fatalf("permission = %#v", body["permission"])
			}
			if subjectObject["object_type"] != "member" || subjectObject["object_id"] != "org-1:alice" {
				t.Fatalf("check subject = %#v", subjectObject)
			}
			checkedPermission = true
			_ = json.NewEncoder(w).Encode(map[string]string{"permissionship": "PERMISSIONSHIP_HAS_PERMISSION"})
		default:
			t.Fatalf("unexpected path %s", r.URL.Path)
		}
	}))
	defer server.Close()

	adapter, err := NewSpiceDBHTTP(SpiceDBHTTPConfig{
		Endpoint: server.URL,
		Token:    "spicedb-token",
	})
	if err != nil {
		t.Fatalf("NewSpiceDBHTTP() error = %v", err)
	}
	if err := adapter.Ping(context.Background()); err != nil {
		t.Fatalf("Ping() error = %v", err)
	}
	_, err = adapter.WriteRelationship(context.Background(), store.Relationship{
		OrgID:        "org-1",
		ResourceType: "team",
		ResourceID:   "org-1:platform",
		Relation:     "member",
		SubjectType:  "member",
		SubjectID:    "org-1:alice",
	})
	if err != nil {
		t.Fatalf("WriteRelationship() error = %v", err)
	}
	decision, err := adapter.CheckPermission(context.Background(), store.PermissionCheck{
		OrgID:        "org-1",
		ResourceType: "team",
		ResourceID:   "org-1:platform",
		Permission:   "read",
		SubjectType:  "member",
		SubjectID:    "org-1:alice",
	})
	if err != nil {
		t.Fatalf("CheckPermission() error = %v", err)
	}
	if !decision.Allowed || decision.Reason != "spicedb_allowed" {
		t.Fatalf("decision = %#v", decision)
	}
	if !wroteRelationship || !checkedPermission {
		t.Fatalf("wroteRelationship=%v checkedPermission=%v", wroteRelationship, checkedPermission)
	}
}
