package httpapi

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"strconv"
	"strings"
	"time"

	"github.com/redis/go-redis/v9"
	"golang.org/x/crypto/bcrypt"

	"hermes-agent/team_cloud/internal/authn"
	"hermes-agent/team_cloud/internal/authz"
	"hermes-agent/team_cloud/internal/backup"
	"hermes-agent/team_cloud/internal/config"
	"hermes-agent/team_cloud/internal/objectstore"
	"hermes-agent/team_cloud/internal/store"
)

type Server struct {
	cfg                         config.Config
	backend                     store.Backend
	authn                       *authn.Authenticator
	authz                       authz.Authorizer
	sessions                    authn.SessionStore
	objects                     objectstore.ObjectStore
	mux                         *http.ServeMux
	databaseConfiguredAtStartup bool
}

type principalContextKey struct{}

func NewServer(cfg config.Config, backend store.Backend) (*Server, error) {
	if cfg.ServiceName == "" {
		cfg.ServiceName = "team-cloud-go"
	}
	if cfg.Version == "" {
		cfg.Version = "0.1.0"
	}
	if backend == nil {
		return nil, fmt.Errorf("backend is required")
	}
	authorizer, err := authz.New(cfg, backend)
	if err != nil {
		return nil, err
	}
	objects, err := objectStoreFromConfig(cfg)
	if err != nil {
		return nil, err
	}
	sessions := sessionStoreFromConfig(cfg)
	server := &Server{cfg: cfg, backend: backend, authn: authn.New(cfg, sessions), authz: authorizer, sessions: sessions, objects: objects, mux: http.NewServeMux(), databaseConfiguredAtStartup: strings.TrimSpace(cfg.DatabaseURL) != ""}
	server.routes()
	return server, nil
}

func (s *Server) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	s.mux.ServeHTTP(w, r)
}

func (s *Server) RunScheduledBackups(ctx context.Context) ([]store.BackupJob, error) {
	policies, err := s.backend.ListBackupPolicies(ctx, true)
	if err != nil {
		return nil, err
	}
	jobs := []store.BackupJob{}
	now := time.Now().UTC()
	for _, policy := range policies {
		if policy.MemberID != store.TeamBackupMemberID && policy.MemberID != store.TeamSoulBackupMemberID {
			continue
		}
		if !backupPolicyDue(policy, now) {
			continue
		}
		var job store.BackupJob
		var err error
		if policy.MemberID == store.TeamSoulBackupMemberID {
			job, err = s.backend.RunTeamSoulBackup(ctx, policy.OrgID, policy.OrgID)
		} else {
			job, err = s.backend.RunTeamMemoryBackup(ctx, policy.OrgID)
		}
		if err != nil {
			return jobs, err
		}
		job, err = s.persistBackupObject(ctx, job)
		if err != nil {
			return jobs, err
		}
		if err := s.afterBackupCreated(ctx, job); err != nil {
			return jobs, err
		}
		if err := s.backend.MarkBackupPolicyRun(ctx, policy.OrgID, policy.MemberID, now.Format(time.RFC3339), nextBackupRunAt(policy.Cadence, now).Format(time.RFC3339)); err != nil {
			return jobs, err
		}
		_, _ = s.backend.AppendAuditEvent(ctx, store.AuditEvent{
			OrgID:    job.OrgID,
			ActorID:  "service:backup-scheduler",
			Action:   scheduledBackupAuditAction(job.MemberID),
			Resource: "backup:" + job.ID,
			Decision: "allowed",
			Metadata: map[string]any{"cadence": policy.Cadence},
		})
		jobs = append(jobs, job)
	}
	return jobs, nil
}

func (s *Server) StartBackupScheduler(ctx context.Context) {
	if !s.cfg.BackupSchedulerEnabled {
		return
	}
	interval := time.Duration(s.cfg.BackupSchedulerIntervalSeconds) * time.Second
	if interval <= 0 {
		interval = time.Hour
	}
	go func() {
		ticker := time.NewTicker(interval)
		defer ticker.Stop()
		for {
			select {
			case <-ctx.Done():
				return
			case <-ticker.C:
				_, _ = s.RunScheduledBackups(ctx)
			}
		}
	}()
}

func (s *Server) routes() {
	s.mux.HandleFunc("/healthz", s.healthz)
	s.mux.HandleFunc("/readyz", s.readyz)
	s.mux.HandleFunc("/metrics", s.metrics)
	s.registerDashboardRoutes()
	s.mux.HandleFunc("/v1/bootstrap/status", s.bootstrapStatus)
	s.mux.HandleFunc("/v1/bootstrap/super-admin", s.bootstrapSuperAdmin)
	s.mux.HandleFunc("/v1/auth/login", s.authLogin)
	s.mux.HandleFunc("/v1/auth/session", s.requireAuth(s.authSession))
	s.mux.HandleFunc("/api/organizations", s.requireAuth(s.organizations))
	s.mux.HandleFunc("/api/organizations/", s.requireAuth(s.organizationChildren))
	s.mux.HandleFunc("/v1/memory", s.requireAuth(s.memoryCollection))
	s.mux.HandleFunc("/v1/memory/", s.requireAuth(s.memoryChildren))
	s.mux.HandleFunc("/v1/team-soul", s.requireAuth(s.teamSoul))
	s.mux.HandleFunc("/v1/runtime/team-soul", s.requireAuth(s.runtimeTeamSoul))
	s.mux.HandleFunc("/v1/team-memory-backup-policy", s.requireAuth(s.teamMemoryBackupPolicy))
	s.mux.HandleFunc("/v1/team-soul-backup-policy", s.requireAuth(s.teamSoulBackupPolicy))
	s.mux.HandleFunc("/v1/audit/events", s.requireAuth(s.auditEvents))
	s.mux.HandleFunc("/v1/authz/relationships", s.requireAuth(s.authzRelationships))
	s.mux.HandleFunc("/v1/authz/check", s.requireAuth(s.authzCheck))
	s.mux.HandleFunc("/v1/backups/team", s.requireAuth(s.teamBackupCollection))
	s.mux.HandleFunc("/v1/backups/team/run", s.requireAuth(s.runTeamBackup))
	s.mux.HandleFunc("/v1/backups/team/", s.requireAuth(s.teamBackupChildren))
	s.mux.HandleFunc("/v1/backups/team-soul", s.requireAuth(s.teamSoulBackupCollection))
	s.mux.HandleFunc("/v1/backups/team-soul/run", s.requireAuth(s.runTeamSoulBackup))
	s.mux.HandleFunc("/v1/backups/team-soul/", s.requireAuth(s.teamSoulBackupChildren))
	s.mux.HandleFunc("/v1/exports/org", s.requireAuth(s.orgExport))
	s.mux.HandleFunc("/v1/deletion-requests", s.requireAuth(s.deletionRequests))
	s.mux.HandleFunc("/v1/deletion-requests/", s.requireAuth(s.deletionRequestChildren))
	s.mux.HandleFunc("/v1/tool-policy/evaluate", s.requireAuth(s.evaluateToolPolicy))
	s.mux.HandleFunc("/v1/tool-policy/rules", s.requireAuth(s.toolPolicyRules))
	s.mux.HandleFunc("/v1/sessions", s.requireAuth(s.cloudSessions))
	s.mux.HandleFunc("/v1/runtime/events", s.requireAuth(s.runtimeEvents))
}

func (s *Server) healthz(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{
		"service": s.cfg.ServiceName,
		"status":  "ok",
		"version": s.cfg.Version,
	})
}

func (s *Server) readyz(w http.ResponseWriter, r *http.Request) {
	backendErr := s.backend.Ping(r.Context())
	authzErr := s.authz.Ping(r.Context())
	sessionErr := s.sessions.Ping(r.Context())
	var objectErr error
	if s.objects != nil {
		objectErr = s.objects.Ping(r.Context())
	}
	if backendErr != nil || authzErr != nil || sessionErr != nil || objectErr != nil {
		detail := map[string]string{}
		if backendErr != nil {
			detail["backend"] = backendErr.Error()
		}
		if authzErr != nil {
			detail["authz"] = authzErr.Error()
		}
		if sessionErr != nil {
			detail["session_store"] = sessionErr.Error()
		}
		if objectErr != nil {
			detail["backup_object_store"] = objectErr.Error()
		}
		writeJSON(w, http.StatusServiceUnavailable, map[string]any{
			"service": s.cfg.ServiceName,
			"status":  "not_ready",
			"checks": map[string]bool{
				"config":              true,
				"backend":             backendErr == nil,
				"authz":               authzErr == nil,
				"session_store":       sessionErr == nil,
				"backup_object_store": objectErr == nil,
			},
			"detail": detail,
		})
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"service": s.cfg.ServiceName,
		"status":  "ready",
		"checks": map[string]bool{
			"config":              true,
			"backend":             s.backend != nil,
			"authz":               s.authz != nil,
			"session_store":       s.sessions != nil,
			"backup_object_store": true,
		},
	})
}

func (s *Server) metrics(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/plain; version=0.0.4")
	_, _ = w.Write([]byte("team_cloud_up 1\n"))
}

func (s *Server) authLogin(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeErrorText(w, http.StatusMethodNotAllowed, "method_not_allowed")
		return
	}
	var payload map[string]any
	if !decodeJSON(w, r, &payload) {
		return
	}
	orgID := strings.TrimSpace(stringValue(payload, "org_id"))
	userID := strings.TrimSpace(stringValue(payload, "user_id"))
	password := stringValue(payload, "password")
	client := strings.ToLower(strings.TrimSpace(stringValue(payload, "client")))
	if orgID == "" || userID == "" || password == "" {
		writeErrorText(w, http.StatusBadRequest, "org_id_user_id_password_required")
		return
	}
	member, err := s.backend.GetMemberByUserID(r.Context(), orgID, userID)
	if err != nil {
		writeErrorText(w, http.StatusUnauthorized, "invalid_credentials")
		return
	}
	if member.Status != "active" {
		writeErrorText(w, http.StatusForbidden, "dashboard_login_forbidden")
		return
	}
	loginAction := "dashboard.login"
	if client == "cli" {
		loginAction = "cli.login"
		if !cliRoleCanLogin(member.Role) {
			writeErrorText(w, http.StatusForbidden, "cli_login_forbidden")
			return
		}
	} else if !dashboardRoleCanLogin(member.Role) {
		writeErrorText(w, http.StatusForbidden, "dashboard_login_forbidden")
		return
	}
	if member.PasswordHash == "" || bcrypt.CompareHashAndPassword([]byte(member.PasswordHash), []byte(password)) != nil {
		writeErrorText(w, http.StatusUnauthorized, "invalid_credentials")
		return
	}
	ttl := time.Duration(s.cfg.SessionTTLSeconds) * time.Second
	if ttl <= 0 {
		ttl = 12 * time.Hour
	}
	token, expiresAt, err := s.authn.IssueSessionToken(r.Context(), authn.Principal{
		Subject:  "member:" + member.ID,
		Email:    member.Email,
		OrgID:    member.OrgID,
		MemberID: member.ID,
		Role:     member.Role,
	}, time.Now().UTC(), ttl)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err)
		return
	}
	s.recordAudit(r.WithContext(context.WithValue(r.Context(), principalContextKey{}, authn.Principal{
		Subject:  "member:" + member.ID,
		Email:    member.Email,
		OrgID:    member.OrgID,
		MemberID: member.ID,
		Role:     member.Role,
		Method:   "dashboard_session",
	})), member.OrgID, loginAction, "member:"+member.ID, "allowed", nil)
	writeJSON(w, http.StatusOK, map[string]any{
		"token":      token,
		"expires_at": expiresAt.Format(time.RFC3339),
		"member":     member,
	})
}

func (s *Server) authSession(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeErrorText(w, http.StatusMethodNotAllowed, "method_not_allowed")
		return
	}
	principal := principalFromContext(r.Context())
	writeJSON(w, http.StatusOK, map[string]any{
		"subject":   principal.Subject,
		"email":     principal.Email,
		"org_id":    principal.OrgID,
		"member_id": principal.MemberID,
		"role":      principal.Role,
		"method":    principal.Method,
	})
}

func (s *Server) organizations(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodPost:
		var payload map[string]string
		if !decodeJSON(w, r, &payload) {
			return
		}
		if !s.allowOrganizationCreate(w, r, payload["slug"]) {
			return
		}
		org, err := s.backend.CreateOrganization(r.Context(), payload["slug"], payload["name"])
		if err == nil {
			s.seedOrganizationOwner(r, org.ID)
		}
		if err != nil {
			writeError(w, http.StatusBadRequest, err)
			return
		}
		s.recordAudit(r, org.ID, "organization.create", "organization:"+org.ID, "allowed", nil)
		writeJSON(w, http.StatusCreated, org)
	case http.MethodGet:
		orgs, err := s.backend.ListOrganizations(r.Context())
		if err != nil {
			writeError(w, http.StatusInternalServerError, err)
			return
		}
		principal := principalFromContext(r.Context())
		if principal.OrgID == "" {
			writeForbidden(w, "missing_principal_scope")
			return
		}
		scoped := make([]store.Organization, 0, 1)
		for _, org := range orgs {
			if org.ID == principal.OrgID {
				scoped = append(scoped, org)
				break
			}
		}
		orgs = scoped
		writeJSON(w, http.StatusOK, map[string]any{"items": orgs})
	default:
		writeErrorText(w, http.StatusMethodNotAllowed, "method_not_allowed")
	}
}

func (s *Server) organizationChildren(w http.ResponseWriter, r *http.Request) {
	parts := pathParts(r.URL.Path)
	if len(parts) < 3 || parts[0] != "api" || parts[1] != "organizations" {
		writeErrorText(w, http.StatusNotFound, "not_found")
		return
	}
	orgID := parts[2]
	if len(parts) == 4 && parts[3] == "members" {
		s.members(w, r, orgID)
		return
	}
	if len(parts) == 5 && parts[3] == "members" && parts[4] == "invite" {
		s.inviteMember(w, r, orgID)
		return
	}
	if len(parts) == 5 && parts[3] == "members" {
		s.memberItem(w, r, orgID, parts[4])
		return
	}
	if len(parts) == 6 && parts[3] == "members" && parts[5] == "disable" {
		s.disableMember(w, r, orgID, parts[4])
		return
	}
	writeErrorText(w, http.StatusNotFound, "not_found")
}

func (s *Server) members(w http.ResponseWriter, r *http.Request, orgID string) {
	switch r.Method {
	case http.MethodGet:
		if !s.authorizeResource(w, r, orgID, "organization", orgID, "manage", "member.list") {
			return
		}
		members, err := s.backend.ListMembers(r.Context(), orgID)
		writeStoreResult(w, http.StatusOK, map[string]any{"items": members}, err)
	case http.MethodPost:
		s.createMember(w, r, orgID)
	default:
		writeErrorText(w, http.StatusMethodNotAllowed, "method_not_allowed")
	}
}

func (s *Server) createMember(w http.ResponseWriter, r *http.Request, orgID string) {
	var payload map[string]any
	if !decodeJSON(w, r, &payload) {
		return
	}
	role := normalizeDashboardRole(stringValue(payload, "role"))
	if role == "" {
		writeErrorText(w, http.StatusBadRequest, "role_must_be_admin_or_user")
		return
	}
	if !s.authorizeDashboardMemberCreate(w, r, orgID, role) {
		return
	}
	email := strings.TrimSpace(stringValue(payload, "email"))
	displayName := strings.TrimSpace(stringValue(payload, "display_name"))
	userID := strings.TrimSpace(stringValue(payload, "user_id"))
	password := stringValue(payload, "password")
	if email == "" || userID == "" || password == "" {
		writeErrorText(w, http.StatusBadRequest, "email_user_id_password_required")
		return
	}
	passwordHash, err := bcrypt.GenerateFromPassword([]byte(password), bcrypt.DefaultCost)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err)
		return
	}
	member, err := s.backend.CreateMember(r.Context(), orgID, email, displayName, userID, role, string(passwordHash))
	if err != nil {
		writeStoreResult(w, http.StatusCreated, member, err)
		return
	}
	s.seedMemberRelationships(r, orgID, member)
	s.recordAudit(r, orgID, "member.create", "member:"+member.ID, "allowed", map[string]any{"role": member.Role})
	writeJSON(w, http.StatusCreated, member)
}

func (s *Server) memberItem(w http.ResponseWriter, r *http.Request, orgID, memberID string) {
	switch r.Method {
	case http.MethodPatch:
		var payload map[string]any
		if !decodeJSON(w, r, &payload) {
			return
		}
		existing, err := s.backend.GetMember(r.Context(), orgID, memberID)
		if err != nil {
			writeStoreResult(w, http.StatusOK, existing, err)
			return
		}
		if !s.authorizeDashboardMemberEdit(w, r, orgID, existing) {
			return
		}
		email := strings.TrimSpace(stringValue(payload, "email"))
		displayName := strings.TrimSpace(stringValue(payload, "display_name"))
		if email == "" {
			writeErrorText(w, http.StatusBadRequest, "email_required")
			return
		}
		member, err := s.backend.UpdateMember(r.Context(), orgID, memberID, email, displayName)
		if err == nil {
			s.recordAudit(r, orgID, "member.update", "member:"+member.ID, "allowed", map[string]any{"role": member.Role})
		}
		writeStoreResult(w, http.StatusOK, member, err)
	default:
		writeErrorText(w, http.StatusMethodNotAllowed, "method_not_allowed")
	}
}

func (s *Server) inviteMember(w http.ResponseWriter, r *http.Request, orgID string) {
	if r.Method != http.MethodPost {
		writeErrorText(w, http.StatusMethodNotAllowed, "method_not_allowed")
		return
	}
	var payload map[string]string
	if !decodeJSON(w, r, &payload) {
		return
	}
	if !s.authorizeResource(w, r, orgID, "organization", orgID, "manage", "member.invite") {
		return
	}
	member, err := s.backend.InviteMember(
		r.Context(),
		orgID,
		payload["email"],
		payload["display_name"],
		payload["user_id"],
		payload["role"],
	)
	if err == nil {
		s.seedMemberRelationships(r, orgID, member)
	}
	writeStoreResult(w, http.StatusCreated, member, err)
}

func (s *Server) disableMember(w http.ResponseWriter, r *http.Request, orgID, memberID string) {
	if r.Method != http.MethodPatch {
		writeErrorText(w, http.StatusMethodNotAllowed, "method_not_allowed")
		return
	}
	existing, err := s.backend.GetMember(r.Context(), orgID, memberID)
	if err != nil {
		writeStoreResult(w, http.StatusOK, existing, err)
		return
	}
	if existing.Role == "super_admin" {
		writeForbidden(w, "super_admin_cannot_be_disabled")
		return
	}
	if !s.authorizeDashboardMemberEdit(w, r, orgID, existing) {
		return
	}
	member, err := s.backend.DisableMember(r.Context(), orgID, memberID)
	if err == nil {
		s.recordAudit(r, orgID, "member.disable", "member:"+member.ID, "allowed", map[string]any{"role": member.Role})
	}
	writeStoreResult(w, http.StatusOK, member, err)
}

func (s *Server) memoryCollection(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodPost:
		var payload map[string]any
		if !decodeJSON(w, r, &payload) {
			return
		}
		if !s.authorizeMemoryCreate(w, r, payload) {
			return
		}
		item, err := s.backend.CreateMemory(r.Context(), payload)
		if err == nil {
			s.recordAudit(r, item.OrgID, "memory.create", "memory:"+item.ID, "allowed", map[string]any{"scope": item.Scope})
		}
		writeStoreResult(w, http.StatusCreated, item, err)
	case http.MethodGet:
		orgID := r.URL.Query().Get("org_id")
		if !s.ensureOrgScope(w, r, orgID, "memory.list") {
			return
		}
		items, err := s.backend.ListMemory(r.Context(), store.MemoryFilter{
			OrgID:       scopedOrgID(r, orgID),
			Scope:       r.URL.Query().Get("scope"),
			Status:      r.URL.Query().Get("status"),
			MemoryType:  r.URL.Query().Get("memory_type"),
			Sensitivity: r.URL.Query().Get("sensitivity"),
		})
		if err == nil {
			items = s.filterMemoryItemsForPrincipal(r, items)
		}
		writeStoreResult(w, http.StatusOK, map[string]any{"items": items}, err)
	default:
		writeErrorText(w, http.StatusMethodNotAllowed, "method_not_allowed")
	}
}

func (s *Server) memoryChildren(w http.ResponseWriter, r *http.Request) {
	parts := pathParts(r.URL.Path)
	if len(parts) == 3 && parts[0] == "v1" && parts[1] == "memory" && parts[2] == "prefetch" {
		s.prefetch(w, r)
		return
	}
	if len(parts) == 3 && parts[0] == "v1" && parts[1] == "memory" && parts[2] == "observations" {
		s.observations(w, r)
		return
	}
	if len(parts) == 3 && parts[0] == "v1" && parts[1] == "memory" && parts[2] == "review" {
		s.listReviews(w, r)
		return
	}
	if len(parts) == 5 && parts[0] == "v1" && parts[1] == "memory" && parts[2] == "review" {
		s.reviewDecision(w, r, parts[3], parts[4])
		return
	}
	if len(parts) == 3 && parts[0] == "v1" && parts[1] == "memory" {
		s.memoryItem(w, r, parts[2])
		return
	}
	if len(parts) == 4 && parts[0] == "v1" && parts[1] == "memory" {
		s.memoryItemAction(w, r, parts[2], parts[3])
		return
	}
	writeErrorText(w, http.StatusNotFound, "not_found")
}

func (s *Server) memoryItem(w http.ResponseWriter, r *http.Request, memoryID string) {
	if r.Method == http.MethodPatch {
		var payload map[string]any
		if !decodeJSON(w, r, &payload) {
			return
		}
		item, err := s.backend.GetMemory(r.Context(), memoryID)
		if err != nil {
			writeStoreResult(w, http.StatusOK, item, err)
			return
		}
		if !s.authorizeMemoryItem(w, r, item, "write_team", "memory.update") {
			return
		}
		updated, err := s.backend.UpdateMemory(r.Context(), memoryID, payload)
		writeStoreResult(w, http.StatusOK, updated, err)
		return
	}
	if r.Method == http.MethodDelete {
		existing, err := s.backend.GetMemory(r.Context(), memoryID)
		if err != nil {
			writeStoreResult(w, http.StatusOK, existing, err)
			return
		}
		if !s.authorizeMemoryItem(w, r, existing, "write_team", "memory.delete") {
			return
		}
		item, err := s.backend.DeleteMemory(r.Context(), memoryID)
		if err == nil {
			s.recordAudit(r, item.OrgID, "memory.delete_hard", "memory:"+item.ID, "allowed", map[string]any{"scope": item.Scope})
		}
		writeStoreResult(w, http.StatusOK, item, err)
		return
	}
	writeErrorText(w, http.StatusMethodNotAllowed, "method_not_allowed")
}

func (s *Server) memoryItemAction(w http.ResponseWriter, r *http.Request, memoryID, action string) {
	if r.Method != http.MethodPost {
		writeErrorText(w, http.StatusMethodNotAllowed, "method_not_allowed")
		return
	}
	statusByAction := map[string]string{
		"archive": "archived",
		"disable": "archived",
		"restore": "active",
	}
	status, ok := statusByAction[action]
	if !ok {
		writeErrorText(w, http.StatusNotFound, "not_found")
		return
	}
	existing, err := s.backend.GetMemory(r.Context(), memoryID)
	if err != nil {
		writeStoreResult(w, http.StatusOK, existing, err)
		return
	}
	if !s.authorizeMemoryItem(w, r, existing, "write_team", "memory."+action) {
		return
	}
	item, err := s.backend.SetMemoryStatus(r.Context(), memoryID, status)
	if err == nil {
		s.recordAudit(r, item.OrgID, "memory."+action, "memory:"+item.ID, "allowed", map[string]any{"status": item.Status})
	}
	writeStoreResult(w, http.StatusOK, item, err)
}

func (s *Server) observations(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeErrorText(w, http.StatusMethodNotAllowed, "method_not_allowed")
		return
	}
	var payload map[string]any
	if !decodeJSON(w, r, &payload) {
		return
	}
	if !s.authorizeObservation(w, r, payload) {
		return
	}
	observation, err := s.backend.CreateObservation(r.Context(), payload)
	writeStoreResult(w, http.StatusCreated, observation, err)
}

func (s *Server) prefetch(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeErrorText(w, http.StatusMethodNotAllowed, "method_not_allowed")
		return
	}
	var payload map[string]any
	if !decodeJSON(w, r, &payload) {
		return
	}
	req := store.PrefetchRequest{
		Query:           stringValue(payload, "query"),
		OrgID:           stringValue(payload, "org_id"),
		MemberID:        stringValue(payload, "member_id"),
		TeamID:          stringValue(payload, "team_id"),
		ProjectID:       stringValue(payload, "project_id"),
		IncludePersonal: false,
		Limit:           intValue(payload, "limit", 8),
		QueryEmbedding:  store.Float64Slice(payload["query_embedding"]),
	}
	if !s.authorizePrefetchRequest(w, r, req) {
		return
	}
	partitions, err := s.backend.Prefetch(r.Context(), req)
	if err == nil {
		partitions = s.filterPrefetchPartitions(r, req, partitions)
	}
	writeStoreResult(w, http.StatusOK, map[string]any{"partitions": partitions}, err)
}

func (s *Server) listReviews(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeErrorText(w, http.StatusMethodNotAllowed, "method_not_allowed")
		return
	}
	orgID := r.URL.Query().Get("org_id")
	if !s.authorizeResource(w, r, orgID, "organization", orgID, "manage", "memory.review.list") {
		return
	}
	reviews, err := s.backend.ListReviews(
		r.Context(),
		orgID,
		defaultString(r.URL.Query().Get("status"), "pending"),
		r.URL.Query().Get("review_kind"),
		intQuery(r, "limit", 100),
	)
	writeStoreResult(w, http.StatusOK, map[string]any{"items": reviews}, err)
}

func (s *Server) reviewDecision(w http.ResponseWriter, r *http.Request, reviewID, action string) {
	if r.Method != http.MethodPost {
		writeErrorText(w, http.StatusMethodNotAllowed, "method_not_allowed")
		return
	}
	var payload map[string]any
	if !decodeJSON(w, r, &payload) {
		return
	}
	if !s.authorizeReviewDecision(w, r, reviewID, action) {
		return
	}
	principal := principalFromContext(r.Context())
	actorMemberID := stringValue(payload, "actor_member_id")
	actorMemberID = principal.MemberID
	switch action {
	case "approve":
		decision, err := s.backend.ApproveReview(r.Context(), reviewID, actorMemberID, payload)
		writeStoreResult(w, http.StatusOK, decision, err)
	case "reject":
		decision, err := s.backend.RejectReview(r.Context(), reviewID, actorMemberID, stringValue(payload, "reason"))
		writeStoreResult(w, http.StatusOK, decision, err)
	default:
		writeErrorText(w, http.StatusNotFound, "not_found")
	}
}

func (s *Server) teamMemoryBackupPolicy(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		orgID := scopedOrgID(r, r.URL.Query().Get("org_id"))
		if !s.authorizeResource(w, r, orgID, "organization", orgID, "manage", "backup.team.policy.read") {
			return
		}
		policy, err := s.backend.GetTeamBackupPolicy(r.Context(), orgID)
		writeStoreResult(w, http.StatusOK, policy, err)
	case http.MethodPut:
		var payload map[string]any
		if !decodeJSON(w, r, &payload) {
			return
		}
		orgID := scopedOrgID(r, stringValue(payload, "org_id"))
		if !s.authorizeResource(w, r, orgID, "organization", orgID, "manage", "backup.team.policy.write") {
			return
		}
		policy, err := s.backend.UpsertTeamBackupPolicy(r.Context(), store.BackupPolicy{
			OrgID:          orgID,
			Cadence:        stringValue(payload, "cadence"),
			Enabled:        boolValue(payload, "enabled", false),
			RetentionCount: intValue(payload, "retention_count", 0),
		})
		writeStoreResult(w, http.StatusOK, policy, err)
	default:
		writeErrorText(w, http.StatusMethodNotAllowed, "method_not_allowed")
	}
}

func (s *Server) teamSoulBackupPolicy(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		orgID := scopedOrgID(r, r.URL.Query().Get("org_id"))
		if !s.authorizeResource(w, r, orgID, "organization", orgID, "manage", "backup.team_soul.policy.read") {
			return
		}
		policy, err := s.backend.GetTeamSoulBackupPolicy(r.Context(), orgID)
		writeStoreResult(w, http.StatusOK, policy, err)
	case http.MethodPut:
		var payload map[string]any
		if !decodeJSON(w, r, &payload) {
			return
		}
		orgID := scopedOrgID(r, stringValue(payload, "org_id"))
		if !s.authorizeResource(w, r, orgID, "organization", orgID, "manage", "backup.team_soul.policy.write") {
			return
		}
		policy, err := s.backend.UpsertTeamSoulBackupPolicy(r.Context(), store.BackupPolicy{
			OrgID:          orgID,
			Cadence:        stringValue(payload, "cadence"),
			Enabled:        boolValue(payload, "enabled", false),
			RetentionCount: intValue(payload, "retention_count", 0),
		})
		writeStoreResult(w, http.StatusOK, policy, err)
	default:
		writeErrorText(w, http.StatusMethodNotAllowed, "method_not_allowed")
	}
}

func (s *Server) teamSoul(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		orgID := scopedOrgID(r, r.URL.Query().Get("org_id"))
		teamID := strings.TrimSpace(r.URL.Query().Get("team_id"))
		if teamID == "" {
			teamID = orgID
		}
		if !s.authorizeResource(w, r, orgID, "organization", orgID, "manage", "team_soul.read") {
			return
		}
		soul, err := s.backend.GetTeamSoul(r.Context(), orgID, teamID)
		writeStoreResult(w, http.StatusOK, soul, err)
	case http.MethodPut:
		var payload map[string]any
		if !decodeJSON(w, r, &payload) {
			return
		}
		content := strings.TrimSpace(stringValue(payload, "content"))
		if content == "" {
			writeErrorText(w, http.StatusBadRequest, "content_required")
			return
		}
		orgID := scopedOrgID(r, stringValue(payload, "org_id"))
		teamID := strings.TrimSpace(stringValue(payload, "team_id"))
		if teamID == "" {
			teamID = orgID
		}
		if !s.authorizeResource(w, r, orgID, "organization", orgID, "manage", "team_soul.write") {
			return
		}
		principal := principalFromContext(r.Context())
		updatedBy := strings.TrimSpace(stringValue(payload, "updated_by"))
		if updatedBy == "" {
			updatedBy = principal.MemberID
		}
		soul, err := s.backend.UpsertTeamSoul(r.Context(), store.TeamSoul{
			OrgID:     orgID,
			TeamID:    teamID,
			Content:   content,
			UpdatedBy: updatedBy,
		})
		if err == nil {
			s.recordAudit(r, orgID, "team_soul.update", "team_soul:"+teamID, "allowed", map[string]any{"version": soul.Version})
		}
		writeStoreResult(w, http.StatusOK, soul, err)
	default:
		writeErrorText(w, http.StatusMethodNotAllowed, "method_not_allowed")
	}
}

func (s *Server) runtimeTeamSoul(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeErrorText(w, http.StatusMethodNotAllowed, "method_not_allowed")
		return
	}
	orgID := scopedOrgID(r, r.URL.Query().Get("org_id"))
	teamID := strings.TrimSpace(r.URL.Query().Get("team_id"))
	if teamID == "" {
		teamID = orgID
	}
	if !s.ensureOrgScope(w, r, orgID, "runtime.team_soul.read") {
		return
	}
	soul, err := s.backend.GetTeamSoul(r.Context(), orgID, teamID)
	writeStoreResult(w, http.StatusOK, soul, err)
}

func (s *Server) auditEvents(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeErrorText(w, http.StatusMethodNotAllowed, "method_not_allowed")
		return
	}
	orgID := r.URL.Query().Get("org_id")
	if !s.authorizeAuditRead(w, r, orgID) {
		return
	}
	events, err := s.backend.ListAuditEvents(r.Context(), scopedOrgID(r, orgID), intQuery(r, "limit", 100))
	writeStoreResult(w, http.StatusOK, map[string]any{"items": events}, err)
}

func (s *Server) authzRelationships(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPut && r.Method != http.MethodPost {
		writeErrorText(w, http.StatusMethodNotAllowed, "method_not_allowed")
		return
	}
	var payload map[string]any
	if !decodeJSON(w, r, &payload) {
		return
	}
	relationshipInput := store.Relationship{
		OrgID:          stringValue(payload, "org_id"),
		ResourceType:   stringValue(payload, "resource_type"),
		ResourceID:     stringValue(payload, "resource_id"),
		Relation:       stringValue(payload, "relation"),
		SubjectType:    stringValue(payload, "subject_type"),
		SubjectID:      stringValue(payload, "subject_id"),
		IdempotencyKey: stringValue(payload, "idempotency_key"),
	}
	if !s.authorizeRelationshipWrite(w, r, relationshipInput) {
		return
	}
	relationship, err := s.authz.WriteRelationship(r.Context(), relationshipInput)
	if err == nil {
		s.recordAudit(r, relationship.OrgID, "authz.relationship.write", relationship.ResourceType+":"+relationship.ResourceID, "allowed", map[string]any{"relation": relationship.Relation})
	}
	writeStoreResult(w, http.StatusOK, relationship, err)
}

func (s *Server) authzCheck(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeErrorText(w, http.StatusMethodNotAllowed, "method_not_allowed")
		return
	}
	var payload map[string]any
	if !decodeJSON(w, r, &payload) {
		return
	}
	check := store.PermissionCheck{
		OrgID:        stringValue(payload, "org_id"),
		ResourceType: stringValue(payload, "resource_type"),
		ResourceID:   stringValue(payload, "resource_id"),
		Permission:   stringValue(payload, "permission"),
		SubjectType:  stringValue(payload, "subject_type"),
		SubjectID:    stringValue(payload, "subject_id"),
	}
	if !s.authorizePermissionCheck(w, r, check) {
		return
	}
	decision, err := s.authz.CheckPermission(r.Context(), check)
	writeStoreResult(w, http.StatusOK, decision, err)
}

func (s *Server) teamBackupCollection(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeErrorText(w, http.StatusMethodNotAllowed, "method_not_allowed")
		return
	}
	orgID := scopedOrgID(r, r.URL.Query().Get("org_id"))
	if !s.authorizeResource(w, r, orgID, "organization", orgID, "manage", "backup.team.list") {
		return
	}
	jobs, err := s.backend.ListBackupJobs(r.Context(), orgID, store.TeamBackupMemberID, intQuery(r, "limit", 100))
	if err == nil {
		for i := range jobs {
			jobs[i] = sanitizedBackupJob(jobs[i])
		}
	}
	writeStoreResult(w, http.StatusOK, map[string]any{"items": jobs}, err)
}

func (s *Server) runTeamBackup(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeErrorText(w, http.StatusMethodNotAllowed, "method_not_allowed")
		return
	}
	var payload map[string]any
	if !decodeJSON(w, r, &payload) {
		return
	}
	orgID := scopedOrgID(r, stringValue(payload, "org_id"))
	if !s.authorizeResource(w, r, orgID, "organization", orgID, "manage", "backup.team.run") {
		return
	}
	job, err := s.backend.RunTeamMemoryBackup(r.Context(), orgID)
	if err == nil {
		job, err = s.persistBackupObject(r.Context(), job)
	}
	if err == nil {
		err = s.afterBackupCreated(r.Context(), job)
	}
	if err == nil {
		s.recordAudit(r, job.OrgID, "backup.team_memory.run", "backup:"+job.ID, "allowed", map[string]any{"item_count": job.ItemCount})
	}
	writeStoreResult(w, http.StatusCreated, job, err)
}

func (s *Server) teamBackupChildren(w http.ResponseWriter, r *http.Request) {
	parts := pathParts(r.URL.Path)
	if len(parts) == 4 && parts[0] == "v1" && parts[1] == "backups" && parts[2] == "team" {
		if r.Method != http.MethodGet {
			writeErrorText(w, http.StatusMethodNotAllowed, "method_not_allowed")
			return
		}
		job, err := s.backend.GetBackupJob(r.Context(), parts[3])
		if err != nil {
			writeStoreResult(w, http.StatusOK, job, err)
			return
		}
		if !s.authorizeTeamBackupJob(w, r, job, "backup.team.read") {
			return
		}
		writeJSON(w, http.StatusOK, sanitizedBackupJob(job))
		return
	}
	if len(parts) == 5 && parts[0] == "v1" && parts[1] == "backups" && parts[2] == "team" {
		s.teamBackupAction(w, r, parts[3], parts[4])
		return
	}
	writeErrorText(w, http.StatusNotFound, "not_found")
}

func (s *Server) teamBackupAction(w http.ResponseWriter, r *http.Request, backupID, action string) {
	if r.Method != http.MethodPost {
		writeErrorText(w, http.StatusMethodNotAllowed, "method_not_allowed")
		return
	}
	var payload map[string]any
	if !decodeJSON(w, r, &payload) {
		return
	}
	job, err := s.backend.GetBackupJob(r.Context(), backupID)
	if err != nil {
		writeStoreResult(w, http.StatusOK, job, err)
		return
	}
	if !s.authorizeTeamBackupJob(w, r, job, "backup.team."+action) {
		return
	}
	if err := s.refreshBackupSnapshotFromObject(r.Context(), job); err != nil {
		writeError(w, http.StatusBadRequest, err)
		return
	}
	switch action {
	case "restore-preview":
		preview, err := s.backend.PreviewTeamMemoryRestore(r.Context(), backupID, stringValue(payload, "mode"))
		writeStoreResult(w, http.StatusOK, preview, err)
	case "restore-execute":
		execution, err := s.backend.ExecuteTeamMemoryRestore(r.Context(), backupID, stringValue(payload, "mode"))
		if err == nil {
			s.recordAudit(r, job.OrgID, "backup.team_memory.restore", "backup:"+backupID, "allowed", map[string]any{"restored_count": execution.RestoredCount})
		}
		writeStoreResult(w, http.StatusOK, execution, err)
	default:
		writeErrorText(w, http.StatusNotFound, "not_found")
	}
}

func (s *Server) teamSoulBackupCollection(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeErrorText(w, http.StatusMethodNotAllowed, "method_not_allowed")
		return
	}
	orgID := scopedOrgID(r, r.URL.Query().Get("org_id"))
	if !s.authorizeResource(w, r, orgID, "organization", orgID, "manage", "backup.team_soul.list") {
		return
	}
	jobs, err := s.backend.ListBackupJobs(r.Context(), orgID, store.TeamSoulBackupMemberID, intQuery(r, "limit", 100))
	if err == nil {
		for i := range jobs {
			jobs[i] = sanitizedBackupJob(jobs[i])
		}
	}
	writeStoreResult(w, http.StatusOK, map[string]any{"items": jobs}, err)
}

func (s *Server) runTeamSoulBackup(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeErrorText(w, http.StatusMethodNotAllowed, "method_not_allowed")
		return
	}
	var payload map[string]any
	if !decodeJSON(w, r, &payload) {
		return
	}
	orgID := scopedOrgID(r, stringValue(payload, "org_id"))
	teamID := strings.TrimSpace(stringValue(payload, "team_id"))
	if teamID == "" {
		teamID = orgID
	}
	if !s.authorizeResource(w, r, orgID, "organization", orgID, "manage", "backup.team_soul.run") {
		return
	}
	job, err := s.backend.RunTeamSoulBackup(r.Context(), orgID, teamID)
	if err == nil {
		job, err = s.persistBackupObject(r.Context(), job)
	}
	if err == nil {
		err = s.afterBackupCreated(r.Context(), job)
	}
	if err == nil {
		s.recordAudit(r, job.OrgID, "backup.team_soul.run", "backup:"+job.ID, "allowed", map[string]any{"team_id": teamID})
	}
	writeStoreResult(w, http.StatusCreated, job, err)
}

func (s *Server) teamSoulBackupChildren(w http.ResponseWriter, r *http.Request) {
	parts := pathParts(r.URL.Path)
	if len(parts) == 4 && parts[0] == "v1" && parts[1] == "backups" && parts[2] == "team-soul" {
		if r.Method != http.MethodGet {
			writeErrorText(w, http.StatusMethodNotAllowed, "method_not_allowed")
			return
		}
		job, err := s.backend.GetBackupJob(r.Context(), parts[3])
		if err != nil {
			writeStoreResult(w, http.StatusOK, job, err)
			return
		}
		if !s.authorizeTeamSoulBackupJob(w, r, job, "backup.team_soul.read") {
			return
		}
		writeJSON(w, http.StatusOK, sanitizedBackupJob(job))
		return
	}
	if len(parts) == 5 && parts[0] == "v1" && parts[1] == "backups" && parts[2] == "team-soul" {
		s.teamSoulBackupAction(w, r, parts[3], parts[4])
		return
	}
	writeErrorText(w, http.StatusNotFound, "not_found")
}

func (s *Server) teamSoulBackupAction(w http.ResponseWriter, r *http.Request, backupID, action string) {
	if r.Method != http.MethodPost {
		writeErrorText(w, http.StatusMethodNotAllowed, "method_not_allowed")
		return
	}
	var payload map[string]any
	if !decodeJSON(w, r, &payload) {
		return
	}
	job, err := s.backend.GetBackupJob(r.Context(), backupID)
	if err != nil {
		writeStoreResult(w, http.StatusOK, job, err)
		return
	}
	if !s.authorizeTeamSoulBackupJob(w, r, job, "backup.team_soul."+action) {
		return
	}
	if err := s.refreshBackupSnapshotFromObject(r.Context(), job); err != nil {
		writeError(w, http.StatusBadRequest, err)
		return
	}
	switch action {
	case "restore-preview":
		preview, err := s.backend.PreviewTeamSoulRestore(r.Context(), backupID, stringValue(payload, "mode"))
		writeStoreResult(w, http.StatusOK, preview, err)
	case "restore-execute":
		execution, err := s.backend.ExecuteTeamSoulRestore(r.Context(), backupID, stringValue(payload, "mode"))
		if err == nil {
			s.recordAudit(r, job.OrgID, "backup.team_soul.restore", "backup:"+backupID, "allowed", map[string]any{"restored_count": execution.RestoredCount})
		}
		writeStoreResult(w, http.StatusOK, execution, err)
	default:
		writeErrorText(w, http.StatusNotFound, "not_found")
	}
}

func (s *Server) orgExport(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeErrorText(w, http.StatusMethodNotAllowed, "method_not_allowed")
		return
	}
	var payload map[string]any
	if !decodeJSON(w, r, &payload) {
		return
	}
	if !s.authorizeResource(w, r, stringValue(payload, "org_id"), "organization", stringValue(payload, "org_id"), "manage", "export.org") {
		return
	}
	exported, err := s.backend.CreateOrgExport(r.Context(), stringValue(payload, "org_id"))
	if err == nil {
		s.recordAudit(r, exported.OrgID, "export.org.create", "export:"+exported.ID, "allowed", nil)
	}
	writeStoreResult(w, http.StatusCreated, exported, err)
}

func (s *Server) deletionRequests(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeErrorText(w, http.StatusMethodNotAllowed, "method_not_allowed")
		return
	}
	var payload map[string]any
	if !decodeJSON(w, r, &payload) {
		return
	}
	deletionScope, err := store.NormalizeDeletionScope(stringValue(payload, "deletion_scope"))
	if err != nil {
		writeErrorText(w, http.StatusBadRequest, err.Error())
		return
	}
	payload["deletion_scope"] = deletionScope
	if !s.authorizeDeletionRequest(w, r, payload) {
		return
	}
	req, err := s.backend.CreateDeletionRequest(r.Context(), store.DeletionRequest{
		OrgID:          stringValue(payload, "org_id"),
		TargetMemberID: stringValue(payload, "target_member_id"),
		RequestedBy:    stringValue(payload, "requested_by"),
		DeletionScope:  deletionScope,
		Reason:         stringValue(payload, "reason"),
	})
	if err == nil {
		s.recordAudit(r, req.OrgID, "deletion.request.create", "deletion:"+req.ID, "allowed", map[string]any{"scope": req.DeletionScope})
	}
	writeStoreResult(w, http.StatusCreated, req, err)
}

func (s *Server) deletionRequestChildren(w http.ResponseWriter, r *http.Request) {
	parts := pathParts(r.URL.Path)
	if len(parts) == 4 && parts[0] == "v1" && parts[1] == "deletion-requests" && parts[3] == "execute" {
		if r.Method != http.MethodPost {
			writeErrorText(w, http.StatusMethodNotAllowed, "method_not_allowed")
			return
		}
		var payload map[string]any
		if !decodeJSON(w, r, &payload) {
			return
		}
		req, err := s.backend.GetDeletionRequest(r.Context(), parts[2])
		if err != nil {
			writeStoreResult(w, http.StatusOK, req, err)
			return
		}
		if !s.authorizeDeletionExecute(w, r, req) {
			return
		}
		actorMemberID := stringValue(payload, "actor_member_id")
		principal := principalFromContext(r.Context())
		actorMemberID = principal.MemberID
		req, err = s.backend.ExecuteDeletionRequest(r.Context(), parts[2], actorMemberID)
		if err == nil {
			s.recordAudit(r, req.OrgID, "deletion.request.execute", "deletion:"+req.ID, "allowed", map[string]any{"scope": req.DeletionScope})
		}
		writeStoreResult(w, http.StatusOK, req, err)
		return
	}
	writeErrorText(w, http.StatusNotFound, "not_found")
}

func (s *Server) evaluateToolPolicy(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeErrorText(w, http.StatusMethodNotAllowed, "method_not_allowed")
		return
	}
	var payload map[string]any
	if !decodeJSON(w, r, &payload) {
		return
	}
	if !s.authorizePersonalMemberScope(w, r, stringValue(payload, "org_id"), stringValue(payload, "member_id"), "tool.policy.evaluate") {
		return
	}
	decision, err := s.backend.EvaluateToolPolicy(r.Context(), store.ToolPolicyRequest{
		OrgID:     stringValue(payload, "org_id"),
		MemberID:  stringValue(payload, "member_id"),
		ToolName:  stringValue(payload, "tool_name"),
		RiskLevel: stringValue(payload, "risk_level"),
	})
	if err == nil {
		s.recordAudit(r, stringValue(payload, "org_id"), "tool.policy.evaluate", "tool:"+stringValue(payload, "tool_name"), decision.Decision, map[string]any{"risk_level": stringValue(payload, "risk_level")})
	}
	writeStoreResult(w, http.StatusOK, decision, err)
}

func (s *Server) toolPolicyRules(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPut && r.Method != http.MethodPost {
		writeErrorText(w, http.StatusMethodNotAllowed, "method_not_allowed")
		return
	}
	var payload map[string]any
	if !decodeJSON(w, r, &payload) {
		return
	}
	if !s.authorizeResource(w, r, stringValue(payload, "org_id"), "organization", stringValue(payload, "org_id"), "manage", "tool.policy.write") {
		return
	}
	rule, err := s.backend.UpsertToolPolicyRule(r.Context(), store.ToolPolicyRule{
		OrgID:     stringValue(payload, "org_id"),
		ToolName:  stringValue(payload, "tool_name"),
		RiskLevel: stringValue(payload, "risk_level"),
		Decision:  stringValue(payload, "decision"),
		UpdatedBy: stringValue(payload, "updated_by"),
	})
	writeStoreResult(w, http.StatusOK, rule, err)
}

func (s *Server) cloudSessions(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeErrorText(w, http.StatusMethodNotAllowed, "method_not_allowed")
		return
	}
	var payload map[string]any
	if !decodeJSON(w, r, &payload) {
		return
	}
	orgID := stringValue(payload, "org_id")
	if !s.authorizeResource(w, r, orgID, "organization", orgID, "run_agent", "session.create") {
		return
	}
	teamID := stringValue(payload, "team_id")
	if teamID == "" {
		teamID = orgID
	}
	session, err := s.backend.CreateCloudSession(r.Context(), store.CloudSession{
		OrgID:         orgID,
		TeamID:        teamID,
		ProjectID:     stringValue(payload, "project_id"),
		OwnerMemberID: stringValue(payload, "owner_member_id"),
		Title:         stringValue(payload, "title"),
	})
	writeStoreResult(w, http.StatusCreated, session, err)
}

func (s *Server) runtimeEvents(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeErrorText(w, http.StatusMethodNotAllowed, "method_not_allowed")
		return
	}
	var payload map[string]any
	if !decodeJSON(w, r, &payload) {
		return
	}
	if !s.authorizeRuntimeEvent(w, r, payload) {
		return
	}
	eventPayload, _ := payload["payload"].(map[string]any)
	event, err := s.backend.AppendRuntimeEvent(r.Context(), store.RuntimeEvent{
		OrgID:     stringValue(payload, "org_id"),
		SessionID: stringValue(payload, "session_id"),
		EventType: stringValue(payload, "event_type"),
		Payload:   eventPayload,
	})
	writeStoreResult(w, http.StatusCreated, event, err)
}

func (s *Server) requireAuth(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		principal, err := s.authn.Authenticate(r.Context(), r)
		if err != nil {
			writeErrorText(w, http.StatusUnauthorized, err.Error())
			return
		}
		ctx := context.WithValue(r.Context(), principalContextKey{}, principal)
		next(w, r.WithContext(ctx))
	}
}

func (s *Server) recordAudit(r *http.Request, orgID, action, resource, decision string, metadata map[string]any) {
	principal := principalFromContext(r.Context())
	if orgID == "" {
		orgID = principal.OrgID
	}
	_, _ = s.backend.AppendAuditEvent(r.Context(), store.AuditEvent{
		OrgID:    orgID,
		ActorID:  principal.Subject,
		Action:   action,
		Resource: resource,
		Decision: decision,
		Metadata: metadata,
	})
}

func objectStoreFromConfig(cfg config.Config) (objectstore.ObjectStore, error) {
	switch strings.TrimSpace(strings.ToLower(cfg.BackupObjectMode)) {
	case "", "database":
		return nil, nil
	case "s3", "minio":
		return objectstore.NewS3(objectstore.S3Config{
			Endpoint:        cfg.BackupS3Endpoint,
			Bucket:          cfg.BackupS3Bucket,
			Region:          cfg.BackupS3Region,
			AccessKeyID:     cfg.BackupS3AccessKeyID,
			SecretAccessKey: cfg.BackupS3SecretAccessKey,
		})
	default:
		return nil, fmt.Errorf("unsupported backup object mode %q", cfg.BackupObjectMode)
	}
}

func sessionStoreFromConfig(cfg config.Config) authn.SessionStore {
	if strings.TrimSpace(cfg.RedisAddr) == "" {
		return authn.NewMemorySessionStore()
	}
	return authn.NewRedisSessionStore(redis.NewClient(&redis.Options{
		Addr:     cfg.RedisAddr,
		Password: cfg.RedisPassword,
		DB:       cfg.RedisDB,
	}), "")
}

func (s *Server) persistBackupObject(ctx context.Context, job store.BackupJob) (store.BackupJob, error) {
	if s.objects == nil {
		return job, nil
	}
	if job.MemberID == store.TeamSoulBackupMemberID {
		payload, err := json.Marshal(job.Manifest)
		if err != nil {
			return store.BackupJob{}, err
		}
		sum := sha256.Sum256(payload)
		if err := s.objects.Put(ctx, job.ObjectKey, payload, "application/json"); err != nil {
			return store.BackupJob{}, err
		}
		manifest := cloneMap(job.Manifest)
		manifest["object_store"] = strings.TrimSpace(strings.ToLower(s.cfg.BackupObjectMode))
		manifest["bucket"] = s.cfg.BackupS3Bucket
		manifest["object_key"] = job.ObjectKey
		return s.backend.UpdateBackupObject(ctx, job.ID, hex.EncodeToString(sum[:]), manifest)
	}
	payload, manifest, err := backup.EncodeEncryptedJSONL(job.OrgID, job.MemberID, job.Items, s.cfg.BackupEncryptionKey)
	if err != nil {
		return store.BackupJob{}, err
	}
	if err := s.objects.Put(ctx, job.ObjectKey, payload, "application/octet-stream"); err != nil {
		return store.BackupJob{}, err
	}
	manifestMap := backup.ManifestMap(manifest, map[string]any{
		"object_store": strings.TrimSpace(strings.ToLower(s.cfg.BackupObjectMode)),
		"bucket":       s.cfg.BackupS3Bucket,
		"object_key":   job.ObjectKey,
	})
	return s.backend.UpdateBackupObject(ctx, job.ID, manifest.ChecksumSHA256, manifestMap)
}

func (s *Server) refreshBackupSnapshotFromObject(ctx context.Context, job store.BackupJob) error {
	if s.objects == nil || !job.ObjectUploaded {
		return nil
	}
	payload, err := s.objects.Get(ctx, job.ObjectKey)
	if err != nil {
		return err
	}
	sum := sha256.Sum256(payload)
	if job.ChecksumSHA256 != "" && hex.EncodeToString(sum[:]) != job.ChecksumSHA256 {
		return fmt.Errorf("backup_object_checksum_mismatch")
	}
	if job.MemberID == store.TeamSoulBackupMemberID {
		var manifest map[string]any
		if err := json.Unmarshal(payload, &manifest); err != nil {
			return err
		}
		manifest["object_store"] = strings.TrimSpace(strings.ToLower(s.cfg.BackupObjectMode))
		manifest["bucket"] = s.cfg.BackupS3Bucket
		manifest["object_key"] = job.ObjectKey
		_, err = s.backend.UpdateBackupObject(ctx, job.ID, hex.EncodeToString(sum[:]), manifest)
		return err
	}
	items, err := backup.DecodeEncryptedJSONL(job.OrgID, job.MemberID, payload, s.cfg.BackupEncryptionKey)
	if err != nil {
		return err
	}
	_, err = s.backend.UpdateBackupItems(ctx, job.ID, items)
	return err
}

func (s *Server) afterBackupCreated(ctx context.Context, job store.BackupJob) error {
	policy, err := s.backend.GetBackupPolicy(ctx, job.OrgID, job.MemberID)
	if err != nil {
		return err
	}
	if policy.RetentionCount <= 0 {
		return nil
	}
	_, err = s.backend.PruneBackupJobs(ctx, job.OrgID, job.MemberID, policy.RetentionCount)
	return err
}

func backupPolicyDue(policy store.BackupPolicy, now time.Time) bool {
	if !policy.Enabled {
		return false
	}
	if strings.TrimSpace(policy.NextRunAt) == "" {
		return true
	}
	nextRunAt, err := time.Parse(time.RFC3339, policy.NextRunAt)
	if err != nil {
		return true
	}
	return !nextRunAt.After(now)
}

func nextBackupRunAt(cadence string, now time.Time) time.Time {
	switch cadence {
	case "hourly":
		return now.Add(time.Hour)
	case "daily":
		return now.AddDate(0, 0, 1)
	case "monthly":
		return now.AddDate(0, 1, 0)
	default:
		return now.AddDate(0, 0, 7)
	}
}

func sanitizedBackupJob(job store.BackupJob) store.BackupJob {
	job.Items = nil
	return job
}

func scheduledBackupAuditAction(memberID string) string {
	if memberID == store.TeamSoulBackupMemberID {
		return "backup.team_soul.scheduled"
	}
	return "backup.team_memory.scheduled"
}

func cloneMap(in map[string]any) map[string]any {
	if in == nil {
		return map[string]any{}
	}
	out := make(map[string]any, len(in))
	for key, value := range in {
		out[key] = value
	}
	return out
}

func (s *Server) allowOrganizationCreate(w http.ResponseWriter, r *http.Request, orgID string) bool {
	principal := principalFromContext(r.Context())
	if principal.OrgID == "" || principal.MemberID == "" || orgID == "" || principal.OrgID != orgID {
		writeForbidden(w, "forbidden_org_scope")
		return false
	}
	return true
}

func (s *Server) seedOrganizationOwner(r *http.Request, orgID string) {
	principal := principalFromContext(r.Context())
	if principal.MemberID == "" {
		return
	}
	_, _ = s.authz.WriteRelationship(r.Context(), store.Relationship{
		OrgID:        orgID,
		ResourceType: "organization",
		ResourceID:   orgID,
		Relation:     "owner",
		SubjectType:  "member",
		SubjectID:    principal.MemberID,
	})
}

func (s *Server) seedMemberRelationships(r *http.Request, orgID string, member store.Member) {
	switch member.Role {
	case "admin":
		_, _ = s.authz.WriteRelationship(r.Context(), store.Relationship{
			OrgID:          orgID,
			ResourceType:   "organization",
			ResourceID:     orgID,
			Relation:       "admin",
			SubjectType:    "member",
			SubjectID:      member.ID,
			IdempotencyKey: "member:" + member.ID + ":organization:" + orgID + ":admin",
		})
	case "user", "member":
		_, _ = s.authz.WriteRelationship(r.Context(), store.Relationship{
			OrgID:          orgID,
			ResourceType:   "organization",
			ResourceID:     orgID,
			Relation:       "member",
			SubjectType:    "member",
			SubjectID:      member.ID,
			IdempotencyKey: "member:" + member.ID + ":organization:" + orgID + ":member",
		})
	}
}

func dashboardRoleCanLogin(role string) bool {
	return role == "super_admin" || role == "admin"
}

func cliRoleCanLogin(role string) bool {
	return role == "super_admin" || role == "admin" || role == "user" || role == "member"
}

func normalizeDashboardRole(role string) string {
	switch strings.TrimSpace(strings.ToLower(role)) {
	case "admin":
		return "admin"
	case "user", "member":
		return "user"
	default:
		return ""
	}
}

func (s *Server) authorizeDashboardMemberCreate(w http.ResponseWriter, r *http.Request, orgID, role string) bool {
	principal := principalFromContext(r.Context())
	if principal.Method != "dashboard_session" {
		return s.authorizeResource(w, r, orgID, "organization", orgID, "manage", "member.create")
	}
	if principal.OrgID != orgID {
		writeForbidden(w, "forbidden_org_scope")
		return false
	}
	switch principal.Role {
	case "super_admin":
		return role == "admin" || role == "user"
	case "admin":
		if role == "user" {
			return true
		}
		writeForbidden(w, "admin_can_only_create_users")
		return false
	default:
		writeForbidden(w, "forbidden_role")
		return false
	}
}

func (s *Server) authorizeDashboardMemberEdit(w http.ResponseWriter, r *http.Request, orgID string, target store.Member) bool {
	principal := principalFromContext(r.Context())
	if principal.Method != "dashboard_session" {
		return s.authorizeResource(w, r, orgID, "organization", orgID, "manage", "member.update")
	}
	if principal.OrgID != orgID {
		writeForbidden(w, "forbidden_org_scope")
		return false
	}
	if target.Role == "super_admin" && target.ID != principal.MemberID {
		writeForbidden(w, "super_admin_can_only_be_changed_by_self")
		return false
	}
	switch principal.Role {
	case "super_admin":
		return true
	case "admin":
		if target.Role == "user" {
			return true
		}
		writeForbidden(w, "admin_can_only_manage_users")
		return false
	default:
		writeForbidden(w, "forbidden_role")
		return false
	}
}

func (s *Server) authorizeResource(w http.ResponseWriter, r *http.Request, orgID, resourceType, resourceID, permission, action string) bool {
	principal := principalFromContext(r.Context())
	if !s.ensureOrgScope(w, r, orgID, action) {
		return false
	}
	if resourceType != "organization" && principal.MemberID != "" {
		adminDecision, err := s.authz.CheckPermission(r.Context(), store.PermissionCheck{
			OrgID:        scopedOrgID(r, orgID),
			ResourceType: "organization",
			ResourceID:   scopedOrgID(r, orgID),
			Permission:   "manage",
			SubjectType:  "member",
			SubjectID:    principal.MemberID,
		})
		if err != nil {
			s.recordAudit(r, scopedOrgID(r, orgID), action, "organization:"+scopedOrgID(r, orgID), "authz_error", map[string]any{"error": err.Error()})
			writeErrorText(w, http.StatusServiceUnavailable, "authz_unavailable")
			return false
		}
		if adminDecision.Allowed {
			return true
		}
	}
	if resourceType == "" || resourceID == "" || permission == "" || principal.MemberID == "" {
		writeForbidden(w, "forbidden")
		return false
	}
	decision, err := s.authz.CheckPermission(r.Context(), store.PermissionCheck{
		OrgID:        scopedOrgID(r, orgID),
		ResourceType: resourceType,
		ResourceID:   resourceID,
		Permission:   permission,
		SubjectType:  "member",
		SubjectID:    principal.MemberID,
	})
	if err != nil {
		s.recordAudit(r, scopedOrgID(r, orgID), action, resourceType+":"+resourceID, "authz_error", map[string]any{"error": err.Error()})
		writeErrorText(w, http.StatusServiceUnavailable, "authz_unavailable")
		return false
	}
	if !decision.Allowed {
		s.recordAudit(r, scopedOrgID(r, orgID), action, resourceType+":"+resourceID, "denied", map[string]any{"reason": decision.Reason})
		writeForbidden(w, "forbidden")
		return false
	}
	return true
}

func (s *Server) resourceAllowed(r *http.Request, orgID, resourceType, resourceID, permission string) (bool, error) {
	principal := principalFromContext(r.Context())
	if resourceType == "" || resourceID == "" || permission == "" || principal.MemberID == "" {
		return false, nil
	}
	decision, err := s.authz.CheckPermission(r.Context(), store.PermissionCheck{
		OrgID:        scopedOrgID(r, orgID),
		ResourceType: resourceType,
		ResourceID:   resourceID,
		Permission:   permission,
		SubjectType:  "member",
		SubjectID:    principal.MemberID,
	})
	if err != nil {
		return false, err
	}
	return decision.Allowed, nil
}

func (s *Server) authorizeAuditRead(w http.ResponseWriter, r *http.Request, orgID string) bool {
	principal := principalFromContext(r.Context())
	if orgID == "" {
		orgID = principal.OrgID
	}
	return s.authorizeResource(w, r, orgID, "organization", orgID, "manage", "audit.read")
}

func (s *Server) authorizeRelationshipWrite(w http.ResponseWriter, r *http.Request, relationship store.Relationship) bool {
	return s.authorizeResource(w, r, relationship.OrgID, "organization", relationship.OrgID, "manage", "authz.relationship.write")
}

func (s *Server) authorizePermissionCheck(w http.ResponseWriter, r *http.Request, check store.PermissionCheck) bool {
	principal := principalFromContext(r.Context())
	if !s.ensureOrgScope(w, r, check.OrgID, "authz.permission.check") {
		return false
	}
	if check.SubjectType == "member" && check.SubjectID == principal.MemberID {
		return true
	}
	return s.authorizeResource(w, r, check.OrgID, "organization", check.OrgID, "manage", "authz.permission.check")
}

func (s *Server) authorizeReviewDecision(w http.ResponseWriter, r *http.Request, reviewID, action string) bool {
	review, err := s.backend.GetReview(r.Context(), reviewID)
	if err != nil {
		writeStoreResult(w, http.StatusOK, review, err)
		return false
	}
	item, err := s.backend.GetMemory(r.Context(), review.MemoryID)
	if err != nil {
		writeStoreResult(w, http.StatusOK, item, err)
		return false
	}
	principal := principalFromContext(r.Context())
	if !s.ensureOrgScope(w, r, review.OrgID, "memory.review."+action) {
		return false
	}
	orgAdmin, err := s.resourceAllowed(r, review.OrgID, "organization", review.OrgID, "manage")
	if err != nil {
		writeErrorText(w, http.StatusServiceUnavailable, "authz_unavailable")
		return false
	}
	if orgAdmin {
		return true
	}
	if item.Scope == "personal" && item.SubjectMemberID == principal.MemberID {
		return true
	}
	if item.Scope == "team_shared" {
		allowed, err := s.resourceAllowed(r, item.OrgID, "organization", item.OrgID, "review")
		if err != nil {
			writeErrorText(w, http.StatusServiceUnavailable, "authz_unavailable")
			return false
		}
		if allowed {
			return true
		}
	}
	writeForbidden(w, "forbidden")
	return false
}

func (s *Server) authorizeTeamBackupJob(w http.ResponseWriter, r *http.Request, job store.BackupJob, action string) bool {
	if job.MemberID != store.TeamBackupMemberID {
		writeForbidden(w, "forbidden_backup_scope")
		return false
	}
	return s.authorizeResource(w, r, job.OrgID, "organization", job.OrgID, "manage", action)
}

func (s *Server) authorizeTeamSoulBackupJob(w http.ResponseWriter, r *http.Request, job store.BackupJob, action string) bool {
	if job.MemberID != store.TeamSoulBackupMemberID {
		writeForbidden(w, "forbidden_backup_scope")
		return false
	}
	return s.authorizeResource(w, r, job.OrgID, "organization", job.OrgID, "manage", action)
}

func (s *Server) authorizeDeletionExecute(w http.ResponseWriter, r *http.Request, req store.DeletionRequest) bool {
	principal := principalFromContext(r.Context())
	if !s.ensureOrgScope(w, r, req.OrgID, "deletion.request.execute") {
		return false
	}
	if req.TargetMemberID == principal.MemberID {
		return true
	}
	return s.authorizeResource(w, r, req.OrgID, "organization", req.OrgID, "manage", "deletion.request.execute")
}

func (s *Server) authorizeRuntimeEvent(w http.ResponseWriter, r *http.Request, payload map[string]any) bool {
	principal := principalFromContext(r.Context())
	sessionID := stringValue(payload, "session_id")
	if sessionID == "" {
		writeForbidden(w, "forbidden_session_scope")
		return false
	}
	session, err := s.backend.GetCloudSession(r.Context(), sessionID)
	if err != nil {
		writeStoreResult(w, http.StatusOK, session, err)
		return false
	}
	if stringValue(payload, "org_id") != "" && stringValue(payload, "org_id") != session.OrgID {
		writeForbidden(w, "forbidden_org_scope")
		return false
	}
	if !s.ensureOrgScope(w, r, session.OrgID, "runtime.event.append") {
		return false
	}
	if session.OwnerMemberID == principal.MemberID {
		return true
	}
	return s.authorizeResource(w, r, session.OrgID, "organization", session.OrgID, "run_agent", "runtime.event.append")
}

func (s *Server) ensureOrgScope(w http.ResponseWriter, r *http.Request, orgID, action string) bool {
	principal := principalFromContext(r.Context())
	if principal.OrgID == "" || principal.MemberID == "" {
		writeForbidden(w, "missing_principal_scope")
		return false
	}
	if orgID != "" && orgID != principal.OrgID {
		s.recordAudit(r, orgID, action, "organization:"+orgID, "denied", map[string]any{"reason": "org_scope_mismatch"})
		writeForbidden(w, "forbidden_org_scope")
		return false
	}
	return true
}

func scopedOrgID(r *http.Request, orgID string) string {
	if orgID != "" {
		return orgID
	}
	return principalFromContext(r.Context()).OrgID
}

func (s *Server) authorizeMemoryCreate(w http.ResponseWriter, r *http.Request, payload map[string]any) bool {
	principal := principalFromContext(r.Context())
	orgID := stringValue(payload, "org_id")
	if !s.ensureOrgScope(w, r, orgID, "memory.create") {
		return false
	}
	scope := stringValue(payload, "scope")
	switch scope {
	case "team_shared":
		if stringValue(payload, "created_by_member_id") == "" {
			payload["created_by_member_id"] = principal.MemberID
		}
		return s.authorizeResource(w, r, orgID, "organization", orgID, "write_team", "memory.create_team_shared")
	default:
		writeForbidden(w, "forbidden_memory_scope")
		return false
	}
}

func (s *Server) authorizeMemoryItem(w http.ResponseWriter, r *http.Request, item store.MemoryItem, teamPermission, action string) bool {
	principal := principalFromContext(r.Context())
	if !s.ensureOrgScope(w, r, item.OrgID, action) {
		return false
	}
	if item.Scope == "personal" {
		if item.SubjectMemberID != principal.MemberID {
			return s.authorizeResource(w, r, item.OrgID, "organization", item.OrgID, "manage", action)
		}
		return true
	}
	return s.authorizeResource(w, r, item.OrgID, "organization", item.OrgID, teamPermission, action)
}

func (s *Server) filterMemoryItemsForPrincipal(r *http.Request, items []store.MemoryItem) []store.MemoryItem {
	principal := principalFromContext(r.Context())
	filtered := make([]store.MemoryItem, 0, len(items))
	for _, item := range items {
		if item.OrgID != principal.OrgID {
			continue
		}
		if item.Scope == "personal" {
			if item.SubjectMemberID == principal.MemberID {
				filtered = append(filtered, item)
			} else if allowed, err := s.resourceAllowed(r, item.OrgID, "organization", item.OrgID, "manage"); err == nil && allowed {
				filtered = append(filtered, item)
			}
			continue
		}
		if s.memoryTeamAllowed(r, item, "read_team") {
			filtered = append(filtered, item)
		}
	}
	return filtered
}

func (s *Server) authorizeObservation(w http.ResponseWriter, r *http.Request, payload map[string]any) bool {
	principal := principalFromContext(r.Context())
	orgID := stringValue(payload, "org_id")
	if !s.ensureOrgScope(w, r, orgID, "memory.observation.create") {
		return false
	}
	memberID := stringValue(payload, "member_id")
	if memberID != "" && memberID != principal.MemberID {
		writeForbidden(w, "forbidden_member_scope")
		return false
	}
	return s.authorizeResource(w, r, orgID, "organization", orgID, "run_agent", "memory.observation.create")
}

func (s *Server) authorizePrefetchRequest(w http.ResponseWriter, r *http.Request, req store.PrefetchRequest) bool {
	principal := principalFromContext(r.Context())
	if !s.ensureOrgScope(w, r, req.OrgID, "memory.prefetch") {
		return false
	}
	if req.MemberID == "" || req.MemberID != principal.MemberID {
		return s.authorizeResource(w, r, req.OrgID, "organization", req.OrgID, "manage", "memory.prefetch")
	}
	return true
}

func (s *Server) filterPrefetchPartitions(r *http.Request, req store.PrefetchRequest, partitions []store.MemoryPartition) []store.MemoryPartition {
	principal := principalFromContext(r.Context())
	filteredPartitions := []store.MemoryPartition{}
	for _, partition := range partitions {
		filteredItems := []store.MemoryItem{}
		for _, item := range partition.Items {
			if item.OrgID != principal.OrgID {
				continue
			}
			if item.Scope == "personal" {
				if item.SubjectMemberID == principal.MemberID {
					filteredItems = append(filteredItems, item)
				} else if allowed, err := s.resourceAllowed(r, item.OrgID, "organization", item.OrgID, "manage"); err == nil && allowed {
					filteredItems = append(filteredItems, item)
				}
				continue
			}
			if s.memoryTeamAllowed(r, item, "read_team") {
				filteredItems = append(filteredItems, item)
			}
		}
		if len(filteredItems) > 0 {
			filteredPartitions = append(filteredPartitions, store.MemoryPartition{Scope: partition.Scope, Items: filteredItems})
		}
	}
	return filteredPartitions
}

func (s *Server) memoryTeamAllowed(r *http.Request, item store.MemoryItem, permission string) bool {
	principal := principalFromContext(r.Context())
	if allowed, err := s.resourceAllowed(r, item.OrgID, "organization", item.OrgID, "manage"); err == nil && allowed {
		return true
	}
	decision, err := s.authz.CheckPermission(r.Context(), store.PermissionCheck{
		OrgID:        item.OrgID,
		ResourceType: "organization",
		ResourceID:   item.OrgID,
		Permission:   permission,
		SubjectType:  "member",
		SubjectID:    principal.MemberID,
	})
	return err == nil && decision.Allowed
}

func (s *Server) authorizePersonalMemberScope(w http.ResponseWriter, r *http.Request, orgID, memberID, action string) bool {
	principal := principalFromContext(r.Context())
	if orgID != "" && !s.ensureOrgScope(w, r, orgID, action) {
		return false
	}
	if memberID == "" {
		writeForbidden(w, "forbidden_member_scope")
		return false
	}
	if memberID == principal.MemberID {
		return true
	}
	if orgID != "" {
		return s.authorizeResource(w, r, orgID, "organization", orgID, "manage", action)
	}
	writeForbidden(w, "forbidden_member_scope")
	return false
}

func (s *Server) authorizeDeletionRequest(w http.ResponseWriter, r *http.Request, payload map[string]any) bool {
	principal := principalFromContext(r.Context())
	orgID := stringValue(payload, "org_id")
	if !s.ensureOrgScope(w, r, orgID, "deletion.request.create") {
		return false
	}
	targetMemberID := stringValue(payload, "target_member_id")
	if targetMemberID == principal.MemberID {
		return true
	}
	return s.authorizeResource(w, r, orgID, "organization", orgID, "manage", "deletion.request.create")
}

func principalFromContext(ctx context.Context) authn.Principal {
	principal, _ := ctx.Value(principalContextKey{}).(authn.Principal)
	return principal
}

func writeStoreResult(w http.ResponseWriter, statusCode int, payload any, err error) {
	if err == nil {
		writeJSON(w, statusCode, payload)
		return
	}
	if errors.Is(err, store.ErrNotFound) {
		writeErrorText(w, http.StatusNotFound, "not_found")
		return
	}
	writeError(w, http.StatusBadRequest, err)
}

func decodeJSON(w http.ResponseWriter, r *http.Request, target any) bool {
	if r.Body == nil || r.Body == http.NoBody {
		return true
	}
	if err := json.NewDecoder(r.Body).Decode(target); err != nil {
		writeError(w, http.StatusBadRequest, err)
		return false
	}
	return true
}

func writeJSON(w http.ResponseWriter, statusCode int, payload any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(statusCode)
	_ = json.NewEncoder(w).Encode(payload)
}

func writeError(w http.ResponseWriter, statusCode int, err error) {
	writeErrorText(w, statusCode, err.Error())
}

func writeErrorText(w http.ResponseWriter, statusCode int, detail string) {
	writeJSON(w, statusCode, map[string]string{"detail": detail})
}

func writeForbidden(w http.ResponseWriter, detail string) {
	writeErrorText(w, http.StatusForbidden, detail)
}

func pathParts(path string) []string {
	path = strings.Trim(path, "/")
	if path == "" {
		return nil
	}
	return strings.Split(path, "/")
}

func stringValue(payload map[string]any, key string) string {
	value, ok := payload[key]
	if !ok || value == nil {
		return ""
	}
	if s, ok := value.(string); ok {
		return s
	}
	return fmt.Sprint(value)
}

func boolValue(payload map[string]any, key string, fallback bool) bool {
	value, ok := payload[key]
	if !ok {
		return fallback
	}
	if b, ok := value.(bool); ok {
		return b
	}
	return fallback
}

func intValue(payload map[string]any, key string, fallback int) int {
	value, ok := payload[key]
	if !ok {
		return fallback
	}
	switch typed := value.(type) {
	case int:
		return typed
	case float64:
		return int(typed)
	case string:
		parsed, err := strconv.Atoi(typed)
		if err == nil {
			return parsed
		}
	}
	return fallback
}

func intQuery(r *http.Request, key string, fallback int) int {
	value := r.URL.Query().Get(key)
	if value == "" {
		return fallback
	}
	parsed, err := strconv.Atoi(value)
	if err != nil {
		return fallback
	}
	return parsed
}

func defaultString(value, fallback string) string {
	if value == "" {
		return fallback
	}
	return value
}
