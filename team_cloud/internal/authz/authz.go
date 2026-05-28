package authz

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"time"

	"hermes-agent/team_cloud/internal/config"
	"hermes-agent/team_cloud/internal/store"
)

type Authorizer interface {
	Ping(ctx context.Context) error
	WriteRelationship(ctx context.Context, relationship store.Relationship) (store.Relationship, error)
	CheckPermission(ctx context.Context, check store.PermissionCheck) (store.PermissionDecision, error)
}

type localStoreAuthorizer struct {
	backend store.Backend
}

type mirroredAuthorizer struct {
	local  Authorizer
	remote Authorizer
}

type SpiceDBHTTPConfig struct {
	Endpoint string
	Token    string
}

type SpiceDBHTTP struct {
	endpoint string
	token    string
	client   *http.Client
}

func New(cfg config.Config, backend store.Backend) (Authorizer, error) {
	mode := strings.TrimSpace(strings.ToLower(cfg.AuthzMode))
	if mode == "" {
		mode = "local"
	}
	local := localStoreAuthorizer{backend: backend}
	switch mode {
	case "local":
		return local, nil
	case "spicedb_http":
		remote, err := NewSpiceDBHTTP(SpiceDBHTTPConfig{
			Endpoint: cfg.AuthzEndpoint,
			Token:    cfg.AuthzToken,
		})
		if err != nil {
			return nil, err
		}
		return mirroredAuthorizer{local: local, remote: remote}, nil
	default:
		return nil, fmt.Errorf("unsupported authz mode %q", cfg.AuthzMode)
	}
}

func (a localStoreAuthorizer) Ping(ctx context.Context) error {
	return nil
}

func (a localStoreAuthorizer) WriteRelationship(ctx context.Context, relationship store.Relationship) (store.Relationship, error) {
	return a.backend.WriteRelationship(ctx, relationship)
}

func (a localStoreAuthorizer) CheckPermission(ctx context.Context, check store.PermissionCheck) (store.PermissionDecision, error) {
	return a.backend.CheckPermission(ctx, check)
}

func (a mirroredAuthorizer) Ping(ctx context.Context) error {
	return a.remote.Ping(ctx)
}

func (a mirroredAuthorizer) WriteRelationship(ctx context.Context, relationship store.Relationship) (store.Relationship, error) {
	if _, err := a.remote.WriteRelationship(ctx, relationship); err != nil {
		return store.Relationship{}, err
	}
	return a.local.WriteRelationship(ctx, relationship)
}

func (a mirroredAuthorizer) CheckPermission(ctx context.Context, check store.PermissionCheck) (store.PermissionDecision, error) {
	return a.remote.CheckPermission(ctx, check)
}

func NewSpiceDBHTTP(cfg SpiceDBHTTPConfig) (*SpiceDBHTTP, error) {
	endpoint := strings.TrimRight(strings.TrimSpace(cfg.Endpoint), "/")
	if endpoint == "" {
		return nil, fmt.Errorf("authz endpoint is required for spicedb_http mode")
	}
	parsed, err := url.Parse(endpoint)
	if err != nil || parsed.Scheme == "" || parsed.Host == "" {
		return nil, fmt.Errorf("invalid authz endpoint %q", cfg.Endpoint)
	}
	return &SpiceDBHTTP{
		endpoint: endpoint,
		token:    strings.TrimSpace(cfg.Token),
		client: &http.Client{
			Timeout: 5 * time.Second,
		},
	}, nil
}

func (a *SpiceDBHTTP) Ping(ctx context.Context) error {
	return a.do(ctx, http.MethodGet, "/healthz", nil, nil)
}

func (a *SpiceDBHTTP) WriteRelationship(ctx context.Context, relationship store.Relationship) (store.Relationship, error) {
	if relationship.OrgID == "" || relationship.ResourceType == "" || relationship.ResourceID == "" || relationship.SubjectID == "" {
		return store.Relationship{}, fmt.Errorf("org_id, resource, and subject are required")
	}
	if relationship.Relation == "" {
		relationship.Relation = "member"
	}
	if relationship.SubjectType == "" {
		relationship.SubjectType = "member"
	}
	payload := map[string]any{
		"updates": []map[string]any{{
			"operation":    "OPERATION_TOUCH",
			"relationship": relationshipPayload(relationship),
		}},
	}
	if err := a.do(ctx, http.MethodPost, "/v1/relationships/write", payload, nil); err != nil {
		return store.Relationship{}, err
	}
	return relationship, nil
}

func (a *SpiceDBHTTP) CheckPermission(ctx context.Context, check store.PermissionCheck) (store.PermissionDecision, error) {
	if check.OrgID == "" || check.ResourceType == "" || check.ResourceID == "" || check.SubjectID == "" || check.Permission == "" {
		return store.PermissionDecision{}, fmt.Errorf("org_id, resource, subject, and permission are required")
	}
	if check.SubjectType == "" {
		check.SubjectType = "member"
	}
	payload := map[string]any{
		"resource": map[string]any{
			"object_type": check.ResourceType,
			"object_id":   spicedbObjectID(check.ResourceID),
		},
		"permission": check.Permission,
		"subject": map[string]any{
			"object": map[string]any{
				"object_type": check.SubjectType,
				"object_id":   spicedbObjectID(check.SubjectID),
			},
		},
	}
	var response struct {
		Permissionship string `json:"permissionship"`
	}
	if err := a.do(ctx, http.MethodPost, "/v1/permissions/check", payload, &response); err != nil {
		return store.PermissionDecision{}, err
	}
	path := fmt.Sprintf("spicedb:%s:%s#%s@%s:%s", check.ResourceType, check.ResourceID, check.Permission, check.SubjectType, check.SubjectID)
	switch response.Permissionship {
	case "PERMISSIONSHIP_HAS_PERMISSION", "HAS_PERMISSION":
		return store.PermissionDecision{Allowed: true, Reason: "spicedb_allowed", Path: []string{path}}, nil
	case "PERMISSIONSHIP_CONDITIONAL_PERMISSION", "CONDITIONAL_PERMISSION":
		return store.PermissionDecision{Allowed: false, Reason: "spicedb_conditional_permission", Path: []string{path}}, nil
	default:
		return store.PermissionDecision{Allowed: false, Reason: "spicedb_denied", Path: []string{path}}, nil
	}
}

func (a *SpiceDBHTTP) do(ctx context.Context, method, path string, payload any, target any) error {
	var body io.Reader
	if payload != nil {
		raw, err := json.Marshal(payload)
		if err != nil {
			return err
		}
		body = bytes.NewReader(raw)
	}
	req, err := http.NewRequestWithContext(ctx, method, a.endpoint+path, body)
	if err != nil {
		return err
	}
	if payload != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	if a.token != "" {
		req.Header.Set("Authorization", "Bearer "+a.token)
	}
	resp, err := a.client.Do(req)
	if err != nil {
		return fmt.Errorf("authz_remote_request: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		detail, _ := io.ReadAll(io.LimitReader(resp.Body, 2048))
		if len(detail) > 0 {
			return fmt.Errorf("authz_remote_status_%d: %s", resp.StatusCode, strings.TrimSpace(string(detail)))
		}
		return fmt.Errorf("authz_remote_status_%d", resp.StatusCode)
	}
	if target != nil {
		if err := json.NewDecoder(resp.Body).Decode(target); err != nil {
			return fmt.Errorf("decode_authz_remote_response: %w", err)
		}
	}
	return nil
}

func relationshipPayload(relationship store.Relationship) map[string]any {
	return map[string]any{
		"resource": map[string]any{
			"object_type": relationship.ResourceType,
			"object_id":   spicedbObjectID(relationship.ResourceID),
		},
		"relation": relationship.Relation,
		"subject": map[string]any{
			"object": map[string]any{
				"object_type": relationship.SubjectType,
				"object_id":   spicedbObjectID(relationship.SubjectID),
			},
		},
	}
}

func spicedbObjectID(id string) string {
	var out strings.Builder
	for _, r := range strings.TrimSpace(id) {
		switch {
		case r >= 'a' && r <= 'z',
			r >= 'A' && r <= 'Z',
			r >= '0' && r <= '9',
			r == '/', r == '_', r == '|', r == '-', r == '=', r == '+':
			out.WriteRune(r)
		case r == ':':
			out.WriteRune('|')
		default:
			out.WriteRune('_')
		}
	}
	return out.String()
}
