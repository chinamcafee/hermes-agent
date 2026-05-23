package httpapi

import (
	"context"
	"fmt"
	"net/http"
	"strings"

	"hermes-agent/team_cloud_go/internal/authn"
	"hermes-agent/team_cloud_go/internal/store"
)

type bootstrapStatusPayload struct {
	Service           string            `json:"service"`
	Version           string            `json:"version"`
	Status            string            `json:"status"`
	Initialized       bool              `json:"initialized"`
	OrganizationCount int               `json:"organization_count"`
	OwnerCount        int               `json:"owner_count"`
	Checks            map[string]bool   `json:"checks"`
	Detail            map[string]string `json:"detail,omitempty"`
}

func (s *Server) bootstrapStatus(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeErrorText(w, http.StatusMethodNotAllowed, "method_not_allowed")
		return
	}
	status := s.bootstrapStatusSnapshot(r.Context())
	writeJSON(w, http.StatusOK, status)
}

func (s *Server) bootstrapSuperAdmin(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeErrorText(w, http.StatusMethodNotAllowed, "method_not_allowed")
		return
	}
	principal, ok := s.requireServiceTokenPrincipal(w, r)
	if !ok {
		return
	}
	status := s.bootstrapStatusSnapshot(r.Context())
	if status.Initialized {
		writeErrorText(w, http.StatusConflict, "already_initialized")
		return
	}
	var payload map[string]any
	if !decodeJSON(w, r, &payload) {
		return
	}
	orgSlug := strings.TrimSpace(stringValue(payload, "org_slug"))
	orgName := strings.TrimSpace(stringValue(payload, "org_name"))
	adminEmail := strings.TrimSpace(stringValue(payload, "admin_email"))
	adminDisplayName := strings.TrimSpace(stringValue(payload, "admin_display_name"))
	adminUserID := strings.TrimSpace(stringValue(payload, "admin_user_id"))
	if orgSlug == "" || orgName == "" || adminEmail == "" || adminUserID == "" {
		writeErrorText(w, http.StatusBadRequest, "org_slug_org_name_admin_email_admin_user_id_required")
		return
	}
	if adminDisplayName == "" {
		adminDisplayName = adminEmail
	}
	org, err := s.backend.CreateOrganization(r.Context(), orgSlug, orgName)
	if err != nil {
		writeError(w, http.StatusBadRequest, err)
		return
	}
	member, err := s.backend.InviteMember(r.Context(), org.ID, adminEmail, adminDisplayName, adminUserID, "owner")
	if err != nil {
		writeError(w, http.StatusBadRequest, err)
		return
	}
	relationship, err := s.authz.WriteRelationship(r.Context(), store.Relationship{
		OrgID:          org.ID,
		ResourceType:   "organization",
		ResourceID:     org.ID,
		Relation:       "owner",
		SubjectType:    "member",
		SubjectID:      member.ID,
		IdempotencyKey: fmt.Sprintf("bootstrap:%s:owner:%s", org.ID, member.ID),
	})
	if err != nil {
		writeErrorText(w, http.StatusServiceUnavailable, err.Error())
		return
	}
	_, _ = s.backend.AppendAuditEvent(r.Context(), store.AuditEvent{
		OrgID:    org.ID,
		ActorID:  principal.Subject,
		Action:   "bootstrap.super_admin.create",
		Resource: "organization:" + org.ID,
		Decision: "allowed",
		Metadata: map[string]any{"member_id": member.ID},
	})
	writeJSON(w, http.StatusCreated, map[string]any{
		"initialized":  true,
		"organization": org,
		"member":       member,
		"relationship": relationship,
	})
}

func (s *Server) requireServiceTokenPrincipal(w http.ResponseWriter, r *http.Request) (authn.Principal, bool) {
	principal, err := s.authn.Authenticate(r.Context(), r)
	if err != nil {
		writeErrorText(w, http.StatusUnauthorized, err.Error())
		return authn.Principal{}, false
	}
	if principal.Method != "service_token" {
		writeErrorText(w, http.StatusForbidden, "service_token_required")
		return authn.Principal{}, false
	}
	return principal, true
}

func (s *Server) bootstrapStatusSnapshot(ctx context.Context) bootstrapStatusPayload {
	checks := map[string]bool{
		"config":                   true,
		"service_token_configured": s.cfg.ServiceToken != "",
		"backend":                  false,
		"authz":                    false,
		"backup_object_store":      true,
		"dashboard":                s.dashboardAvailable(),
	}
	detail := map[string]string{}
	orgCount := 0
	ownerCount := 0
	if err := s.backend.Ping(ctx); err != nil {
		detail["backend"] = err.Error()
	} else {
		checks["backend"] = true
		orgs, err := s.backend.ListOrganizations(ctx)
		if err != nil {
			detail["organizations"] = err.Error()
		} else {
			orgCount = len(orgs)
			for _, org := range orgs {
				members, err := s.backend.ListMembers(ctx, org.ID)
				if err != nil {
					detail["members:"+org.ID] = err.Error()
					continue
				}
				for _, member := range members {
					if strings.EqualFold(member.Role, "owner") && member.Status != "suspended" {
						ownerCount++
					}
				}
			}
		}
	}
	if err := s.authz.Ping(ctx); err != nil {
		detail["authz"] = err.Error()
	} else {
		checks["authz"] = true
	}
	if s.objects != nil {
		if err := s.objects.Ping(ctx); err != nil {
			checks["backup_object_store"] = false
			detail["backup_object_store"] = err.Error()
		}
	}
	ready := true
	for _, ok := range checks {
		if !ok {
			ready = false
			break
		}
	}
	payload := bootstrapStatusPayload{
		Service:           s.cfg.ServiceName,
		Version:           s.cfg.Version,
		Status:            "ready",
		Initialized:       ownerCount > 0,
		OrganizationCount: orgCount,
		OwnerCount:        ownerCount,
		Checks:            checks,
	}
	if !ready {
		payload.Status = "not_ready"
	}
	if len(detail) > 0 {
		payload.Detail = detail
	}
	return payload
}

func (s *Server) dashboardAvailable() bool {
	if !s.cfg.DashboardEnabled {
		return false
	}
	if strings.TrimSpace(s.cfg.DashboardDir) == "" {
		return false
	}
	return true
}
