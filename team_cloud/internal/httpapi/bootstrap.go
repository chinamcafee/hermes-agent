package httpapi

import (
	"context"
	"fmt"
	"net/http"
	"strings"

	"golang.org/x/crypto/bcrypt"

	"hermes-agent/team_cloud/internal/config"
	"hermes-agent/team_cloud/internal/store"
)

type bootstrapStatusPayload struct {
	Service           string            `json:"service"`
	Version           string            `json:"version"`
	Status            string            `json:"status"`
	Initialized       bool              `json:"initialized"`
	OrganizationCount int               `json:"organization_count"`
	OwnerCount        int               `json:"owner_count"`
	SuperAdminCount   int               `json:"super_admin_count"`
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
	status := s.bootstrapStatusSnapshot(r.Context())
	if status.Initialized {
		writeErrorText(w, http.StatusConflict, "already_initialized")
		return
	}
	if !s.databaseConfiguredAtStartup {
		writeErrorText(w, http.StatusConflict, "postgres_restart_required")
		return
	}
	var payload map[string]any
	if !decodeJSON(w, r, &payload) {
		return
	}
	orgSlug := strings.TrimSpace(stringValue(payload, "org_slug"))
	orgName := strings.TrimSpace(stringValue(payload, "org_name"))
	teamName := strings.TrimSpace(stringValue(payload, "team_name"))
	adminEmail := strings.TrimSpace(stringValue(payload, "admin_email"))
	adminDisplayName := strings.TrimSpace(stringValue(payload, "admin_display_name"))
	adminUserID := strings.TrimSpace(stringValue(payload, "admin_user_id"))
	adminPassword := stringValue(payload, "admin_password")
	if orgName == "" {
		orgName = teamName
	}
	if orgSlug == "" {
		orgSlug = slugifyIdentifier(orgName)
	}
	if orgSlug == "" {
		orgSlug = "team"
	}
	if orgName == "" || adminEmail == "" || adminUserID == "" || adminPassword == "" {
		writeErrorText(w, http.StatusBadRequest, "team_name_admin_email_admin_user_id_admin_password_required")
		return
	}
	if adminDisplayName == "" {
		adminDisplayName = adminEmail
	}
	passwordHash, err := bcrypt.GenerateFromPassword([]byte(adminPassword), bcrypt.DefaultCost)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err)
		return
	}
	memberID := orgSlug + ":" + adminUserID
	orgRelationship, err := s.authz.WriteRelationship(r.Context(), store.Relationship{
		OrgID:          orgSlug,
		ResourceType:   "organization",
		ResourceID:     orgSlug,
		Relation:       "owner",
		SubjectType:    "member",
		SubjectID:      memberID,
		IdempotencyKey: fmt.Sprintf("bootstrap:%s:owner:%s", orgSlug, memberID),
	})
	if err != nil {
		writeErrorText(w, http.StatusServiceUnavailable, err.Error())
		return
	}
	org, err := s.backend.CreateOrganization(r.Context(), orgSlug, orgName)
	if err != nil {
		writeError(w, http.StatusBadRequest, err)
		return
	}
	member, err := s.backend.CreateMember(r.Context(), org.ID, adminEmail, adminDisplayName, adminUserID, "super_admin", string(passwordHash))
	if err != nil {
		writeError(w, http.StatusBadRequest, err)
		return
	}
	_, _ = s.backend.AppendAuditEvent(r.Context(), store.AuditEvent{
		OrgID:    org.ID,
		ActorID:  "bootstrap:init",
		Action:   "bootstrap.super_admin.create",
		Resource: "organization:" + org.ID,
		Decision: "allowed",
		Metadata: map[string]any{"member_id": member.ID},
	})
	writeJSON(w, http.StatusCreated, map[string]any{
		"initialized":      true,
		"organization":     org,
		"member":           member,
		"org_relationship": orgRelationship,
	})
}

func (s *Server) bootstrapStatusSnapshot(ctx context.Context) bootstrapStatusPayload {
	objectStoreRequired := backupObjectStoreRequired(s.cfg)
	objectStoreConfigured := minioConfigured(s.cfg)
	checks := map[string]bool{
		"config":                  true,
		"postgres_configured":     strings.TrimSpace(s.cfg.DatabaseURL) != "",
		"postgres_backend_active": s.databaseConfiguredAtStartup,
		"redis_configured":        strings.TrimSpace(s.cfg.RedisAddr) != "",
		"minio_configured":        objectStoreConfigured,
		"backend":                 false,
		"authz":                   false,
		"session_store":           false,
		"backup_object_store":     !objectStoreRequired || objectStoreConfigured,
		"dashboard":               s.dashboardAvailable(),
	}
	detail := map[string]string{}
	orgCount := 0
	ownerCount := 0
	superAdminCount := 0
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
					if member.Status == "suspended" || member.Status == "removed" {
						continue
					}
					if strings.EqualFold(member.Role, "owner") {
						ownerCount++
					}
					if strings.EqualFold(member.Role, "super_admin") {
						superAdminCount++
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
	if err := s.sessions.Ping(ctx); err != nil {
		detail["session_store"] = err.Error()
	} else {
		checks["session_store"] = true
	}
	if objectStoreRequired && s.objects != nil {
		if err := s.objects.Ping(ctx); err != nil {
			checks["backup_object_store"] = false
			detail["backup_object_store"] = err.Error()
		}
	}
	ready := true
	for _, key := range []string{"config", "postgres_configured", "postgres_backend_active", "backend", "authz", "session_store", "backup_object_store", "dashboard"} {
		if !checks[key] {
			ready = false
			break
		}
	}
	payload := bootstrapStatusPayload{
		Service:           s.cfg.ServiceName,
		Version:           s.cfg.Version,
		Status:            "ready",
		Initialized:       checks["postgres_configured"] && checks["postgres_backend_active"] && orgCount == 1 && superAdminCount == 1,
		OrganizationCount: orgCount,
		OwnerCount:        ownerCount,
		SuperAdminCount:   superAdminCount,
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

func slugifyIdentifier(value string) string {
	value = strings.ToLower(strings.TrimSpace(value))
	var out strings.Builder
	lastDash := false
	for _, r := range value {
		if (r >= 'a' && r <= 'z') || (r >= '0' && r <= '9') {
			out.WriteRune(r)
			lastDash = false
			continue
		}
		if !lastDash && out.Len() > 0 {
			out.WriteByte('-')
			lastDash = true
		}
	}
	return strings.Trim(out.String(), "-")
}

func minioConfigured(cfg config.Config) bool {
	if !backupObjectStoreRequired(cfg) {
		return false
	}
	return strings.TrimSpace(cfg.BackupS3Endpoint) != "" &&
		strings.TrimSpace(cfg.BackupS3Bucket) != "" &&
		strings.TrimSpace(cfg.BackupS3AccessKeyID) != "" &&
		strings.TrimSpace(cfg.BackupS3SecretAccessKey) != "" &&
		strings.TrimSpace(cfg.BackupEncryptionKey) != ""
}

func backupObjectStoreRequired(cfg config.Config) bool {
	mode := strings.TrimSpace(strings.ToLower(cfg.BackupObjectMode))
	return mode == "minio" || mode == "s3"
}
