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

	"hermes-agent/team_cloud_go/internal/store"
)

type Store struct {
	mu              sync.RWMutex
	orgs            map[string]store.Organization
	teams           map[string]store.Team
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
		teams:           map[string]store.Team{},
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

func (s *Store) CreateTeam(ctx context.Context, orgID, slug, name string) (store.Team, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if _, ok := s.orgs[orgID]; !ok {
		return store.Team{}, store.ErrNotFound
	}
	if slug == "" || name == "" {
		return store.Team{}, fmt.Errorf("slug and name are required")
	}
	team := store.Team{ID: orgID + ":" + slug, OrgID: orgID, Slug: slug, Name: name, Status: "active"}
	s.teams[team.ID] = team
	return team, nil
}

func (s *Store) ListTeams(ctx context.Context, orgID string) ([]store.Team, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	if _, ok := s.orgs[orgID]; !ok {
		return nil, store.ErrNotFound
	}
	out := []store.Team{}
	for _, team := range s.teams {
		if team.OrgID == orgID {
			out = append(out, team)
		}
	}
	sort.Slice(out, func(i, j int) bool { return out[i].ID < out[j].ID })
	return out, nil
}

func (s *Store) InviteMember(ctx context.Context, orgID, email, displayName, userID, role string) (store.Member, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if _, ok := s.orgs[orgID]; !ok {
		return store.Member{}, store.ErrNotFound
	}
	if role == "" {
		role = "member"
	}
	member := store.Member{
		ID:          orgID + ":" + userID,
		OrgID:       orgID,
		UserID:      userID,
		Email:       email,
		DisplayName: displayName,
		Role:        role,
		Status:      "invited",
	}
	s.members[member.ID] = member
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
		ID:              s.nextMemoryID(),
		OrgID:           stringValue(payload, "org_id"),
		Scope:           scope,
		SubjectMemberID: stringValue(payload, "subject_member_id"),
		TeamID:          stringValue(payload, "team_id"),
		ProjectID:       stringValue(payload, "project_id"),
		Status:          status,
		Sensitivity:     defaultString(stringValue(payload, "sensitivity"), "normal"),
		MemoryType:      defaultString(stringValue(payload, "memory_type"), "fact"),
		Content:         content,
		Embedding:       store.Float64Slice(payload["embedding"]),
		Version:         1,
	}
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
	if _, ok := payload["embedding"]; ok {
		item.Embedding = store.Float64Slice(payload["embedding"])
		if err := store.ValidateEmbedding(item.Embedding); err != nil {
			return store.MemoryItem{}, err
		}
	}
	item.Version++
	s.memories[memoryID] = item
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
	if req.IncludePersonal {
		items := s.matchMemories(0, func(item store.MemoryItem) bool {
			return item.OrgID == req.OrgID &&
				item.Scope == "personal" &&
				item.SubjectMemberID == req.MemberID &&
				item.Status == "active"
		})
		items = store.RankPrefetchItems(items, req.Query, "", req.QueryEmbedding, req.Limit)
		if len(items) > 0 {
			partitions = append(partitions, store.MemoryPartition{Scope: "personal", Items: items})
		}
	}
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

func (s *Store) RunPersonalBackup(ctx context.Context, orgID, memberID string) (store.BackupJob, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	items := []store.MemoryItem{}
	for _, item := range s.memories {
		if item.OrgID == orgID && item.Scope == "personal" && item.SubjectMemberID == memberID && item.Status == "active" {
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
		MemberID:       memberID,
		Status:         "completed",
		ObjectKey:      fmt.Sprintf("org/%s/member/%s/personal-memory/backup-%d.jsonl.enc", orgID, memberID, s.backupCounter),
		ObjectUploaded: false,
		ChecksumSHA256: hex.EncodeToString(sum[:]),
		ItemCount:      len(items),
		Manifest: map[string]any{
			"object_store": "database",
			"format":       "json",
		},
		Items:     cloneMemoryItems(items),
		CreatedAt: time.Now().UTC(),
	}
	s.backupJobs[job.ID] = job
	return job, nil
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

func (s *Store) PreviewPersonalRestore(ctx context.Context, backupID, memberID, mode string) (store.RestorePreview, error) {
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
		if item.SubjectMemberID != memberID {
			continue
		}
		if mode == "merge" && s.hasActivePersonalMemory(item.OrgID, memberID, item.Content) {
			skipCount++
		} else {
			createCount++
		}
	}
	preview := store.RestorePreview{BackupID: backupID, MemberID: memberID, CreateCount: createCount, SkipCount: skipCount, Mode: mode}
	s.restorePreviews[restorePreviewKey(preview.BackupID, preview.MemberID, preview.Mode)] = true
	return preview, nil
}

func (s *Store) ExecutePersonalRestore(ctx context.Context, backupID, memberID, mode string) (store.RestoreExecution, error) {
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
	if !s.restorePreviews[restorePreviewKey(backupID, memberID, mode)] {
		return store.RestoreExecution{}, fmt.Errorf("restore_preview_required")
	}
	switch mode {
	case "overwrite":
		s.markPersonalMemories(job.OrgID, memberID, "deleted")
	case "archive_current_then_restore":
		s.markPersonalMemories(job.OrgID, memberID, "archived")
	}
	restored := 0
	for _, item := range job.Items {
		if item.SubjectMemberID != memberID {
			continue
		}
		if mode == "merge" && s.hasActivePersonalMemory(item.OrgID, memberID, item.Content) {
			continue
		}
		restoredItem := item
		restoredItem.ID = s.nextMemoryID()
		restoredItem.Status = "active"
		restoredItem.Version = 1
		s.memories[restoredItem.ID] = restoredItem
		restored++
	}
	return store.RestoreExecution{BackupID: backupID, MemberID: memberID, Mode: mode, RestoredCount: restored, Status: "executed"}, nil
}

func (s *Store) markPersonalMemories(orgID, memberID, status string) {
	for id, item := range s.memories {
		if item.OrgID == orgID && item.Scope == "personal" && item.SubjectMemberID == memberID && item.Status == "active" {
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
	if req.DeletionScope == "personal_memory" {
		for id, item := range s.memories {
			if item.OrgID == req.OrgID && item.Scope == "personal" && item.SubjectMemberID == req.TargetMemberID {
				item.Status = "deleted"
				item.Version++
				s.memories[id] = item
			}
		}
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

func (s *Store) nextMemoryID() string {
	s.memoryCounter++
	return fmt.Sprintf("mem-%d", s.memoryCounter)
}

func (s *Store) hasActivePersonalMemory(orgID, memberID, content string) bool {
	for _, item := range s.memories {
		if item.OrgID == orgID && item.Scope == "personal" && item.SubjectMemberID == memberID && item.Status == "active" && item.Content == content {
			return true
		}
	}
	return false
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
	case "personal":
		if item.SubjectMemberID == "" || item.TeamID != "" {
			return fmt.Errorf("personal memory requires subject_member_id and no team_id")
		}
	case "team_shared":
		if item.TeamID == "" || item.SubjectMemberID != "" {
			return fmt.Errorf("team_shared memory requires team_id and no subject_member_id")
		}
	default:
		return fmt.Errorf("scope must be personal or team_shared")
	}
	return nil
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
