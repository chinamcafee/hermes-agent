package store

import (
	"context"
	"errors"
	"time"
)

var ErrNotFound = errors.New("not found")

const TeamBackupMemberID = "__team_memory__"
const TeamSoulBackupMemberID = "__team_soul__"

type Organization struct {
	ID     string `json:"id"`
	Slug   string `json:"slug"`
	Name   string `json:"name"`
	Status string `json:"status"`
}

type Member struct {
	ID           string `json:"id"`
	OrgID        string `json:"org_id"`
	UserID       string `json:"user_id"`
	Email        string `json:"email"`
	DisplayName  string `json:"display_name"`
	Role         string `json:"role"`
	Status       string `json:"status"`
	PasswordHash string `json:"-"`
}

type MemoryItem struct {
	ID                string    `json:"id"`
	OrgID             string    `json:"org_id"`
	Scope             string    `json:"scope"`
	SubjectMemberID   string    `json:"subject_member_id,omitempty"`
	TeamID            string    `json:"team_id,omitempty"`
	ProjectID         string    `json:"project_id,omitempty"`
	Status            string    `json:"status"`
	Sensitivity       string    `json:"sensitivity"`
	MemoryType        string    `json:"memory_type"`
	SourceType        string    `json:"source_type,omitempty"`
	SourceMemberID    string    `json:"source_member_id,omitempty"`
	CreatedByMemberID string    `json:"created_by_member_id,omitempty"`
	Content           string    `json:"content"`
	Embedding         []float64 `json:"embedding,omitempty"`
	Version           int       `json:"version"`
}

type ReviewItem struct {
	ID                  string `json:"id"`
	OrgID               string `json:"org_id"`
	MemoryID            string `json:"memory_id"`
	Status              string `json:"status"`
	ReviewKind          string `json:"review_kind"`
	SubmittedByMemberID string `json:"submitted_by_member_id,omitempty"`
}

type ReviewDecision struct {
	ID           string `json:"id"`
	Status       string `json:"status"`
	MemoryID     string `json:"memory_id"`
	MemoryStatus string `json:"memory_status"`
}

type Observation struct {
	ID        string         `json:"id"`
	OrgID     string         `json:"org_id"`
	SessionID string         `json:"session_id,omitempty"`
	MemberID  string         `json:"member_id,omitempty"`
	TeamID    string         `json:"team_id,omitempty"`
	ProjectID string         `json:"project_id,omitempty"`
	Status    string         `json:"status"`
	Payload   map[string]any `json:"observation"`
}

type MemoryPartition struct {
	Scope string       `json:"scope"`
	Items []MemoryItem `json:"items"`
}

type BackupPolicy struct {
	OrgID          string `json:"org_id"`
	MemberID       string `json:"member_id"`
	Cadence        string `json:"cadence"`
	Enabled        bool   `json:"enabled"`
	RetentionCount int    `json:"retention_count"`
	LastRunAt      string `json:"last_run_at,omitempty"`
	NextRunAt      string `json:"next_run_at,omitempty"`
}

type AuditEvent struct {
	ID       string         `json:"id"`
	OrgID    string         `json:"org_id"`
	ActorID  string         `json:"actor_id,omitempty"`
	Action   string         `json:"action"`
	Resource string         `json:"resource"`
	Decision string         `json:"decision"`
	Metadata map[string]any `json:"metadata,omitempty"`
}

type Relationship struct {
	OrgID          string `json:"org_id"`
	ResourceType   string `json:"resource_type"`
	ResourceID     string `json:"resource_id"`
	Relation       string `json:"relation"`
	SubjectType    string `json:"subject_type"`
	SubjectID      string `json:"subject_id"`
	IdempotencyKey string `json:"idempotency_key"`
}

type PermissionCheck struct {
	OrgID        string `json:"org_id"`
	ResourceType string `json:"resource_type"`
	ResourceID   string `json:"resource_id"`
	Permission   string `json:"permission"`
	SubjectType  string `json:"subject_type"`
	SubjectID    string `json:"subject_id"`
}

type PermissionDecision struct {
	Allowed bool     `json:"allowed"`
	Reason  string   `json:"reason"`
	Path    []string `json:"path,omitempty"`
}

type BackupJob struct {
	ID             string         `json:"id"`
	OrgID          string         `json:"org_id"`
	MemberID       string         `json:"member_id"`
	Status         string         `json:"status"`
	ObjectKey      string         `json:"object_key"`
	ObjectUploaded bool           `json:"object_uploaded"`
	ChecksumSHA256 string         `json:"checksum_sha256"`
	ItemCount      int            `json:"item_count"`
	Manifest       map[string]any `json:"manifest,omitempty"`
	Items          []MemoryItem   `json:"items,omitempty"`
	CreatedAt      time.Time      `json:"created_at,omitempty"`
}

type RestorePreview struct {
	BackupID    string `json:"backup_id"`
	MemberID    string `json:"member_id"`
	CreateCount int    `json:"create_count"`
	SkipCount   int    `json:"skip_count"`
	Mode        string `json:"mode"`
}

type RestoreExecution struct {
	BackupID      string `json:"backup_id"`
	MemberID      string `json:"member_id"`
	Mode          string `json:"mode"`
	RestoredCount int    `json:"restored_count"`
	Status        string `json:"status"`
}

type OrgExport struct {
	ID              string         `json:"id"`
	OrgID           string         `json:"org_id"`
	Status          string         `json:"status"`
	TeamSharedCount int            `json:"team_shared_count"`
	PersonalCount   int            `json:"personal_count"`
	Manifest        map[string]any `json:"manifest"`
}

type DeletionRequest struct {
	ID             string `json:"id"`
	OrgID          string `json:"org_id"`
	TargetMemberID string `json:"target_member_id"`
	RequestedBy    string `json:"requested_by"`
	DeletionScope  string `json:"deletion_scope"`
	Reason         string `json:"reason"`
	Status         string `json:"status"`
}

type ToolPolicyRule struct {
	OrgID     string `json:"org_id"`
	ToolName  string `json:"tool_name"`
	RiskLevel string `json:"risk_level"`
	Decision  string `json:"decision"`
	UpdatedBy string `json:"updated_by,omitempty"`
}

type ToolPolicyRequest struct {
	OrgID     string `json:"org_id"`
	MemberID  string `json:"member_id"`
	ToolName  string `json:"tool_name"`
	RiskLevel string `json:"risk_level"`
}

type ToolPolicyDecision struct {
	Decision      string `json:"decision"`
	Reason        string `json:"reason"`
	ApprovalID    string `json:"approval_id,omitempty"`
	EffectiveRule string `json:"effective_rule,omitempty"`
}

type CloudSession struct {
	ID            string `json:"id"`
	OrgID         string `json:"org_id"`
	TeamID        string `json:"team_id"`
	ProjectID     string `json:"project_id,omitempty"`
	OwnerMemberID string `json:"owner_member_id,omitempty"`
	Title         string `json:"title"`
	Status        string `json:"status"`
}

type RuntimeEvent struct {
	ID        string         `json:"id"`
	OrgID     string         `json:"org_id"`
	SessionID string         `json:"session_id"`
	EventType string         `json:"event_type"`
	Payload   map[string]any `json:"payload,omitempty"`
	CreatedAt time.Time      `json:"created_at"`
}

type TeamSoul struct {
	OrgID          string `json:"org_id"`
	TeamID         string `json:"team_id"`
	Content        string `json:"content"`
	Version        int    `json:"version"`
	ChecksumSHA256 string `json:"checksum_sha256"`
	UpdatedBy      string `json:"updated_by,omitempty"`
	UpdatedAt      string `json:"updated_at,omitempty"`
}

type MemoryFilter struct {
	OrgID       string
	Scope       string
	Status      string
	MemoryType  string
	Sensitivity string
}

type PrefetchRequest struct {
	Query           string
	OrgID           string
	MemberID        string
	TeamID          string
	ProjectID       string
	IncludePersonal bool
	Limit           int
	QueryEmbedding  []float64
}

type Backend interface {
	Ping(ctx context.Context) error

	CreateOrganization(ctx context.Context, slug, name string) (Organization, error)
	ListOrganizations(ctx context.Context) ([]Organization, error)
	CreateMember(ctx context.Context, orgID, email, displayName, userID, role, passwordHash string) (Member, error)
	InviteMember(ctx context.Context, orgID, email, displayName, userID, role string) (Member, error)
	GetMember(ctx context.Context, orgID, memberID string) (Member, error)
	GetMemberByUserID(ctx context.Context, orgID, userID string) (Member, error)
	UpdateMember(ctx context.Context, orgID, memberID, email, displayName string) (Member, error)
	ListMembers(ctx context.Context, orgID string) ([]Member, error)
	DisableMember(ctx context.Context, orgID, memberID string) (Member, error)

	CreateMemory(ctx context.Context, payload map[string]any) (MemoryItem, error)
	ListMemory(ctx context.Context, filter MemoryFilter) ([]MemoryItem, error)
	GetMemory(ctx context.Context, memoryID string) (MemoryItem, error)
	UpdateMemory(ctx context.Context, memoryID string, payload map[string]any) (MemoryItem, error)
	SetMemoryStatus(ctx context.Context, memoryID, status string) (MemoryItem, error)
	DeleteMemory(ctx context.Context, memoryID string) (MemoryItem, error)
	CreateObservation(ctx context.Context, payload map[string]any) (Observation, error)
	Prefetch(ctx context.Context, req PrefetchRequest) ([]MemoryPartition, error)
	ListReviews(ctx context.Context, orgID, status, reviewKind string, limit int) ([]ReviewItem, error)
	GetReview(ctx context.Context, reviewID string) (ReviewItem, error)
	ApproveReview(ctx context.Context, reviewID, actorMemberID string, edits map[string]any) (ReviewDecision, error)
	RejectReview(ctx context.Context, reviewID, actorMemberID, reason string) (ReviewDecision, error)

	GetBackupPolicy(ctx context.Context, orgID, memberID string) (BackupPolicy, error)
	UpsertBackupPolicy(ctx context.Context, policy BackupPolicy) (BackupPolicy, error)
	ListBackupPolicies(ctx context.Context, enabledOnly bool) ([]BackupPolicy, error)
	MarkBackupPolicyRun(ctx context.Context, orgID, memberID, lastRunAt, nextRunAt string) error
	GetTeamBackupPolicy(ctx context.Context, orgID string) (BackupPolicy, error)
	UpsertTeamBackupPolicy(ctx context.Context, policy BackupPolicy) (BackupPolicy, error)
	GetTeamSoulBackupPolicy(ctx context.Context, orgID string) (BackupPolicy, error)
	UpsertTeamSoulBackupPolicy(ctx context.Context, policy BackupPolicy) (BackupPolicy, error)

	AppendAuditEvent(ctx context.Context, event AuditEvent) (AuditEvent, error)
	ListAuditEvents(ctx context.Context, orgID string, limit int) ([]AuditEvent, error)
	WriteRelationship(ctx context.Context, relationship Relationship) (Relationship, error)
	CheckPermission(ctx context.Context, check PermissionCheck) (PermissionDecision, error)
	RunTeamMemoryBackup(ctx context.Context, orgID string) (BackupJob, error)
	RunTeamSoulBackup(ctx context.Context, orgID, teamID string) (BackupJob, error)
	ListBackupJobs(ctx context.Context, orgID, memberID string, limit int) ([]BackupJob, error)
	GetBackupJob(ctx context.Context, backupID string) (BackupJob, error)
	UpdateBackupObject(ctx context.Context, backupID, checksumSHA256 string, manifest map[string]any) (BackupJob, error)
	UpdateBackupItems(ctx context.Context, backupID string, items []MemoryItem) (BackupJob, error)
	PruneBackupJobs(ctx context.Context, orgID, memberID string, keep int) (int, error)
	PreviewTeamMemoryRestore(ctx context.Context, backupID, mode string) (RestorePreview, error)
	ExecuteTeamMemoryRestore(ctx context.Context, backupID, mode string) (RestoreExecution, error)
	PreviewTeamSoulRestore(ctx context.Context, backupID, mode string) (RestorePreview, error)
	ExecuteTeamSoulRestore(ctx context.Context, backupID, mode string) (RestoreExecution, error)
	CreateOrgExport(ctx context.Context, orgID string) (OrgExport, error)
	CreateDeletionRequest(ctx context.Context, req DeletionRequest) (DeletionRequest, error)
	GetDeletionRequest(ctx context.Context, requestID string) (DeletionRequest, error)
	ExecuteDeletionRequest(ctx context.Context, requestID, actorMemberID string) (DeletionRequest, error)
	UpsertToolPolicyRule(ctx context.Context, rule ToolPolicyRule) (ToolPolicyRule, error)
	EvaluateToolPolicy(ctx context.Context, req ToolPolicyRequest) (ToolPolicyDecision, error)
	CreateCloudSession(ctx context.Context, session CloudSession) (CloudSession, error)
	GetCloudSession(ctx context.Context, sessionID string) (CloudSession, error)
	AppendRuntimeEvent(ctx context.Context, event RuntimeEvent) (RuntimeEvent, error)
	GetTeamSoul(ctx context.Context, orgID, teamID string) (TeamSoul, error)
	UpsertTeamSoul(ctx context.Context, soul TeamSoul) (TeamSoul, error)
}
