package memory

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"sort"
	"sync"
	"time"

	"hermes-agent/team_cloud/internal/store"
)

type Store struct {
	mu              sync.RWMutex
	orgs            map[string]store.Organization
	members         map[string]store.Member
	memories        map[string]store.MemoryItem
	reviews         map[string]store.ReviewItem
	observations    map[string]store.Observation
	backupPolicy    map[string]store.BackupPolicy
	auditEvents     []store.AuditEvent
	relationships   map[string]store.Relationship
	backupJobs      map[string]store.BackupJob
	restorePreviews map[string]bool
	orgExports      map[string]store.OrgExport
	deletions       map[string]store.DeletionRequest
	toolRules       map[string]store.ToolPolicyRule
	sessions        map[string]store.CloudSession
	runtimeEvents   []store.RuntimeEvent
	teamSouls       map[string]store.TeamSoul
	memoryCounter   int
	reviewCounter   int
	obsCounter      int
	auditCounter    int
	backupCounter   int
	exportCounter   int
	deleteCounter   int
	approvalCount   int
	sessionCount    int
	eventCounter    int
}

func New() *Store {
	return &Store{
		orgs:            map[string]store.Organization{},
		members:         map[string]store.Member{},
		memories:        map[string]store.MemoryItem{},
		reviews:         map[string]store.ReviewItem{},
		observations:    map[string]store.Observation{},
		backupPolicy:    map[string]store.BackupPolicy{},
		relationships:   map[string]store.Relationship{},
		backupJobs:      map[string]store.BackupJob{},
		restorePreviews: map[string]bool{},
		orgExports:      map[string]store.OrgExport{},
		deletions:       map[string]store.DeletionRequest{},
		toolRules:       map[string]store.ToolPolicyRule{},
		sessions:        map[string]store.CloudSession{},
		teamSouls:       map[string]store.TeamSoul{},
	}
}

func (s *Store) Ping(ctx context.Context) error {
	return nil
}

func (s *Store) CreateOrganization(ctx context.Context, slug, name string) (store.Organization, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if slug == "" || name == "" {
		return store.Organization{}, fmt.Errorf("slug and name are required")
	}
	org := store.Organization{ID: slug, Slug: slug, Name: name, Status: "active"}
	s.orgs[slug] = org
	return org, nil
}

func (s *Store) ListOrganizations(ctx context.Context) ([]store.Organization, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	out := make([]store.Organization, 0, len(s.orgs))
	for _, org := range s.orgs {
		out = append(out, org)
	}
	sort.Slice(out, func(i, j int) bool { return out[i].ID < out[j].ID })
	return out, nil
}

func (s *Store) CreateMember(ctx context.Context, orgID, email, displayName, userID, role, passwordHash string) (store.Member, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.createMemberLocked(orgID, email, displayName, userID, role, "active", passwordHash)
}

func (s *Store) InviteMember(ctx context.Context, orgID, email, displayName, userID, role string) (store.Member, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.createMemberLocked(orgID, email, displayName, userID, role, "invited", "")
}

func (s *Store) createMemberLocked(orgID, email, displayName, userID, role, status, passwordHash string) (store.Member, error) {
	if _, ok := s.orgs[orgID]; !ok {
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
	s.members[member.ID] = member
	return member, nil
}

func (s *Store) GetMemberByUserID(ctx context.Context, orgID, userID string) (store.Member, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	member, ok := s.members[orgID+":"+userID]
	if !ok || member.OrgID != orgID {
		return store.Member{}, store.ErrNotFound
	}
	return member, nil
}

func (s *Store) GetMember(ctx context.Context, orgID, memberID string) (store.Member, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	member, ok := s.members[memberID]
	if !ok || member.OrgID != orgID {
		return store.Member{}, store.ErrNotFound
	}
	return member, nil
}

func (s *Store) UpdateMember(ctx context.Context, orgID, memberID, email, displayName string) (store.Member, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	member, ok := s.members[memberID]
	if !ok || member.OrgID != orgID {
		return store.Member{}, store.ErrNotFound
	}
	member.Email = email
	member.DisplayName = displayName
	s.members[memberID] = member
	return member, nil
}

func (s *Store) ListMembers(ctx context.Context, orgID string) ([]store.Member, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	if _, ok := s.orgs[orgID]; !ok {
		return nil, store.ErrNotFound
	}
	out := []store.Member{}
	for _, member := range s.members {
		if member.OrgID == orgID {
			out = append(out, member)
		}
	}
	sort.Slice(out, func(i, j int) bool { return out[i].ID < out[j].ID })
	return out, nil
}

func (s *Store) DisableMember(ctx context.Context, orgID, memberID string) (store.Member, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	member, ok := s.members[memberID]
	if !ok || member.OrgID != orgID {
		return store.Member{}, store.ErrNotFound
	}
	member.Status = "suspended"
	s.members[memberID] = member
	return member, nil
}

func (s *Store) CreateMemory(ctx context.Context, payload map[string]any) (store.MemoryItem, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	scope := stringValue(payload, "scope")
	content := stringValue(payload, "content")
	if content == "" {
		return store.MemoryItem{}, fmt.Errorf("content is required")
	}
	status := stringValue(payload, "status")
	if status == "" {
		if scope == "team_shared" {
			status = "pending_review"
		} else {
			status = "active"
		}
	}
	item := store.MemoryItem{
		ID:                s.nextMemoryID(),
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
		Content:           content,
		Embedding:         store.Float64Slice(payload["embedding"]),
		Version:           1,
	}
	normalizeMemorySource(&item)
	if err := store.ValidateEmbedding(item.Embedding); err != nil {
		return store.MemoryItem{}, err
	}
	if err := validateMemory(item); err != nil {
		return store.MemoryItem{}, err
	}
	s.memories[item.ID] = item
	if item.Scope == "team_shared" && item.Status == "pending_review" {
		review := store.ReviewItem{
			ID:                  s.nextReviewID(),
			OrgID:               item.OrgID,
			MemoryID:            item.ID,
			Status:              "pending",
			ReviewKind:          "team_shared_memory",
			SubmittedByMemberID: stringValue(payload, "created_by_member_id"),
		}
		s.reviews[review.ID] = review
	}
	return item, nil
}

func (s *Store) ListMemory(ctx context.Context, filter store.MemoryFilter) ([]store.MemoryItem, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	out := []store.MemoryItem{}
	for _, item := range s.memories {
		if item.OrgID != filter.OrgID {
			continue
		}
		if filter.Scope != "" && item.Scope != filter.Scope {
			continue
		}
		if filter.Status != "" && item.Status != filter.Status {
			continue
		}
		if filter.MemoryType != "" && item.MemoryType != filter.MemoryType {
			continue
		}
		if filter.Sensitivity != "" && item.Sensitivity != filter.Sensitivity {
			continue
		}
		out = append(out, item)
	}
	sort.Slice(out, func(i, j int) bool { return out[i].ID < out[j].ID })
	return out, nil
}

func (s *Store) GetMemory(ctx context.Context, memoryID string) (store.MemoryItem, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	item, ok := s.memories[memoryID]
	if !ok {
		return store.MemoryItem{}, store.ErrNotFound
	}
	return item, nil
}

func (s *Store) UpdateMemory(ctx context.Context, memoryID string, payload map[string]any) (store.MemoryItem, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	item, ok := s.memories[memoryID]
	if !ok {
		return store.MemoryItem{}, store.ErrNotFound
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
	}
	if err := validateMemory(item); err != nil {
		return store.MemoryItem{}, err
	}
	item.Version++
	s.memories[memoryID] = item
	return item, nil
}

func (s *Store) DeleteMemory(ctx context.Context, memoryID string) (store.MemoryItem, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	item, ok := s.memories[memoryID]
	if !ok {
		return store.MemoryItem{}, store.ErrNotFound
	}
	delete(s.memories, memoryID)
	for reviewID, review := range s.reviews {
		if review.MemoryID == memoryID {
			delete(s.reviews, reviewID)
		}
	}
	return item, nil
}

func (s *Store) SetMemoryStatus(ctx context.Context, memoryID, status string) (store.MemoryItem, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	item, ok := s.memories[memoryID]
	if !ok {
		return store.MemoryItem{}, store.ErrNotFound
	}
	item.Status = status
	item.Version++
	s.memories[memoryID] = item
	return item, nil
}

func (s *Store) CreateObservation(ctx context.Context, payload map[string]any) (store.Observation, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	observationPayload, _ := payload["observation"].(map[string]any)
	s.obsCounter++
	observation := store.Observation{
		ID:        fmt.Sprintf("obs-%d", s.obsCounter),
		OrgID:     stringValue(payload, "org_id"),
		SessionID: stringValue(payload, "session_id"),
		MemberID:  stringValue(payload, "member_id"),
		TeamID:    stringValue(payload, "team_id"),
		ProjectID: stringValue(payload, "project_id"),
		Status:    "pending",
		Payload:   observationPayload,
	}
	s.observations[observation.ID] = observation
	return observation, nil
}

func (s *Store) Prefetch(ctx context.Context, req store.PrefetchRequest) ([]store.MemoryPartition, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	partitions := []store.MemoryPartition{}
	teamItems := s.matchMemories(0, func(item store.MemoryItem) bool {
		if item.OrgID != req.OrgID || item.Scope != "team_shared" || item.Status != "active" {
			return false
		}
		if item.TeamID != "" && item.TeamID != req.TeamID {
			return false
		}
		return true
	})
	teamItems = store.RankPrefetchItems(teamItems, req.Query, req.ProjectID, req.QueryEmbedding, req.Limit)
	if len(teamItems) > 0 {
		partitions = append(partitions, store.MemoryPartition{Scope: "team_shared", Items: teamItems})
	}
	return partitions, nil
}

func (s *Store) ListReviews(ctx context.Context, orgID, status, reviewKind string, limit int) ([]store.ReviewItem, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	if limit <= 0 {
		limit = 100
	}
	out := []store.ReviewItem{}
	for _, review := range s.reviews {
		if review.OrgID != orgID {
			continue
		}
		if status != "" && review.Status != status {
			continue
		}
		if reviewKind != "" && review.ReviewKind != reviewKind {
			continue
		}
		out = append(out, review)
		if len(out) >= limit {
			break
		}
	}
	sort.Slice(out, func(i, j int) bool { return out[i].ID < out[j].ID })
	return out, nil
}

func (s *Store) GetReview(ctx context.Context, reviewID string) (store.ReviewItem, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	review, ok := s.reviews[reviewID]
	if !ok {
		return store.ReviewItem{}, store.ErrNotFound
	}
	return review, nil
}

func (s *Store) ApproveReview(ctx context.Context, reviewID, actorMemberID string, edits map[string]any) (store.ReviewDecision, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	review, ok := s.reviews[reviewID]
	if !ok {
		return store.ReviewDecision{}, store.ErrNotFound
	}
	item := s.memories[review.MemoryID]
	if content := stringValue(edits, "content"); content != "" {
		item.Content = content
	}
	item.Status = "active"
	item.Version++
	review.Status = "approved"
	s.memories[item.ID] = item
	s.reviews[reviewID] = review
	return store.ReviewDecision{ID: review.ID, Status: review.Status, MemoryID: item.ID, MemoryStatus: item.Status}, nil
}

func (s *Store) RejectReview(ctx context.Context, reviewID, actorMemberID, reason string) (store.ReviewDecision, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	review, ok := s.reviews[reviewID]
	if !ok {
		return store.ReviewDecision{}, store.ErrNotFound
	}
	item := s.memories[review.MemoryID]
	item.Status = "rejected"
	item.Version++
	review.Status = "rejected"
	s.memories[item.ID] = item
	s.reviews[reviewID] = review
	return store.ReviewDecision{ID: review.ID, Status: review.Status, MemoryID: item.ID, MemoryStatus: item.Status}, nil
}

func (s *Store) GetBackupPolicy(ctx context.Context, orgID, memberID string) (store.BackupPolicy, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	key := backupKey(orgID, memberID)
	policy, ok := s.backupPolicy[key]
	if !ok {
		return store.BackupPolicy{OrgID: orgID, MemberID: memberID, Cadence: "weekly", Enabled: false, RetentionCount: 4}, nil
	}
	return policy, nil
}

func (s *Store) UpsertBackupPolicy(ctx context.Context, policy store.BackupPolicy) (store.BackupPolicy, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if policy.Cadence == "" {
		policy.Cadence = "weekly"
	}
	if policy.RetentionCount == 0 {
		policy.RetentionCount = 4
	}
	s.backupPolicy[backupKey(policy.OrgID, policy.MemberID)] = policy
	return policy, nil
}

func (s *Store) ListBackupPolicies(ctx context.Context, enabledOnly bool) ([]store.BackupPolicy, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	out := []store.BackupPolicy{}
	for _, policy := range s.backupPolicy {
		if enabledOnly && !policy.Enabled {
			continue
		}
		out = append(out, policy)
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].OrgID == out[j].OrgID {
			return out[i].MemberID < out[j].MemberID
		}
		return out[i].OrgID < out[j].OrgID
	})
	return out, nil
}

func (s *Store) MarkBackupPolicyRun(ctx context.Context, orgID, memberID, lastRunAt, nextRunAt string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	key := backupKey(orgID, memberID)
	policy, ok := s.backupPolicy[key]
	if !ok {
		return store.ErrNotFound
	}
	policy.LastRunAt = lastRunAt
	policy.NextRunAt = nextRunAt
	s.backupPolicy[key] = policy
	return nil
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
	s.mu.Lock()
	defer s.mu.Unlock()
	s.auditCounter++
	if event.ID == "" {
		event.ID = fmt.Sprintf("audit-%d", s.auditCounter)
	}
	if event.Decision == "" {
		event.Decision = "allowed"
	}
	if event.Metadata == nil {
		event.Metadata = map[string]any{}
	}
	s.auditEvents = append(s.auditEvents, event)
	return event, nil
}

func (s *Store) ListAuditEvents(ctx context.Context, orgID string, limit int) ([]store.AuditEvent, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	if limit <= 0 {
		limit = 100
	}
	out := []store.AuditEvent{}
	for i := len(s.auditEvents) - 1; i >= 0 && len(out) < limit; i-- {
		event := s.auditEvents[i]
		if orgID == "" || event.OrgID == orgID {
			out = append(out, event)
		}
	}
	return out, nil
}

func (s *Store) WriteRelationship(ctx context.Context, relationship store.Relationship) (store.Relationship, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if relationship.OrgID == "" || relationship.ResourceType == "" || relationship.ResourceID == "" || relationship.SubjectID == "" {
		return store.Relationship{}, fmt.Errorf("org_id, resource, and subject are required")
	}
	if relationship.Relation == "" {
		relationship.Relation = "member"
	}
	if relationship.SubjectType == "" {
		relationship.SubjectType = "member"
	}
	key := relationshipKey(relationship)
	if relationship.IdempotencyKey != "" {
		key = relationship.IdempotencyKey
	}
	s.relationships[key] = relationship
	return relationship, nil
}

func (s *Store) CheckPermission(ctx context.Context, check store.PermissionCheck) (store.PermissionDecision, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	for _, relationship := range s.relationships {
		if relationship.OrgID != check.OrgID ||
			relationship.ResourceType != check.ResourceType ||
			relationship.ResourceID != check.ResourceID ||
			relationship.SubjectType != check.SubjectType ||
			relationship.SubjectID != check.SubjectID {
			continue
		}
		if relationAllows(relationship.Relation, check.Permission) {
			path := fmt.Sprintf("%s:%s#%s@%s:%s", relationship.ResourceType, relationship.ResourceID, relationship.Relation, relationship.SubjectType, relationship.SubjectID)
			return store.PermissionDecision{Allowed: true, Reason: "relationship_allowed", Path: []string{path}}, nil
		}
	}
	return store.PermissionDecision{Allowed: false, Reason: "no_matching_relationship"}, nil
}

func (s *Store) RunTeamMemoryBackup(ctx context.Context, orgID string) (store.BackupJob, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	items := []store.MemoryItem{}
	for _, item := range s.memories {
		if item.OrgID == orgID && item.Scope == "team_shared" && item.Status == "active" {
			items = append(items, item)
		}
	}
	sort.Slice(items, func(i, j int) bool { return items[i].ID < items[j].ID })
	raw, err := json.Marshal(items)
	if err != nil {
		return store.BackupJob{}, err
	}
	sum := sha256.Sum256(raw)
	s.backupCounter++
	job := store.BackupJob{
		ID:             fmt.Sprintf("backup-%d", s.backupCounter),
		OrgID:          orgID,
		MemberID:       store.TeamBackupMemberID,
		Status:         "completed",
		ObjectKey:      fmt.Sprintf("org/%s/team-memory/backup-%d.jsonl.enc", orgID, s.backupCounter),
		ObjectUploaded: false,
		ChecksumSHA256: hex.EncodeToString(sum[:]),
		ItemCount:      len(items),
		Manifest: map[string]any{
			"object_store": "database",
			"format":       "json",
			"backup_scope": "team_memory",
		},
		Items:     cloneMemoryItems(items),
		CreatedAt: time.Now().UTC(),
	}
	s.backupJobs[job.ID] = job
	return job, nil
}

func (s *Store) RunTeamSoulBackup(ctx context.Context, orgID, teamID string) (store.BackupJob, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if teamID == "" {
		teamID = orgID
	}
	soul, ok := s.teamSouls[teamSoulKey(orgID, teamID)]
	if !ok {
		return store.BackupJob{}, store.ErrNotFound
	}
	manifest := map[string]any{
		"object_store": "database",
		"format":       "json",
		"backup_scope": "team_soul",
		"team_soul":    store.TeamSoulBackupManifest(soul),
	}
	raw, err := json.Marshal(manifest)
	if err != nil {
		return store.BackupJob{}, err
	}
	sum := sha256.Sum256(raw)
	s.backupCounter++
	job := store.BackupJob{
		ID:             fmt.Sprintf("backup-%d", s.backupCounter),
		OrgID:          orgID,
		MemberID:       store.TeamSoulBackupMemberID,
		Status:         "completed",
		ObjectKey:      fmt.Sprintf("org/%s/team-soul/backup-%d.json.enc", orgID, s.backupCounter),
		ObjectUploaded: false,
		ChecksumSHA256: hex.EncodeToString(sum[:]),
		ItemCount:      1,
		Manifest:       manifest,
		CreatedAt:      time.Now().UTC(),
	}
	s.backupJobs[job.ID] = job
	return job, nil
}

func (s *Store) ListBackupJobs(ctx context.Context, orgID, memberID string, limit int) ([]store.BackupJob, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	if limit <= 0 {
		limit = 100
	}
	jobs := []store.BackupJob{}
	for _, job := range s.backupJobs {
		if job.OrgID == orgID && job.MemberID == memberID && job.Status != "pruned" {
			job.Items = nil
			jobs = append(jobs, job)
		}
	}
	sort.Slice(jobs, func(i, j int) bool {
		if jobs[i].CreatedAt.Equal(jobs[j].CreatedAt) {
			return jobs[i].ID > jobs[j].ID
		}
		return jobs[i].CreatedAt.After(jobs[j].CreatedAt)
	})
	if len(jobs) > limit {
		jobs = jobs[:limit]
	}
	return jobs, nil
}

func (s *Store) GetBackupJob(ctx context.Context, backupID string) (store.BackupJob, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	job, ok := s.backupJobs[backupID]
	if !ok {
		return store.BackupJob{}, store.ErrNotFound
	}
	job.Items = cloneMemoryItems(job.Items)
	return job, nil
}

func (s *Store) UpdateBackupObject(ctx context.Context, backupID, checksumSHA256 string, manifest map[string]any) (store.BackupJob, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	job, ok := s.backupJobs[backupID]
	if !ok {
		return store.BackupJob{}, store.ErrNotFound
	}
	job.ObjectUploaded = true
	job.ChecksumSHA256 = checksumSHA256
	job.Manifest = cloneMap(manifest)
	s.backupJobs[backupID] = job
	job.Items = cloneMemoryItems(job.Items)
	return job, nil
}

func (s *Store) UpdateBackupItems(ctx context.Context, backupID string, items []store.MemoryItem) (store.BackupJob, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	job, ok := s.backupJobs[backupID]
	if !ok {
		return store.BackupJob{}, store.ErrNotFound
	}
	job.Items = cloneMemoryItems(items)
	job.ItemCount = len(items)
	s.backupJobs[backupID] = job
	job.Items = cloneMemoryItems(job.Items)
	return job, nil
}

func (s *Store) PruneBackupJobs(ctx context.Context, orgID, memberID string, keep int) (int, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if keep <= 0 {
		return 0, nil
	}
	jobs := []store.BackupJob{}
	for _, job := range s.backupJobs {
		if job.OrgID == orgID && job.MemberID == memberID && job.Status != "pruned" {
			jobs = append(jobs, job)
		}
	}
	sort.Slice(jobs, func(i, j int) bool {
		if jobs[i].CreatedAt.Equal(jobs[j].CreatedAt) {
			return jobs[i].ID > jobs[j].ID
		}
		return jobs[i].CreatedAt.After(jobs[j].CreatedAt)
	})
	if len(jobs) <= keep {
		return 0, nil
	}
	pruned := 0
	for _, job := range jobs[keep:] {
		job.Status = "pruned"
		job.Items = nil
		s.backupJobs[job.ID] = job
		pruned++
	}
	return pruned, nil
}

func (s *Store) PreviewTeamMemoryRestore(ctx context.Context, backupID, mode string) (store.RestorePreview, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	job, ok := s.backupJobs[backupID]
	if !ok {
		return store.RestorePreview{}, store.ErrNotFound
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
		if _, exists := s.memories[item.ID]; exists {
			skipCount++
		} else {
			createCount++
		}
	}
	preview := store.RestorePreview{BackupID: backupID, MemberID: store.TeamBackupMemberID, CreateCount: createCount, SkipCount: skipCount, Mode: mode}
	s.restorePreviews[restorePreviewKey(preview.BackupID, preview.MemberID, preview.Mode)] = true
	return preview, nil
}

func (s *Store) ExecuteTeamMemoryRestore(ctx context.Context, backupID, mode string) (store.RestoreExecution, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	job, ok := s.backupJobs[backupID]
	if !ok {
		return store.RestoreExecution{}, store.ErrNotFound
	}
	mode = normalizeRestoreMode(mode)
	if err := validateRestoreMode(mode); err != nil {
		return store.RestoreExecution{}, err
	}
	if !s.restorePreviews[restorePreviewKey(backupID, store.TeamBackupMemberID, mode)] {
		return store.RestoreExecution{}, fmt.Errorf("restore_preview_required")
	}
	switch mode {
	case "overwrite":
		s.markTeamMemories(job.OrgID, "deleted")
	case "archive_current_then_restore":
		s.markTeamMemories(job.OrgID, "archived")
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
		if existing, ok := s.memories[item.ID]; ok {
			item.Version = existing.Version + 1
		}
		s.memories[item.ID] = item
		restored++
	}
	return store.RestoreExecution{BackupID: backupID, MemberID: store.TeamBackupMemberID, Mode: mode, RestoredCount: restored, Status: "executed"}, nil
}

func (s *Store) PreviewTeamSoulRestore(ctx context.Context, backupID, mode string) (store.RestorePreview, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	job, ok := s.backupJobs[backupID]
	if !ok {
		return store.RestorePreview{}, store.ErrNotFound
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
	createCount := 1
	skipCount := 0
	if existing, ok := s.teamSouls[teamSoulKey(soul.OrgID, soul.TeamID)]; ok && existing.ChecksumSHA256 == soul.ChecksumSHA256 {
		createCount = 0
		skipCount = 1
	}
	preview := store.RestorePreview{BackupID: backupID, MemberID: store.TeamSoulBackupMemberID, CreateCount: createCount, SkipCount: skipCount, Mode: mode}
	s.restorePreviews[restorePreviewKey(preview.BackupID, preview.MemberID, preview.Mode)] = true
	return preview, nil
}

func (s *Store) ExecuteTeamSoulRestore(ctx context.Context, backupID, mode string) (store.RestoreExecution, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	job, ok := s.backupJobs[backupID]
	if !ok {
		return store.RestoreExecution{}, store.ErrNotFound
	}
	if job.MemberID != store.TeamSoulBackupMemberID {
		return store.RestoreExecution{}, fmt.Errorf("unsupported_backup_scope")
	}
	mode = normalizeRestoreMode(mode)
	if err := validateRestoreMode(mode); err != nil {
		return store.RestoreExecution{}, err
	}
	if !s.restorePreviews[restorePreviewKey(backupID, store.TeamSoulBackupMemberID, mode)] {
		return store.RestoreExecution{}, fmt.Errorf("restore_preview_required")
	}
	soul, err := store.TeamSoulFromBackupManifest(job.Manifest)
	if err != nil {
		return store.RestoreExecution{}, err
	}
	key := teamSoulKey(soul.OrgID, soul.TeamID)
	existing, ok := s.teamSouls[key]
	if ok {
		soul.Version = existing.Version + 1
	} else if soul.Version <= 0 {
		soul.Version = 1
	}
	if soul.UpdatedBy == "" {
		soul.UpdatedBy = "restore:" + backupID
	}
	soul.UpdatedAt = time.Now().UTC().Format(time.RFC3339)
	s.teamSouls[key] = soul
	return store.RestoreExecution{BackupID: backupID, MemberID: store.TeamSoulBackupMemberID, Mode: mode, RestoredCount: 1, Status: "executed"}, nil
}

func (s *Store) markTeamMemories(orgID, status string) {
	for id, item := range s.memories {
		if item.OrgID == orgID && item.Scope == "team_shared" && item.Status == "active" {
			item.Status = status
			item.Version++
			s.memories[id] = item
		}
	}
}

func (s *Store) CreateOrgExport(ctx context.Context, orgID string) (store.OrgExport, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	sharedCount := 0
	for _, item := range s.memories {
		if item.OrgID == orgID && item.Scope == "team_shared" && item.Status == "active" {
			sharedCount++
		}
	}
	s.exportCounter++
	export := store.OrgExport{
		ID:              fmt.Sprintf("export-%d", s.exportCounter),
		OrgID:           orgID,
		Status:          "completed",
		TeamSharedCount: sharedCount,
		PersonalCount:   0,
		Manifest: map[string]any{
			"contains_personal_memory": false,
			"team_shared_count":        sharedCount,
		},
	}
	s.orgExports[export.ID] = export
	return export, nil
}

func (s *Store) CreateDeletionRequest(ctx context.Context, req store.DeletionRequest) (store.DeletionRequest, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if req.OrgID == "" || req.TargetMemberID == "" || req.DeletionScope == "" {
		return store.DeletionRequest{}, fmt.Errorf("org_id, target_member_id, and deletion_scope are required")
	}
	scope, err := store.NormalizeDeletionScope(req.DeletionScope)
	if err != nil {
		return store.DeletionRequest{}, err
	}
	req.DeletionScope = scope
	s.deleteCounter++
	req.ID = fmt.Sprintf("deletion-%d", s.deleteCounter)
	req.Status = "pending"
	s.deletions[req.ID] = req
	return req, nil
}

func (s *Store) GetDeletionRequest(ctx context.Context, requestID string) (store.DeletionRequest, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	req, ok := s.deletions[requestID]
	if !ok {
		return store.DeletionRequest{}, store.ErrNotFound
	}
	return req, nil
}

func (s *Store) ExecuteDeletionRequest(ctx context.Context, requestID, actorMemberID string) (store.DeletionRequest, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	req, ok := s.deletions[requestID]
	if !ok {
		return store.DeletionRequest{}, store.ErrNotFound
	}
	if _, err := store.NormalizeDeletionScope(req.DeletionScope); err != nil {
		return store.DeletionRequest{}, err
	}
	req.Status = "executed"
	s.deletions[requestID] = req
	return req, nil
}

func (s *Store) UpsertToolPolicyRule(ctx context.Context, rule store.ToolPolicyRule) (store.ToolPolicyRule, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if rule.OrgID == "" || rule.ToolName == "" || rule.Decision == "" {
		return store.ToolPolicyRule{}, fmt.Errorf("org_id, tool_name, and decision are required")
	}
	if rule.RiskLevel == "" {
		rule.RiskLevel = "*"
	}
	s.toolRules[toolRuleKey(rule.OrgID, rule.ToolName, rule.RiskLevel)] = rule
	return rule, nil
}

func (s *Store) EvaluateToolPolicy(ctx context.Context, req store.ToolPolicyRequest) (store.ToolPolicyDecision, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if rule, ok := s.toolRules[toolRuleKey(req.OrgID, req.ToolName, req.RiskLevel)]; ok {
		return store.ToolPolicyDecision{Decision: rule.Decision, Reason: "explicit_rule", EffectiveRule: toolRuleKey(req.OrgID, req.ToolName, req.RiskLevel)}, nil
	}
	if rule, ok := s.toolRules[toolRuleKey(req.OrgID, req.ToolName, "*")]; ok {
		return store.ToolPolicyDecision{Decision: rule.Decision, Reason: "explicit_rule", EffectiveRule: toolRuleKey(req.OrgID, req.ToolName, "*")}, nil
	}
	switch req.RiskLevel {
	case "safe", "low":
		return store.ToolPolicyDecision{Decision: "allowed", Reason: "default_low_risk"}, nil
	case "destructive", "critical", "high":
		s.approvalCount++
		return store.ToolPolicyDecision{Decision: "approval_required", Reason: "high_risk_default", ApprovalID: fmt.Sprintf("approval-%d", s.approvalCount)}, nil
	default:
		return store.ToolPolicyDecision{Decision: "denied", Reason: "unknown_risk_level"}, nil
	}
}

func (s *Store) CreateCloudSession(ctx context.Context, session store.CloudSession) (store.CloudSession, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.sessionCount++
	if session.ID == "" {
		session.ID = fmt.Sprintf("session-%d", s.sessionCount)
	}
	if session.Status == "" {
		session.Status = "active"
	}
	s.sessions[session.ID] = session
	return session, nil
}

func (s *Store) GetCloudSession(ctx context.Context, sessionID string) (store.CloudSession, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	session, ok := s.sessions[sessionID]
	if !ok {
		return store.CloudSession{}, store.ErrNotFound
	}
	return session, nil
}

func (s *Store) AppendRuntimeEvent(ctx context.Context, event store.RuntimeEvent) (store.RuntimeEvent, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.eventCounter++
	if event.ID == "" {
		event.ID = fmt.Sprintf("event-%d", s.eventCounter)
	}
	if event.CreatedAt.IsZero() {
		event.CreatedAt = time.Now().UTC()
	}
	if event.Payload == nil {
		event.Payload = map[string]any{}
	}
	s.runtimeEvents = append(s.runtimeEvents, event)
	return event, nil
}

func (s *Store) GetTeamSoul(ctx context.Context, orgID, teamID string) (store.TeamSoul, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	soul, ok := s.teamSouls[teamSoulKey(orgID, teamID)]
	if !ok {
		return store.TeamSoul{}, store.ErrNotFound
	}
	return soul, nil
}

func (s *Store) UpsertTeamSoul(ctx context.Context, soul store.TeamSoul) (store.TeamSoul, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if soul.OrgID == "" || soul.TeamID == "" || soul.Content == "" {
		return store.TeamSoul{}, fmt.Errorf("org_id, team_id and content are required")
	}
	key := teamSoulKey(soul.OrgID, soul.TeamID)
	existing, ok := s.teamSouls[key]
	if ok {
		soul.Version = existing.Version + 1
	} else {
		soul.Version = 1
	}
	sum := sha256.Sum256([]byte(soul.Content))
	soul.ChecksumSHA256 = hex.EncodeToString(sum[:])
	soul.UpdatedAt = time.Now().UTC().Format(time.RFC3339)
	s.teamSouls[key] = soul
	return soul, nil
}

func (s *Store) nextMemoryID() string {
	s.memoryCounter++
	return fmt.Sprintf("mem-%d", s.memoryCounter)
}

func teamSoulKey(orgID, teamID string) string {
	return orgID + "\x00" + teamID
}

func (s *Store) nextReviewID() string {
	s.reviewCounter++
	return fmt.Sprintf("review-%d", s.reviewCounter)
}

func (s *Store) matchMemories(limit int, predicate func(store.MemoryItem) bool) []store.MemoryItem {
	out := []store.MemoryItem{}
	for _, item := range s.memories {
		if predicate(item) {
			out = append(out, item)
		}
	}
	sort.Slice(out, func(i, j int) bool { return out[i].ID < out[j].ID })
	if limit > 0 && len(out) > limit {
		return out[:limit]
	}
	return out
}

func validateMemory(item store.MemoryItem) error {
	if item.OrgID == "" {
		return fmt.Errorf("org_id is required")
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

func backupKey(orgID, memberID string) string {
	return orgID + ":" + memberID
}

func restorePreviewKey(backupID, memberID, mode string) string {
	return backupID + ":" + memberID + ":" + defaultString(mode, "merge")
}

func matchesQuery(content, query string) bool {
	return store.MatchesQuery(content, query)
}

func cloneMemoryItems(items []store.MemoryItem) []store.MemoryItem {
	out := make([]store.MemoryItem, len(items))
	copy(out, items)
	return out
}

func cloneMap(in map[string]any) map[string]any {
	if in == nil {
		return nil
	}
	out := make(map[string]any, len(in))
	for key, value := range in {
		out[key] = value
	}
	return out
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

func toolRuleKey(orgID, toolName, riskLevel string) string {
	return orgID + ":" + toolName + ":" + riskLevel
}
