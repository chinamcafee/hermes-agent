package postgres

import (
	"context"
	"crypto/rand"
	"crypto/sha256"
	"database/sql"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"sort"
	"strings"
	"time"

	_ "github.com/jackc/pgx/v5/stdlib"

	"hermes-agent/team_cloud/internal/store"
)

type Store struct {
	db *sql.DB
}

const postgresEmbeddingDimension = 1536

func Open(ctx context.Context, databaseURL string, autoMigrate bool) (*Store, error) {
	if strings.TrimSpace(databaseURL) == "" {
		return nil, fmt.Errorf("database URL is required")
	}
	db, err := sql.Open("pgx", databaseURL)
	if err != nil {
		return nil, fmt.Errorf("open postgres: %w", err)
	}
	db.SetMaxOpenConns(20)
	db.SetMaxIdleConns(5)
	db.SetConnMaxLifetime(30 * time.Minute)

	s := &Store{db: db}
	if err := s.Ping(ctx); err != nil {
		_ = db.Close()
		return nil, fmt.Errorf("ping postgres: %w", err)
	}
	if autoMigrate {
		if err := s.ApplyMigrations(ctx); err != nil {
			_ = db.Close()
			return nil, fmt.Errorf("apply postgres schema: %w", err)
		}
	}
	return s, nil
}

func (s *Store) Close() error {
	return s.db.Close()
}

func (s *Store) Ping(ctx context.Context) error {
	return s.db.PingContext(ctx)
}

func (s *Store) ApplyMigrations(ctx context.Context) error {
	_, err := s.db.ExecContext(ctx, SchemaSQL)
	return err
}

func (s *Store) CreateOrganization(ctx context.Context, slug, name string) (store.Organization, error) {
	if slug == "" || name == "" {
		return store.Organization{}, fmt.Errorf("slug and name are required")
	}
	org := store.Organization{ID: slug, Slug: slug, Name: name, Status: "active"}
	_, err := s.db.ExecContext(ctx, `
insert into tcg_organizations(id, slug, name, status)
values ($1, $2, $3, $4)
on conflict (id) do update set
  slug = excluded.slug,
  name = excluded.name,
  status = excluded.status,
  updated_at = now()
`, org.ID, org.Slug, org.Name, org.Status)
	if err != nil {
		return store.Organization{}, err
	}
	return org, nil
}

func (s *Store) ListOrganizations(ctx context.Context) ([]store.Organization, error) {
	rows, err := s.db.QueryContext(ctx, `
select id, slug, name, status from tcg_organizations order by id
`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	out := []store.Organization{}
	for rows.Next() {
		var org store.Organization
		if err := rows.Scan(&org.ID, &org.Slug, &org.Name, &org.Status); err != nil {
			return nil, err
		}
		out = append(out, org)
	}
	return out, rows.Err()
}

func (s *Store) CreateMember(ctx context.Context, orgID, email, displayName, userID, role, passwordHash string) (store.Member, error) {
	return s.upsertMember(ctx, orgID, email, displayName, userID, role, "active", passwordHash)
}

func (s *Store) InviteMember(ctx context.Context, orgID, email, displayName, userID, role string) (store.Member, error) {
	return s.upsertMember(ctx, orgID, email, displayName, userID, role, "invited", "")
}

func (s *Store) upsertMember(ctx context.Context, orgID, email, displayName, userID, role, status, passwordHash string) (store.Member, error) {
	if ok, err := s.organizationExists(ctx, orgID); err != nil {
		return store.Member{}, err
	} else if !ok {
		return store.Member{}, store.ErrNotFound
	}
	if userID == "" {
		userID = email
	}
	if userID == "" {
		return store.Member{}, fmt.Errorf("user_id or email is required")
	}
	if role == "" {
		role = "user"
	}
	member := store.Member{
		ID:           orgID + ":" + userID,
		OrgID:        orgID,
		UserID:       userID,
		Email:        email,
		DisplayName:  displayName,
		Role:         role,
		Status:       status,
		PasswordHash: passwordHash,
	}
	_, err := s.db.ExecContext(ctx, `
insert into tcg_members(id, org_id, user_id, email, display_name, role, password_hash, status)
values ($1, $2, $3, $4, $5, $6, $7, $8)
on conflict (id) do update set
  email = excluded.email,
  display_name = excluded.display_name,
  role = excluded.role,
  password_hash = case when excluded.password_hash <> '' then excluded.password_hash else tcg_members.password_hash end,
  status = excluded.status,
  updated_at = now()
`, member.ID, member.OrgID, member.UserID, member.Email, member.DisplayName, member.Role, member.PasswordHash, member.Status)
	if err != nil {
		return store.Member{}, err
	}
	return member, nil
}

func (s *Store) GetMemberByUserID(ctx context.Context, orgID, userID string) (store.Member, error) {
	var member store.Member
	err := s.db.QueryRowContext(ctx, `
select id, org_id, user_id, email, display_name, role, status, password_hash
from tcg_members
where org_id = $1 and user_id = $2
`, orgID, userID).Scan(&member.ID, &member.OrgID, &member.UserID, &member.Email, &member.DisplayName, &member.Role, &member.Status, &member.PasswordHash)
	if errors.Is(err, sql.ErrNoRows) {
		return store.Member{}, store.ErrNotFound
	}
	return member, err
}

func (s *Store) GetMember(ctx context.Context, orgID, memberID string) (store.Member, error) {
	var member store.Member
	err := s.db.QueryRowContext(ctx, `
select id, org_id, user_id, email, display_name, role, status, password_hash
from tcg_members
where org_id = $1 and id = $2
`, orgID, memberID).Scan(&member.ID, &member.OrgID, &member.UserID, &member.Email, &member.DisplayName, &member.Role, &member.Status, &member.PasswordHash)
	if errors.Is(err, sql.ErrNoRows) {
		return store.Member{}, store.ErrNotFound
	}
	return member, err
}

func (s *Store) UpdateMember(ctx context.Context, orgID, memberID, email, displayName string) (store.Member, error) {
	var member store.Member
	err := s.db.QueryRowContext(ctx, `
update tcg_members
set email = $3, display_name = $4, updated_at = now()
where org_id = $1 and id = $2
returning id, org_id, user_id, email, display_name, role, status
`, orgID, memberID, email, displayName).Scan(&member.ID, &member.OrgID, &member.UserID, &member.Email, &member.DisplayName, &member.Role, &member.Status)
	if errors.Is(err, sql.ErrNoRows) {
		return store.Member{}, store.ErrNotFound
	}
	return member, err
}

func (s *Store) ListMembers(ctx context.Context, orgID string) ([]store.Member, error) {
	if ok, err := s.organizationExists(ctx, orgID); err != nil {
		return nil, err
	} else if !ok {
		return nil, store.ErrNotFound
	}
	rows, err := s.db.QueryContext(ctx, `
select id, org_id, user_id, email, display_name, role, status
from tcg_members
where org_id = $1
order by id
`, orgID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	out := []store.Member{}
	for rows.Next() {
		var member store.Member
		if err := rows.Scan(&member.ID, &member.OrgID, &member.UserID, &member.Email, &member.DisplayName, &member.Role, &member.Status); err != nil {
			return nil, err
		}
		out = append(out, member)
	}
	return out, rows.Err()
}

func (s *Store) DisableMember(ctx context.Context, orgID, memberID string) (store.Member, error) {
	var member store.Member
	err := s.db.QueryRowContext(ctx, `
update tcg_members
set status = 'suspended', updated_at = now()
where org_id = $1 and id = $2
returning id, org_id, user_id, email, display_name, role, status
`, orgID, memberID).Scan(&member.ID, &member.OrgID, &member.UserID, &member.Email, &member.DisplayName, &member.Role, &member.Status)
	if errors.Is(err, sql.ErrNoRows) {
		return store.Member{}, store.ErrNotFound
	}
	return member, err
}

func (s *Store) CreateMemory(ctx context.Context, payload map[string]any) (store.MemoryItem, error) {
	scope := stringValue(payload, "scope")
	status := stringValue(payload, "status")
	if status == "" {
		if scope == "team_shared" {
			status = "pending_review"
		} else {
			status = "active"
		}
	}
	item := store.MemoryItem{
		ID:                randomID("mem"),
		OrgID:             stringValue(payload, "org_id"),
		Scope:             scope,
		SubjectMemberID:   stringValue(payload, "subject_member_id"),
		TeamID:            stringValue(payload, "team_id"),
		ProjectID:         stringValue(payload, "project_id"),
		Status:            status,
		Sensitivity:       defaultString(stringValue(payload, "sensitivity"), "normal"),
		MemoryType:        defaultString(stringValue(payload, "memory_type"), "fact"),
		SourceType:        stringValue(payload, "source_type"),
		SourceMemberID:    stringValue(payload, "source_member_id"),
		CreatedByMemberID: stringValue(payload, "created_by_member_id"),
		Content:           stringValue(payload, "content"),
		Embedding:         store.Float64Slice(payload["embedding"]),
		Version:           1,
	}
	normalizeMemorySource(&item)
	if err := store.ValidateEmbedding(item.Embedding); err != nil {
		return store.MemoryItem{}, err
	}
	if err := validatePostgresEmbedding(item.Embedding); err != nil {
		return store.MemoryItem{}, err
	}
	if err := validateMemory(item); err != nil {
		return store.MemoryItem{}, err
	}

	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		return store.MemoryItem{}, err
	}
	defer rollbackUnlessCommitted(tx)

	_, err = tx.ExecContext(ctx, `
insert into tcg_memory_items(
  id, org_id, scope, subject_member_id, team_id, project_id,
  status, sensitivity, memory_type, source_type, source_member_id, created_by_member_id,
  content, embedding, version
)
values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, nullif($14, '')::vector, $15)
`, item.ID, item.OrgID, item.Scope, item.SubjectMemberID, item.TeamID, item.ProjectID, item.Status, item.Sensitivity, item.MemoryType, item.SourceType, item.SourceMemberID, item.CreatedByMemberID, item.Content, store.VectorLiteral(item.Embedding), item.Version)
	if err != nil {
		return store.MemoryItem{}, err
	}
	if item.Scope == "team_shared" && item.Status == "pending_review" {
		review := store.ReviewItem{
			ID:                  randomID("review"),
			OrgID:               item.OrgID,
			MemoryID:            item.ID,
			Status:              "pending",
			ReviewKind:          "team_shared_memory",
			SubmittedByMemberID: stringValue(payload, "created_by_member_id"),
		}
		_, err = tx.ExecContext(ctx, `
insert into tcg_memory_review_items(
  id, org_id, memory_id, status, review_kind, submitted_by_member_id
)
values ($1, $2, $3, $4, $5, $6)
`, review.ID, review.OrgID, review.MemoryID, review.Status, review.ReviewKind, review.SubmittedByMemberID)
		if err != nil {
			return store.MemoryItem{}, err
		}
	}
	if err := tx.Commit(); err != nil {
		return store.MemoryItem{}, err
	}
	return item, nil
}

func (s *Store) ListMemory(ctx context.Context, filter store.MemoryFilter) ([]store.MemoryItem, error) {
	rows, err := s.db.QueryContext(ctx, `
select id, org_id, scope, subject_member_id, team_id, project_id,
       status, sensitivity, memory_type, source_type, source_member_id, created_by_member_id,
       content, coalesce(embedding::text, ''), version
from tcg_memory_items
where org_id = $1
  and ($2 = '' or scope = $2)
  and ($3 = '' or status = $3)
  and ($4 = '' or memory_type = $4)
  and ($5 = '' or sensitivity = $5)
order by id
`, filter.OrgID, filter.Scope, filter.Status, filter.MemoryType, filter.Sensitivity)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	return scanMemoryRows(rows)
}

func (s *Store) GetMemory(ctx context.Context, memoryID string) (store.MemoryItem, error) {
	return s.getMemory(ctx, memoryID)
}

func (s *Store) UpdateMemory(ctx context.Context, memoryID string, payload map[string]any) (store.MemoryItem, error) {
	item, err := s.getMemory(ctx, memoryID)
	if err != nil {
		return store.MemoryItem{}, err
	}
	if content := stringValue(payload, "content"); content != "" {
		item.Content = content
	}
	if memoryType := stringValue(payload, "memory_type"); memoryType != "" {
		item.MemoryType = memoryType
	}
	if sensitivity := stringValue(payload, "sensitivity"); sensitivity != "" {
		item.Sensitivity = sensitivity
	}
	if status := stringValue(payload, "status"); status != "" {
		item.Status = status
	}
	if sourceType := stringValue(payload, "source_type"); sourceType != "" {
		item.SourceType = sourceType
	}
	if sourceMemberID := stringValue(payload, "source_member_id"); sourceMemberID != "" {
		item.SourceMemberID = sourceMemberID
	}
	if createdByMemberID := stringValue(payload, "created_by_member_id"); createdByMemberID != "" {
		item.CreatedByMemberID = createdByMemberID
	}
	normalizeMemorySource(&item)
	if _, ok := payload["embedding"]; ok {
		item.Embedding = store.Float64Slice(payload["embedding"])
		if err := store.ValidateEmbedding(item.Embedding); err != nil {
			return store.MemoryItem{}, err
		}
		if err := validatePostgresEmbedding(item.Embedding); err != nil {
			return store.MemoryItem{}, err
		}
	}
	if err := validateMemory(item); err != nil {
		return store.MemoryItem{}, err
	}
	item.Version++
	_, err = s.db.ExecContext(ctx, `
update tcg_memory_items
set content = $2,
    memory_type = $3,
    sensitivity = $4,
    status = $5,
    source_type = $6,
    source_member_id = $7,
    created_by_member_id = $8,
    embedding = nullif($9, '')::vector,
    version = $10,
    updated_at = now()
where id = $1
`, item.ID, item.Content, item.MemoryType, item.Sensitivity, item.Status, item.SourceType, item.SourceMemberID, item.CreatedByMemberID, store.VectorLiteral(item.Embedding), item.Version)
	if err != nil {
		return store.MemoryItem{}, err
	}
	return item, nil
}

func (s *Store) SetMemoryStatus(ctx context.Context, memoryID, status string) (store.MemoryItem, error) {
	var item store.MemoryItem
	err := s.db.QueryRowContext(ctx, `
update tcg_memory_items
set status = $2, version = version + 1, updated_at = now()
where id = $1
returning id, org_id, scope, subject_member_id, team_id, project_id,
          status, sensitivity, memory_type, source_type, source_member_id, created_by_member_id,
          content, coalesce(embedding::text, ''), version
`, memoryID, status).Scan(
		&item.ID, &item.OrgID, &item.Scope, &item.SubjectMemberID, &item.TeamID, &item.ProjectID,
		&item.Status, &item.Sensitivity, &item.MemoryType, &item.SourceType, &item.SourceMemberID, &item.CreatedByMemberID,
		&item.Content, (*vectorScanTarget)(&item.Embedding), &item.Version,
	)
	if errors.Is(err, sql.ErrNoRows) {
		return store.MemoryItem{}, store.ErrNotFound
	}
	return item, err
}

func (s *Store) DeleteMemory(ctx context.Context, memoryID string) (store.MemoryItem, error) {
	var item store.MemoryItem
	err := s.db.QueryRowContext(ctx, `
delete from tcg_memory_items
where id = $1
returning id, org_id, scope, subject_member_id, team_id, project_id,
          status, sensitivity, memory_type, source_type, source_member_id, created_by_member_id,
          content, coalesce(embedding::text, ''), version
`, memoryID).Scan(
		&item.ID, &item.OrgID, &item.Scope, &item.SubjectMemberID, &item.TeamID, &item.ProjectID,
		&item.Status, &item.Sensitivity, &item.MemoryType, &item.SourceType, &item.SourceMemberID, &item.CreatedByMemberID,
		&item.Content, (*vectorScanTarget)(&item.Embedding), &item.Version,
	)
	if errors.Is(err, sql.ErrNoRows) {
		return store.MemoryItem{}, store.ErrNotFound
	}
	return item, err
}

func (s *Store) CreateObservation(ctx context.Context, payload map[string]any) (store.Observation, error) {
	observationPayload, _ := payload["observation"].(map[string]any)
	if observationPayload == nil {
		observationPayload = map[string]any{}
	}
	rawObservation, err := json.Marshal(observationPayload)
	if err != nil {
		return store.Observation{}, err
	}
	observation := store.Observation{
		ID:        randomID("obs"),
		OrgID:     stringValue(payload, "org_id"),
		SessionID: stringValue(payload, "session_id"),
		MemberID:  stringValue(payload, "member_id"),
		TeamID:    stringValue(payload, "team_id"),
		ProjectID: stringValue(payload, "project_id"),
		Status:    "pending",
		Payload:   observationPayload,
	}
	_, err = s.db.ExecContext(ctx, `
insert into tcg_memory_observations(
  id, org_id, session_id, member_id, team_id, project_id, observation, status
)
values ($1, $2, $3, $4, $5, $6, $7::jsonb, $8)
`, observation.ID, observation.OrgID, observation.SessionID, observation.MemberID, observation.TeamID, observation.ProjectID, string(rawObservation), observation.Status)
	if err != nil {
		return store.Observation{}, err
	}
	return observation, nil
}

func (s *Store) Prefetch(ctx context.Context, req store.PrefetchRequest) ([]store.MemoryPartition, error) {
	partitions := []store.MemoryPartition{}
	if len(req.QueryEmbedding) > 0 {
		if err := validatePostgresEmbedding(req.QueryEmbedding); err != nil {
			return nil, err
		}
		items, err := s.vectorActiveMemories(ctx, req.OrgID, "team_shared", "", req.TeamID, req.ProjectID, req.QueryEmbedding, req.Limit)
		if err != nil {
			return nil, err
		}
		if len(items) > 0 {
			partitions = append(partitions, store.MemoryPartition{Scope: "team_shared", Items: items})
		}
		return partitions, nil
	}

	items, err := s.activeMemories(ctx, req.OrgID, "team_shared", "", req.TeamID)
	if err != nil {
		return nil, err
	}
	items = store.RankPrefetchItems(items, req.Query, req.ProjectID, req.QueryEmbedding, req.Limit)
	if len(items) > 0 {
		partitions = append(partitions, store.MemoryPartition{Scope: "team_shared", Items: items})
	}
	return partitions, nil
}

func (s *Store) ListReviews(ctx context.Context, orgID, status, reviewKind string, limit int) ([]store.ReviewItem, error) {
	if limit <= 0 {
		limit = 100
	}
	rows, err := s.db.QueryContext(ctx, `
select id, org_id, memory_id, status, review_kind, submitted_by_member_id
from tcg_memory_review_items
where org_id = $1
  and ($2 = '' or status = $2)
  and ($3 = '' or review_kind = $3)
order by id
limit $4
`, orgID, status, reviewKind, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	out := []store.ReviewItem{}
	for rows.Next() {
		var item store.ReviewItem
		if err := rows.Scan(&item.ID, &item.OrgID, &item.MemoryID, &item.Status, &item.ReviewKind, &item.SubmittedByMemberID); err != nil {
			return nil, err
		}
		out = append(out, item)
	}
	return out, rows.Err()
}

func (s *Store) GetReview(ctx context.Context, reviewID string) (store.ReviewItem, error) {
	var item store.ReviewItem
	err := s.db.QueryRowContext(ctx, `
select id, org_id, memory_id, status, review_kind, submitted_by_member_id
from tcg_memory_review_items
where id = $1
`, reviewID).Scan(&item.ID, &item.OrgID, &item.MemoryID, &item.Status, &item.ReviewKind, &item.SubmittedByMemberID)
	if errors.Is(err, sql.ErrNoRows) {
		return store.ReviewItem{}, store.ErrNotFound
	}
	return item, err
}

func (s *Store) ApproveReview(ctx context.Context, reviewID, actorMemberID string, edits map[string]any) (store.ReviewDecision, error) {
	return s.reviewDecision(ctx, reviewID, actorMemberID, "approved", "active", stringValue(edits, "content"), "")
}

func (s *Store) RejectReview(ctx context.Context, reviewID, actorMemberID, reason string) (store.ReviewDecision, error) {
	return s.reviewDecision(ctx, reviewID, actorMemberID, "rejected", "rejected", "", reason)
}

func (s *Store) GetBackupPolicy(ctx context.Context, orgID, memberID string) (store.BackupPolicy, error) {
	var policy store.BackupPolicy
	var lastRunAt, nextRunAt sql.NullTime
	err := s.db.QueryRowContext(ctx, `
select org_id, member_id, cadence, enabled, retention_count, last_run_at, next_run_at
from tcg_backup_policies
where org_id = $1 and member_id = $2
`, orgID, memberID).Scan(&policy.OrgID, &policy.MemberID, &policy.Cadence, &policy.Enabled, &policy.RetentionCount, &lastRunAt, &nextRunAt)
	if errors.Is(err, sql.ErrNoRows) {
		return store.BackupPolicy{OrgID: orgID, MemberID: memberID, Cadence: "weekly", Enabled: false, RetentionCount: 4}, nil
	}
	policy.LastRunAt = nullTimeString(lastRunAt)
	policy.NextRunAt = nullTimeString(nextRunAt)
	return policy, err
}

func (s *Store) UpsertBackupPolicy(ctx context.Context, policy store.BackupPolicy) (store.BackupPolicy, error) {
	if policy.Cadence == "" {
		policy.Cadence = "weekly"
	}
	if policy.RetentionCount == 0 {
		policy.RetentionCount = 4
	}
	_, err := s.db.ExecContext(ctx, `
insert into tcg_backup_policies(org_id, member_id, cadence, enabled, retention_count)
values ($1, $2, $3, $4, $5)
on conflict (org_id, member_id) do update set
  cadence = excluded.cadence,
  enabled = excluded.enabled,
  retention_count = excluded.retention_count,
  updated_at = now()
`, policy.OrgID, policy.MemberID, policy.Cadence, policy.Enabled, policy.RetentionCount)
	if err != nil {
		return store.BackupPolicy{}, err
	}
	return policy, nil
}

func (s *Store) ListBackupPolicies(ctx context.Context, enabledOnly bool) ([]store.BackupPolicy, error) {
	rows, err := s.db.QueryContext(ctx, `
select org_id, member_id, cadence, enabled, retention_count, last_run_at, next_run_at
from tcg_backup_policies
where ($1 = false or enabled = true)
order by org_id, member_id
`, enabledOnly)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := []store.BackupPolicy{}
	for rows.Next() {
		var policy store.BackupPolicy
		var lastRunAt, nextRunAt sql.NullTime
		if err := rows.Scan(&policy.OrgID, &policy.MemberID, &policy.Cadence, &policy.Enabled, &policy.RetentionCount, &lastRunAt, &nextRunAt); err != nil {
			return nil, err
		}
		policy.LastRunAt = nullTimeString(lastRunAt)
		policy.NextRunAt = nullTimeString(nextRunAt)
		out = append(out, policy)
	}
	return out, rows.Err()
}

func (s *Store) MarkBackupPolicyRun(ctx context.Context, orgID, memberID, lastRunAt, nextRunAt string) error {
	_, err := s.db.ExecContext(ctx, `
update tcg_backup_policies
set last_run_at = nullif($3, '')::timestamptz,
    next_run_at = nullif($4, '')::timestamptz,
    updated_at = now()
where org_id = $1 and member_id = $2
`, orgID, memberID, lastRunAt, nextRunAt)
	return err
}

func (s *Store) GetTeamBackupPolicy(ctx context.Context, orgID string) (store.BackupPolicy, error) {
	return s.GetBackupPolicy(ctx, orgID, store.TeamBackupMemberID)
}

func (s *Store) UpsertTeamBackupPolicy(ctx context.Context, policy store.BackupPolicy) (store.BackupPolicy, error) {
	policy.MemberID = store.TeamBackupMemberID
	return s.UpsertBackupPolicy(ctx, policy)
}

func (s *Store) GetTeamSoulBackupPolicy(ctx context.Context, orgID string) (store.BackupPolicy, error) {
	return s.GetBackupPolicy(ctx, orgID, store.TeamSoulBackupMemberID)
}

func (s *Store) UpsertTeamSoulBackupPolicy(ctx context.Context, policy store.BackupPolicy) (store.BackupPolicy, error) {
	policy.MemberID = store.TeamSoulBackupMemberID
	return s.UpsertBackupPolicy(ctx, policy)
}

func (s *Store) AppendAuditEvent(ctx context.Context, event store.AuditEvent) (store.AuditEvent, error) {
	if event.ID == "" {
		event.ID = randomID("audit")
	}
	if event.Decision == "" {
		event.Decision = "allowed"
	}
	if event.Metadata == nil {
		event.Metadata = map[string]any{}
	}
	rawMetadata, err := json.Marshal(event.Metadata)
	if err != nil {
		return store.AuditEvent{}, err
	}
	_, err = s.db.ExecContext(ctx, `
insert into tcg_audit_events(id, org_id, actor_id, action, resource, decision, metadata)
values ($1, $2, $3, $4, $5, $6, $7::jsonb)
`, event.ID, event.OrgID, event.ActorID, event.Action, event.Resource, event.Decision, string(rawMetadata))
	return event, err
}

func (s *Store) ListAuditEvents(ctx context.Context, orgID string, limit int) ([]store.AuditEvent, error) {
	if limit <= 0 {
		limit = 100
	}
	rows, err := s.db.QueryContext(ctx, `
select id, org_id, actor_id, action, resource, decision, metadata
from tcg_audit_events
where ($1 = '' or org_id = $1)
order by created_at desc
limit $2
`, orgID, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := []store.AuditEvent{}
	for rows.Next() {
		var event store.AuditEvent
		var rawMetadata []byte
		if err := rows.Scan(&event.ID, &event.OrgID, &event.ActorID, &event.Action, &event.Resource, &event.Decision, &rawMetadata); err != nil {
			return nil, err
		}
		_ = json.Unmarshal(rawMetadata, &event.Metadata)
		out = append(out, event)
	}
	return out, rows.Err()
}

func (s *Store) WriteRelationship(ctx context.Context, relationship store.Relationship) (store.Relationship, error) {
	if relationship.OrgID == "" || relationship.ResourceType == "" || relationship.ResourceID == "" || relationship.SubjectID == "" {
		return store.Relationship{}, fmt.Errorf("org_id, resource, and subject are required")
	}
	if relationship.Relation == "" {
		relationship.Relation = "member"
	}
	if relationship.SubjectType == "" {
		relationship.SubjectType = "member"
	}
	if relationship.IdempotencyKey == "" {
		relationship.IdempotencyKey = relationshipKey(relationship)
	}
	_, err := s.db.ExecContext(ctx, `
insert into tcg_relationships(idempotency_key, org_id, resource_type, resource_id, relation, subject_type, subject_id)
values ($1, $2, $3, $4, $5, $6, $7)
on conflict (idempotency_key) do update set
  org_id = excluded.org_id,
  resource_type = excluded.resource_type,
  resource_id = excluded.resource_id,
  relation = excluded.relation,
  subject_type = excluded.subject_type,
  subject_id = excluded.subject_id
`, relationship.IdempotencyKey, relationship.OrgID, relationship.ResourceType, relationship.ResourceID, relationship.Relation, relationship.SubjectType, relationship.SubjectID)
	return relationship, err
}

func (s *Store) CheckPermission(ctx context.Context, check store.PermissionCheck) (store.PermissionDecision, error) {
	rows, err := s.db.QueryContext(ctx, `
select relation from tcg_relationships
where org_id = $1
  and resource_type = $2
  and resource_id = $3
  and subject_type = $4
  and subject_id = $5
`, check.OrgID, check.ResourceType, check.ResourceID, check.SubjectType, check.SubjectID)
	if err != nil {
		return store.PermissionDecision{}, err
	}
	defer rows.Close()
	for rows.Next() {
		var relation string
		if err := rows.Scan(&relation); err != nil {
			return store.PermissionDecision{}, err
		}
		if relationAllows(relation, check.Permission) {
			path := fmt.Sprintf("%s:%s#%s@%s:%s", check.ResourceType, check.ResourceID, relation, check.SubjectType, check.SubjectID)
			return store.PermissionDecision{Allowed: true, Reason: "relationship_allowed", Path: []string{path}}, nil
		}
	}
	if err := rows.Err(); err != nil {
		return store.PermissionDecision{}, err
	}
	return store.PermissionDecision{Allowed: false, Reason: "no_matching_relationship"}, nil
}

func (s *Store) RunTeamMemoryBackup(ctx context.Context, orgID string) (store.BackupJob, error) {
	items, err := s.activeMemories(ctx, orgID, "team_shared", "", "")
	if err != nil {
		return store.BackupJob{}, err
	}
	rawItems, err := json.Marshal(items)
	if err != nil {
		return store.BackupJob{}, err
	}
	sum := sha256.Sum256(rawItems)
	job := store.BackupJob{
		ID:             randomID("backup"),
		OrgID:          orgID,
		MemberID:       store.TeamBackupMemberID,
		Status:         "completed",
		ObjectKey:      fmt.Sprintf("org/%s/team-memory/%s.jsonl.enc", orgID, time.Now().UTC().Format("20060102150405")),
		ObjectUploaded: false,
		ChecksumSHA256: hex.EncodeToString(sum[:]),
		ItemCount:      len(items),
		Manifest: map[string]any{
			"object_store": "database",
			"format":       "json",
			"backup_scope": "team_memory",
		},
		Items:     items,
		CreatedAt: time.Now().UTC(),
	}
	rawManifest, err := json.Marshal(job.Manifest)
	if err != nil {
		return store.BackupJob{}, err
	}
	_, err = s.db.ExecContext(ctx, `
insert into tcg_backup_jobs(id, org_id, member_id, status, object_key, object_uploaded, checksum_sha256, item_count, manifest, items)
values ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb, $10::jsonb)
`, job.ID, job.OrgID, job.MemberID, job.Status, job.ObjectKey, job.ObjectUploaded, job.ChecksumSHA256, job.ItemCount, string(rawManifest), string(rawItems))
	return job, err
}

func (s *Store) RunTeamSoulBackup(ctx context.Context, orgID, teamID string) (store.BackupJob, error) {
	if strings.TrimSpace(teamID) == "" {
		teamID = orgID
	}
	soul, err := s.GetTeamSoul(ctx, orgID, teamID)
	if err != nil {
		return store.BackupJob{}, err
	}
	manifest := map[string]any{
		"object_store": "database",
		"format":       "json",
		"backup_scope": "team_soul",
		"team_soul":    store.TeamSoulBackupManifest(soul),
	}
	rawManifest, err := json.Marshal(manifest)
	if err != nil {
		return store.BackupJob{}, err
	}
	sum := sha256.Sum256(rawManifest)
	rawItems, err := json.Marshal([]store.MemoryItem{})
	if err != nil {
		return store.BackupJob{}, err
	}
	job := store.BackupJob{
		ID:             randomID("backup"),
		OrgID:          orgID,
		MemberID:       store.TeamSoulBackupMemberID,
		Status:         "completed",
		ObjectKey:      fmt.Sprintf("org/%s/team-soul/%s.json.enc", orgID, time.Now().UTC().Format("20060102150405")),
		ObjectUploaded: false,
		ChecksumSHA256: hex.EncodeToString(sum[:]),
		ItemCount:      1,
		Manifest:       manifest,
		CreatedAt:      time.Now().UTC(),
	}
	_, err = s.db.ExecContext(ctx, `
insert into tcg_backup_jobs(id, org_id, member_id, status, object_key, object_uploaded, checksum_sha256, item_count, manifest, items)
values ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb, $10::jsonb)
`, job.ID, job.OrgID, job.MemberID, job.Status, job.ObjectKey, job.ObjectUploaded, job.ChecksumSHA256, job.ItemCount, string(rawManifest), string(rawItems))
	return job, err
}

func (s *Store) ListBackupJobs(ctx context.Context, orgID, memberID string, limit int) ([]store.BackupJob, error) {
	if limit <= 0 {
		limit = 100
	}
	rows, err := s.db.QueryContext(ctx, `
select id, org_id, member_id, status, object_key, object_uploaded, checksum_sha256, item_count, manifest, created_at
from tcg_backup_jobs
where org_id = $1 and member_id = $2 and status <> 'pruned'
order by created_at desc, id desc
limit $3
`, orgID, memberID, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := []store.BackupJob{}
	for rows.Next() {
		var job store.BackupJob
		var rawManifest []byte
		if err := rows.Scan(&job.ID, &job.OrgID, &job.MemberID, &job.Status, &job.ObjectKey, &job.ObjectUploaded, &job.ChecksumSHA256, &job.ItemCount, &rawManifest, &job.CreatedAt); err != nil {
			return nil, err
		}
		_ = json.Unmarshal(rawManifest, &job.Manifest)
		out = append(out, job)
	}
	return out, rows.Err()
}

func (s *Store) GetBackupJob(ctx context.Context, backupID string) (store.BackupJob, error) {
	var job store.BackupJob
	var rawItems []byte
	var rawManifest []byte
	var createdAt time.Time
	err := s.db.QueryRowContext(ctx, `
select id, org_id, member_id, status, object_key, object_uploaded, checksum_sha256, item_count, manifest, items, created_at
from tcg_backup_jobs
where id = $1
`, backupID).Scan(&job.ID, &job.OrgID, &job.MemberID, &job.Status, &job.ObjectKey, &job.ObjectUploaded, &job.ChecksumSHA256, &job.ItemCount, &rawManifest, &rawItems, &createdAt)
	if errors.Is(err, sql.ErrNoRows) {
		return store.BackupJob{}, store.ErrNotFound
	}
	if err != nil {
		return store.BackupJob{}, err
	}
	_ = json.Unmarshal(rawManifest, &job.Manifest)
	_ = json.Unmarshal(rawItems, &job.Items)
	job.CreatedAt = createdAt
	return job, nil
}

func (s *Store) UpdateBackupObject(ctx context.Context, backupID, checksumSHA256 string, manifest map[string]any) (store.BackupJob, error) {
	rawManifest, err := json.Marshal(manifest)
	if err != nil {
		return store.BackupJob{}, err
	}
	_, err = s.db.ExecContext(ctx, `
update tcg_backup_jobs
set object_uploaded = true,
    checksum_sha256 = $2,
    manifest = $3::jsonb
where id = $1
`, backupID, checksumSHA256, string(rawManifest))
	if err != nil {
		return store.BackupJob{}, err
	}
	return s.GetBackupJob(ctx, backupID)
}

func (s *Store) UpdateBackupItems(ctx context.Context, backupID string, items []store.MemoryItem) (store.BackupJob, error) {
	rawItems, err := json.Marshal(items)
	if err != nil {
		return store.BackupJob{}, err
	}
	_, err = s.db.ExecContext(ctx, `
update tcg_backup_jobs
set items = $2::jsonb,
    item_count = $3
where id = $1
`, backupID, string(rawItems), len(items))
	if err != nil {
		return store.BackupJob{}, err
	}
	return s.GetBackupJob(ctx, backupID)
}

func (s *Store) PruneBackupJobs(ctx context.Context, orgID, memberID string, keep int) (int, error) {
	if keep <= 0 {
		return 0, nil
	}
	result, err := s.db.ExecContext(ctx, `
with ranked as (
  select id,
         row_number() over (order by created_at desc, id desc) as rn
  from tcg_backup_jobs
  where org_id = $1 and member_id = $2 and status <> 'pruned'
)
update tcg_backup_jobs
set status = 'pruned',
    items = '[]'::jsonb
where id in (select id from ranked where rn > $3)
`, orgID, memberID, keep)
	if err != nil {
		return 0, err
	}
	rows, _ := result.RowsAffected()
	return int(rows), nil
}

func (s *Store) PreviewTeamMemoryRestore(ctx context.Context, backupID, mode string) (store.RestorePreview, error) {
	job, err := s.GetBackupJob(ctx, backupID)
	if err != nil {
		return store.RestorePreview{}, err
	}
	mode = normalizeRestoreMode(mode)
	if err := validateRestoreMode(mode); err != nil {
		return store.RestorePreview{}, err
	}
	createCount := 0
	skipCount := 0
	for _, item := range job.Items {
		if item.Scope != "team_shared" || item.OrgID != job.OrgID {
			continue
		}
		var exists bool
		err = s.db.QueryRowContext(ctx, `select exists(select 1 from tcg_memory_items where id = $1)`, item.ID).Scan(&exists)
		if err != nil {
			return store.RestorePreview{}, err
		}
		if exists {
			skipCount++
		} else {
			createCount++
		}
	}
	preview := store.RestorePreview{BackupID: backupID, MemberID: store.TeamBackupMemberID, CreateCount: createCount, SkipCount: skipCount, Mode: mode}
	_, err = s.db.ExecContext(ctx, `
insert into tcg_restore_previews(backup_id, member_id, mode, create_count, skip_count)
values ($1, $2, $3, $4, $5)
on conflict (backup_id, member_id, mode) do update set
  create_count = excluded.create_count,
  skip_count = excluded.skip_count,
  created_at = now()
`, preview.BackupID, preview.MemberID, preview.Mode, preview.CreateCount, preview.SkipCount)
	if err != nil {
		return store.RestorePreview{}, err
	}
	return preview, nil
}

func (s *Store) ExecuteTeamMemoryRestore(ctx context.Context, backupID, mode string) (store.RestoreExecution, error) {
	job, err := s.GetBackupJob(ctx, backupID)
	if err != nil {
		return store.RestoreExecution{}, err
	}
	mode = normalizeRestoreMode(mode)
	if err := validateRestoreMode(mode); err != nil {
		return store.RestoreExecution{}, err
	}
	var previewExists bool
	err = s.db.QueryRowContext(ctx, `
select exists(
  select 1 from tcg_restore_previews
  where backup_id = $1 and member_id = $2 and mode = $3
)
`, backupID, store.TeamBackupMemberID, mode).Scan(&previewExists)
	if err != nil {
		return store.RestoreExecution{}, err
	}
	if !previewExists {
		return store.RestoreExecution{}, fmt.Errorf("restore_preview_required")
	}
	switch mode {
	case "overwrite":
		if err := s.markTeamMemories(ctx, job.OrgID, "deleted"); err != nil {
			return store.RestoreExecution{}, err
		}
	case "archive_current_then_restore":
		if err := s.markTeamMemories(ctx, job.OrgID, "archived"); err != nil {
			return store.RestoreExecution{}, err
		}
	}
	restored := 0
	for _, item := range job.Items {
		if item.Scope != "team_shared" || item.OrgID != job.OrgID || item.ID == "" {
			continue
		}
		item.Status = "active"
		if item.Version <= 0 {
			item.Version = 1
		}
		_, err = s.db.ExecContext(ctx, `
insert into tcg_memory_items(
  id, org_id, scope, subject_member_id, team_id, project_id,
  status, sensitivity, memory_type, source_type, source_member_id, created_by_member_id,
  content, embedding, version
)
values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, nullif($14, '')::vector, $15)
on conflict (id) do update set
  org_id = excluded.org_id,
  scope = excluded.scope,
  subject_member_id = excluded.subject_member_id,
  team_id = excluded.team_id,
  project_id = excluded.project_id,
  status = excluded.status,
  sensitivity = excluded.sensitivity,
  memory_type = excluded.memory_type,
  source_type = excluded.source_type,
  source_member_id = excluded.source_member_id,
  created_by_member_id = excluded.created_by_member_id,
  content = excluded.content,
  embedding = excluded.embedding,
  version = tcg_memory_items.version + 1,
  updated_at = now()
`, item.ID, item.OrgID, item.Scope, item.SubjectMemberID, item.TeamID, item.ProjectID, item.Status, item.Sensitivity, item.MemoryType, item.SourceType, item.SourceMemberID, item.CreatedByMemberID, item.Content, store.VectorLiteral(item.Embedding), item.Version)
		if err != nil {
			return store.RestoreExecution{}, err
		}
		restored++
	}
	return store.RestoreExecution{BackupID: backupID, MemberID: store.TeamBackupMemberID, Mode: mode, RestoredCount: restored, Status: "executed"}, nil
}

func (s *Store) PreviewTeamSoulRestore(ctx context.Context, backupID, mode string) (store.RestorePreview, error) {
	job, err := s.GetBackupJob(ctx, backupID)
	if err != nil {
		return store.RestorePreview{}, err
	}
	if job.MemberID != store.TeamSoulBackupMemberID {
		return store.RestorePreview{}, fmt.Errorf("unsupported_backup_scope")
	}
	mode = normalizeRestoreMode(mode)
	if err := validateRestoreMode(mode); err != nil {
		return store.RestorePreview{}, err
	}
	soul, err := store.TeamSoulFromBackupManifest(job.Manifest)
	if err != nil {
		return store.RestorePreview{}, err
	}
	var existsWithChecksum bool
	err = s.db.QueryRowContext(ctx, `
select exists(
  select 1 from tcg_team_souls
  where org_id = $1 and team_id = $2 and checksum_sha256 = $3
)
`, soul.OrgID, soul.TeamID, soul.ChecksumSHA256).Scan(&existsWithChecksum)
	if err != nil {
		return store.RestorePreview{}, err
	}
	createCount := 1
	skipCount := 0
	if existsWithChecksum {
		createCount = 0
		skipCount = 1
	}
	preview := store.RestorePreview{BackupID: backupID, MemberID: store.TeamSoulBackupMemberID, CreateCount: createCount, SkipCount: skipCount, Mode: mode}
	_, err = s.db.ExecContext(ctx, `
insert into tcg_restore_previews(backup_id, member_id, mode, create_count, skip_count)
values ($1, $2, $3, $4, $5)
on conflict (backup_id, member_id, mode) do update set
  create_count = excluded.create_count,
  skip_count = excluded.skip_count,
  created_at = now()
`, preview.BackupID, preview.MemberID, preview.Mode, preview.CreateCount, preview.SkipCount)
	if err != nil {
		return store.RestorePreview{}, err
	}
	return preview, nil
}

func (s *Store) ExecuteTeamSoulRestore(ctx context.Context, backupID, mode string) (store.RestoreExecution, error) {
	job, err := s.GetBackupJob(ctx, backupID)
	if err != nil {
		return store.RestoreExecution{}, err
	}
	if job.MemberID != store.TeamSoulBackupMemberID {
		return store.RestoreExecution{}, fmt.Errorf("unsupported_backup_scope")
	}
	mode = normalizeRestoreMode(mode)
	if err := validateRestoreMode(mode); err != nil {
		return store.RestoreExecution{}, err
	}
	var previewExists bool
	err = s.db.QueryRowContext(ctx, `
select exists(
  select 1 from tcg_restore_previews
  where backup_id = $1 and member_id = $2 and mode = $3
)
`, backupID, store.TeamSoulBackupMemberID, mode).Scan(&previewExists)
	if err != nil {
		return store.RestoreExecution{}, err
	}
	if !previewExists {
		return store.RestoreExecution{}, fmt.Errorf("restore_preview_required")
	}
	soul, err := store.TeamSoulFromBackupManifest(job.Manifest)
	if err != nil {
		return store.RestoreExecution{}, err
	}
	if soul.UpdatedBy == "" {
		soul.UpdatedBy = "restore:" + backupID
	}
	_, err = s.UpsertTeamSoul(ctx, soul)
	if err != nil {
		return store.RestoreExecution{}, err
	}
	return store.RestoreExecution{BackupID: backupID, MemberID: store.TeamSoulBackupMemberID, Mode: mode, RestoredCount: 1, Status: "executed"}, nil
}

func (s *Store) CreateOrgExport(ctx context.Context, orgID string) (store.OrgExport, error) {
	var sharedCount int
	err := s.db.QueryRowContext(ctx, `
select count(*) from tcg_memory_items
where org_id = $1 and scope = 'team_shared' and status = 'active'
`, orgID).Scan(&sharedCount)
	if err != nil {
		return store.OrgExport{}, err
	}
	exported := store.OrgExport{
		ID:              randomID("export"),
		OrgID:           orgID,
		Status:          "completed",
		TeamSharedCount: sharedCount,
		PersonalCount:   0,
		Manifest: map[string]any{
			"contains_personal_memory": false,
			"team_shared_count":        sharedCount,
		},
	}
	rawManifest, err := json.Marshal(exported.Manifest)
	if err != nil {
		return store.OrgExport{}, err
	}
	_, err = s.db.ExecContext(ctx, `
insert into tcg_org_exports(id, org_id, status, team_shared_count, personal_count, manifest)
values ($1, $2, $3, $4, $5, $6::jsonb)
`, exported.ID, exported.OrgID, exported.Status, exported.TeamSharedCount, exported.PersonalCount, string(rawManifest))
	return exported, err
}

func (s *Store) CreateDeletionRequest(ctx context.Context, req store.DeletionRequest) (store.DeletionRequest, error) {
	if req.OrgID == "" || req.TargetMemberID == "" || req.DeletionScope == "" {
		return store.DeletionRequest{}, fmt.Errorf("org_id, target_member_id, and deletion_scope are required")
	}
	scope, err := store.NormalizeDeletionScope(req.DeletionScope)
	if err != nil {
		return store.DeletionRequest{}, err
	}
	req.DeletionScope = scope
	req.ID = randomID("deletion")
	req.Status = "pending"
	_, err = s.db.ExecContext(ctx, `
insert into tcg_deletion_requests(id, org_id, target_member_id, requested_by, deletion_scope, reason, status)
values ($1, $2, $3, $4, $5, $6, $7)
`, req.ID, req.OrgID, req.TargetMemberID, req.RequestedBy, req.DeletionScope, req.Reason, req.Status)
	return req, err
}

func (s *Store) GetDeletionRequest(ctx context.Context, requestID string) (store.DeletionRequest, error) {
	var req store.DeletionRequest
	err := s.db.QueryRowContext(ctx, `
select id, org_id, target_member_id, requested_by, deletion_scope, reason, status
from tcg_deletion_requests
where id = $1
`, requestID).Scan(&req.ID, &req.OrgID, &req.TargetMemberID, &req.RequestedBy, &req.DeletionScope, &req.Reason, &req.Status)
	if errors.Is(err, sql.ErrNoRows) {
		return store.DeletionRequest{}, store.ErrNotFound
	}
	return req, err
}

func (s *Store) ExecuteDeletionRequest(ctx context.Context, requestID, actorMemberID string) (store.DeletionRequest, error) {
	var req store.DeletionRequest
	err := s.db.QueryRowContext(ctx, `
select id, org_id, target_member_id, requested_by, deletion_scope, reason, status
from tcg_deletion_requests
where id = $1
`, requestID).Scan(&req.ID, &req.OrgID, &req.TargetMemberID, &req.RequestedBy, &req.DeletionScope, &req.Reason, &req.Status)
	if errors.Is(err, sql.ErrNoRows) {
		return store.DeletionRequest{}, store.ErrNotFound
	}
	if err != nil {
		return store.DeletionRequest{}, err
	}
	if _, err := store.NormalizeDeletionScope(req.DeletionScope); err != nil {
		return store.DeletionRequest{}, err
	}
	req.Status = "executed"
	_, err = s.db.ExecContext(ctx, `
update tcg_deletion_requests set status = 'executed', executed_at = now() where id = $1
`, req.ID)
	return req, err
}

func (s *Store) UpsertToolPolicyRule(ctx context.Context, rule store.ToolPolicyRule) (store.ToolPolicyRule, error) {
	if rule.OrgID == "" || rule.ToolName == "" || rule.Decision == "" {
		return store.ToolPolicyRule{}, fmt.Errorf("org_id, tool_name, and decision are required")
	}
	if rule.RiskLevel == "" {
		rule.RiskLevel = "*"
	}
	_, err := s.db.ExecContext(ctx, `
insert into tcg_tool_policy_rules(org_id, tool_name, risk_level, decision, updated_by)
values ($1, $2, $3, $4, $5)
on conflict (org_id, tool_name, risk_level) do update set
  decision = excluded.decision,
  updated_by = excluded.updated_by,
  updated_at = now()
`, rule.OrgID, rule.ToolName, rule.RiskLevel, rule.Decision, rule.UpdatedBy)
	return rule, err
}

func (s *Store) EvaluateToolPolicy(ctx context.Context, req store.ToolPolicyRequest) (store.ToolPolicyDecision, error) {
	rule, ok, err := s.findToolPolicyRule(ctx, req.OrgID, req.ToolName, req.RiskLevel)
	if err != nil {
		return store.ToolPolicyDecision{}, err
	}
	if ok {
		return store.ToolPolicyDecision{Decision: rule.Decision, Reason: "explicit_rule", EffectiveRule: req.OrgID + ":" + req.ToolName + ":" + rule.RiskLevel}, nil
	}
	switch req.RiskLevel {
	case "safe", "low":
		return store.ToolPolicyDecision{Decision: "allowed", Reason: "default_low_risk"}, nil
	case "destructive", "critical", "high":
		return store.ToolPolicyDecision{Decision: "approval_required", Reason: "high_risk_default", ApprovalID: randomID("approval")}, nil
	default:
		return store.ToolPolicyDecision{Decision: "denied", Reason: "unknown_risk_level"}, nil
	}
}

func (s *Store) CreateCloudSession(ctx context.Context, session store.CloudSession) (store.CloudSession, error) {
	if session.ID == "" {
		session.ID = randomID("session")
	}
	if session.Status == "" {
		session.Status = "active"
	}
	_, err := s.db.ExecContext(ctx, `
insert into tcg_cloud_sessions(id, org_id, team_id, project_id, owner_member_id, title, status)
values ($1, $2, $3, $4, $5, $6, $7)
`, session.ID, session.OrgID, session.TeamID, session.ProjectID, session.OwnerMemberID, session.Title, session.Status)
	return session, err
}

func (s *Store) GetCloudSession(ctx context.Context, sessionID string) (store.CloudSession, error) {
	var session store.CloudSession
	err := s.db.QueryRowContext(ctx, `
select id, org_id, team_id, project_id, owner_member_id, title, status
from tcg_cloud_sessions
where id = $1
`, sessionID).Scan(&session.ID, &session.OrgID, &session.TeamID, &session.ProjectID, &session.OwnerMemberID, &session.Title, &session.Status)
	if errors.Is(err, sql.ErrNoRows) {
		return store.CloudSession{}, store.ErrNotFound
	}
	return session, err
}

func (s *Store) AppendRuntimeEvent(ctx context.Context, event store.RuntimeEvent) (store.RuntimeEvent, error) {
	if event.ID == "" {
		event.ID = randomID("event")
	}
	if event.CreatedAt.IsZero() {
		event.CreatedAt = time.Now().UTC()
	}
	if event.Payload == nil {
		event.Payload = map[string]any{}
	}
	rawPayload, err := json.Marshal(event.Payload)
	if err != nil {
		return store.RuntimeEvent{}, err
	}
	_, err = s.db.ExecContext(ctx, `
insert into tcg_runtime_events(id, org_id, session_id, event_type, payload, created_at)
values ($1, $2, $3, $4, $5::jsonb, $6)
`, event.ID, event.OrgID, event.SessionID, event.EventType, string(rawPayload), event.CreatedAt)
	return event, err
}

func (s *Store) GetTeamSoul(ctx context.Context, orgID, teamID string) (store.TeamSoul, error) {
	var soul store.TeamSoul
	var updatedAt time.Time
	err := s.db.QueryRowContext(ctx, `
select org_id, team_id, content, version, checksum_sha256, updated_by, updated_at
from tcg_team_souls
where org_id = $1 and team_id = $2
`, orgID, teamID).Scan(&soul.OrgID, &soul.TeamID, &soul.Content, &soul.Version, &soul.ChecksumSHA256, &soul.UpdatedBy, &updatedAt)
	if errors.Is(err, sql.ErrNoRows) {
		return store.TeamSoul{}, store.ErrNotFound
	}
	if err != nil {
		return store.TeamSoul{}, err
	}
	soul.UpdatedAt = updatedAt.UTC().Format(time.RFC3339)
	return soul, nil
}

func (s *Store) UpsertTeamSoul(ctx context.Context, soul store.TeamSoul) (store.TeamSoul, error) {
	if strings.TrimSpace(soul.OrgID) == "" || strings.TrimSpace(soul.TeamID) == "" || strings.TrimSpace(soul.Content) == "" {
		return store.TeamSoul{}, fmt.Errorf("org_id, team_id and content are required")
	}
	sum := sha256.Sum256([]byte(soul.Content))
	soul.ChecksumSHA256 = hex.EncodeToString(sum[:])
	var updatedAt time.Time
	err := s.db.QueryRowContext(ctx, `
insert into tcg_team_souls(org_id, team_id, content, version, checksum_sha256, updated_by)
values ($1, $2, $3, 1, $4, $5)
on conflict (org_id, team_id) do update set
  content = excluded.content,
  version = tcg_team_souls.version + 1,
  checksum_sha256 = excluded.checksum_sha256,
  updated_by = excluded.updated_by,
  updated_at = now()
returning org_id, team_id, content, version, checksum_sha256, updated_by, updated_at
`, soul.OrgID, soul.TeamID, soul.Content, soul.ChecksumSHA256, soul.UpdatedBy).Scan(&soul.OrgID, &soul.TeamID, &soul.Content, &soul.Version, &soul.ChecksumSHA256, &soul.UpdatedBy, &updatedAt)
	if err != nil {
		return store.TeamSoul{}, err
	}
	soul.UpdatedAt = updatedAt.UTC().Format(time.RFC3339)
	return soul, nil
}

func (s *Store) organizationExists(ctx context.Context, orgID string) (bool, error) {
	var exists bool
	err := s.db.QueryRowContext(ctx, `select exists(select 1 from tcg_organizations where id = $1)`, orgID).Scan(&exists)
	return exists, err
}

func (s *Store) getMemory(ctx context.Context, memoryID string) (store.MemoryItem, error) {
	var item store.MemoryItem
	err := s.db.QueryRowContext(ctx, `
select id, org_id, scope, subject_member_id, team_id, project_id,
       status, sensitivity, memory_type, source_type, source_member_id, created_by_member_id,
       content, coalesce(embedding::text, ''), version
from tcg_memory_items
where id = $1
`, memoryID).Scan(
		&item.ID, &item.OrgID, &item.Scope, &item.SubjectMemberID, &item.TeamID, &item.ProjectID,
		&item.Status, &item.Sensitivity, &item.MemoryType, &item.SourceType, &item.SourceMemberID, &item.CreatedByMemberID,
		&item.Content, (*vectorScanTarget)(&item.Embedding), &item.Version,
	)
	if errors.Is(err, sql.ErrNoRows) {
		return store.MemoryItem{}, store.ErrNotFound
	}
	return item, err
}

func (s *Store) activeMemories(ctx context.Context, orgID, scope, subjectMemberID, teamID string) ([]store.MemoryItem, error) {
	rows, err := s.db.QueryContext(ctx, `
select id, org_id, scope, subject_member_id, team_id, project_id,
       status, sensitivity, memory_type, source_type, source_member_id, created_by_member_id,
       content, coalesce(embedding::text, ''), version
from tcg_memory_items
where org_id = $1
  and scope = $2
  and status = 'active'
  and ($3 = '' or subject_member_id = $3)
  and ($4 = '' or team_id = $4)
order by id
`, orgID, scope, subjectMemberID, teamID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	return scanMemoryRows(rows)
}

func (s *Store) vectorActiveMemories(ctx context.Context, orgID, scope, subjectMemberID, teamID, projectID string, queryEmbedding []float64, limit int) ([]store.MemoryItem, error) {
	if limit <= 0 {
		limit = 8
	}
	rows, err := s.db.QueryContext(ctx, `
select id, org_id, scope, subject_member_id, team_id, project_id,
       status, sensitivity, memory_type, source_type, source_member_id, created_by_member_id,
       content, coalesce(embedding::text, ''), version
from tcg_memory_items
where org_id = $1
  and scope = $2
  and status = 'active'
  and ($3 = '' or subject_member_id = $3)
  and ($4 = '' or team_id = $4)
  and ($5 = '' or project_id = '' or project_id = $5)
  and embedding is not null
order by embedding <=> $6::vector, id
limit $7
`, orgID, scope, subjectMemberID, teamID, projectID, store.VectorLiteral(queryEmbedding), limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	return scanMemoryRows(rows)
}

func (s *Store) reviewDecision(ctx context.Context, reviewID, actorMemberID, reviewStatus, memoryStatus, editedContent, reason string) (store.ReviewDecision, error) {
	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		return store.ReviewDecision{}, err
	}
	defer rollbackUnlessCommitted(tx)

	var review store.ReviewItem
	var item store.MemoryItem
	err = tx.QueryRowContext(ctx, `
select r.id, r.org_id, r.memory_id, r.status, r.review_kind, r.submitted_by_member_id,
       m.id, m.org_id, m.scope, m.subject_member_id, m.team_id, m.project_id,
       m.status, m.sensitivity, m.memory_type, m.source_type, m.source_member_id, m.created_by_member_id,
       m.content, coalesce(m.embedding::text, ''), m.version
from tcg_memory_review_items r
join tcg_memory_items m on m.id = r.memory_id
where r.id = $1
for update
`, reviewID).Scan(
		&review.ID, &review.OrgID, &review.MemoryID, &review.Status, &review.ReviewKind, &review.SubmittedByMemberID,
		&item.ID, &item.OrgID, &item.Scope, &item.SubjectMemberID, &item.TeamID, &item.ProjectID,
		&item.Status, &item.Sensitivity, &item.MemoryType, &item.SourceType, &item.SourceMemberID, &item.CreatedByMemberID,
		&item.Content, (*vectorScanTarget)(&item.Embedding), &item.Version,
	)
	if errors.Is(err, sql.ErrNoRows) {
		return store.ReviewDecision{}, store.ErrNotFound
	}
	if err != nil {
		return store.ReviewDecision{}, err
	}
	if editedContent != "" {
		item.Content = editedContent
	}
	item.Status = memoryStatus
	item.Version++
	_, err = tx.ExecContext(ctx, `
update tcg_memory_items
set content = $2, status = $3, version = $4, updated_at = now()
where id = $1
`, item.ID, item.Content, item.Status, item.Version)
	if err != nil {
		return store.ReviewDecision{}, err
	}
	_, err = tx.ExecContext(ctx, `
update tcg_memory_review_items
set status = $2,
    reviewed_by_member_id = $3,
    reason = $4,
    reviewed_at = now()
where id = $1
`, review.ID, reviewStatus, actorMemberID, reason)
	if err != nil {
		return store.ReviewDecision{}, err
	}
	if err := tx.Commit(); err != nil {
		return store.ReviewDecision{}, err
	}
	return store.ReviewDecision{ID: review.ID, Status: reviewStatus, MemoryID: item.ID, MemoryStatus: item.Status}, nil
}

func scanMemoryRows(rows *sql.Rows) ([]store.MemoryItem, error) {
	out := []store.MemoryItem{}
	for rows.Next() {
		var item store.MemoryItem
		if err := rows.Scan(
			&item.ID, &item.OrgID, &item.Scope, &item.SubjectMemberID, &item.TeamID, &item.ProjectID,
			&item.Status, &item.Sensitivity, &item.MemoryType, &item.SourceType, &item.SourceMemberID, &item.CreatedByMemberID,
			&item.Content, (*vectorScanTarget)(&item.Embedding), &item.Version,
		); err != nil {
			return nil, err
		}
		out = append(out, item)
	}
	return out, rows.Err()
}

type vectorScanTarget []float64

func (target *vectorScanTarget) Scan(value any) error {
	switch typed := value.(type) {
	case nil:
		*target = nil
	case string:
		*target = vectorScanTarget(store.ParseVectorLiteral(typed))
	case []byte:
		*target = vectorScanTarget(store.ParseVectorLiteral(string(typed)))
	default:
		return fmt.Errorf("unsupported vector scan type %T", value)
	}
	return nil
}

func filterPrefetch(items []store.MemoryItem, query, projectID string, limit int) []store.MemoryItem {
	if limit <= 0 {
		limit = 8
	}
	out := []store.MemoryItem{}
	for _, item := range items {
		if projectID != "" && item.ProjectID != "" && item.ProjectID != projectID {
			continue
		}
		if !matchesQuery(item.Content, query) {
			continue
		}
		out = append(out, item)
	}
	sort.Slice(out, func(i, j int) bool { return out[i].ID < out[j].ID })
	if len(out) > limit {
		return out[:limit]
	}
	return out
}

func (s *Store) markTeamMemories(ctx context.Context, orgID, status string) error {
	_, err := s.db.ExecContext(ctx, `
update tcg_memory_items
set status = $2, version = version + 1, updated_at = now()
where org_id = $1
  and scope = 'team_shared'
  and status = 'active'
`, orgID, status)
	return err
}

func (s *Store) findToolPolicyRule(ctx context.Context, orgID, toolName, riskLevel string) (store.ToolPolicyRule, bool, error) {
	for _, candidateRisk := range []string{riskLevel, "*"} {
		var rule store.ToolPolicyRule
		err := s.db.QueryRowContext(ctx, `
select org_id, tool_name, risk_level, decision, updated_by
from tcg_tool_policy_rules
where org_id = $1 and tool_name = $2 and risk_level = $3
`, orgID, toolName, candidateRisk).Scan(&rule.OrgID, &rule.ToolName, &rule.RiskLevel, &rule.Decision, &rule.UpdatedBy)
		if err == nil {
			return rule, true, nil
		}
		if !errors.Is(err, sql.ErrNoRows) {
			return store.ToolPolicyRule{}, false, err
		}
	}
	return store.ToolPolicyRule{}, false, nil
}

func validateMemory(item store.MemoryItem) error {
	if item.OrgID == "" {
		return fmt.Errorf("org_id is required")
	}
	if item.Content == "" {
		return fmt.Errorf("content is required")
	}
	switch item.Scope {
	case "team_shared":
		if item.SubjectMemberID != "" {
			return fmt.Errorf("team_shared memory requires no subject_member_id")
		}
	default:
		return fmt.Errorf("scope must be team_shared")
	}
	switch item.SourceType {
	case "", "auto_extracted", "admin_created":
	default:
		return fmt.Errorf("source_type must be auto_extracted or admin_created")
	}
	return nil
}

func normalizeMemorySource(item *store.MemoryItem) {
	if item.Scope != "team_shared" {
		return
	}
	if item.SourceType == "" {
		item.SourceType = "auto_extracted"
	}
	if item.SourceType == "auto_extracted" && item.SourceMemberID == "" {
		item.SourceMemberID = item.CreatedByMemberID
	}
	if item.SourceType == "admin_created" {
		item.SourceMemberID = ""
	}
}

func validatePostgresEmbedding(values []float64) error {
	if len(values) == 0 {
		return nil
	}
	if len(values) != postgresEmbeddingDimension {
		return fmt.Errorf("embedding must have %d dimensions for postgres pgvector", postgresEmbeddingDimension)
	}
	return nil
}

func normalizeRestoreMode(mode string) string {
	return defaultString(mode, "merge")
}

func validateRestoreMode(mode string) error {
	switch mode {
	case "merge", "overwrite", "archive_current_then_restore":
		return nil
	default:
		return fmt.Errorf("unsupported_restore_mode")
	}
}

func rollbackUnlessCommitted(tx *sql.Tx) {
	_ = tx.Rollback()
}

func randomID(prefix string) string {
	var b [16]byte
	if _, err := rand.Read(b[:]); err != nil {
		return fmt.Sprintf("%s-%d", prefix, time.Now().UnixNano())
	}
	return prefix + "-" + hex.EncodeToString(b[:])
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

func defaultString(value, fallback string) string {
	if value == "" {
		return fallback
	}
	return value
}

func nullTimeString(value sql.NullTime) string {
	if !value.Valid {
		return ""
	}
	return value.Time.UTC().Format(time.RFC3339)
}

func matchesQuery(content, query string) bool {
	query = strings.TrimSpace(strings.ToLower(query))
	if query == "" {
		return true
	}
	content = strings.ToLower(content)
	for _, token := range strings.Fields(query) {
		if strings.Contains(content, token) {
			return true
		}
	}
	return false
}

func relationshipKey(relationship store.Relationship) string {
	return relationship.OrgID + ":" + relationship.ResourceType + ":" + relationship.ResourceID + "#" + relationship.Relation + "@" + relationship.SubjectType + ":" + relationship.SubjectID
}

func relationAllows(relation, permission string) bool {
	switch relation {
	case "owner", "admin":
		return true
	case "member":
		return permission == "read" || permission == "read_team" || permission == "use" || permission == "run_agent"
	case "reviewer":
		return permission == "review" || permission == "read" || permission == "read_team"
	default:
		return relation == permission
	}
}
