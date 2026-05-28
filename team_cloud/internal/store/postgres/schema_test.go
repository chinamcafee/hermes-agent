package postgres

import (
	"os"
	"strings"
	"testing"
)

func TestSchemaContainsCloudCollaborationTables(t *testing.T) {
	required := []string{
		"create table if not exists tcg_organizations",
		"create table if not exists tcg_members",
		"create table if not exists tcg_memory_items",
		"create extension if not exists vector",
		"embedding vector",
		"tcg_memory_items_embedding_hnsw_idx",
		"source_type in ('', 'auto_extracted', 'admin_created')",
		"source_member_id text not null default ''",
		"created_by_member_id text not null default ''",
		"create table if not exists tcg_memory_review_items",
		"create table if not exists tcg_memory_observations",
		"create table if not exists tcg_backup_policies",
		"create table if not exists tcg_audit_events",
		"create table if not exists tcg_relationships",
		"create table if not exists tcg_backup_jobs",
		"create table if not exists tcg_restore_previews",
		"create table if not exists tcg_org_exports",
		"create table if not exists tcg_deletion_requests",
		"create table if not exists tcg_tool_policy_rules",
		"create table if not exists tcg_cloud_sessions",
		"create table if not exists tcg_runtime_events",
		"create table if not exists tcg_team_souls",
		"scope = 'team_shared'",
	}
	normalized := strings.ToLower(SchemaSQL)
	for _, fragment := range required {
		if !strings.Contains(normalized, fragment) {
			t.Fatalf("SchemaSQL missing %q", fragment)
		}
	}
	if strings.Contains(normalized, "create table if not exists tcg_teams") {
		t.Fatal("SchemaSQL must not create a first-version workgroup table")
	}
	if !strings.Contains(normalized, "drop table if exists tcg_teams cascade") {
		t.Fatal("SchemaSQL should destructively remove the retired workgroup table")
	}
}

func TestPrefetchUsesPgvectorSQLWhenQueryEmbeddingIsProvided(t *testing.T) {
	source, err := os.ReadFile("store.go")
	if err != nil {
		t.Fatalf("read postgres store source: %v", err)
	}
	text := string(source)
	required := []string{
		"len(req.QueryEmbedding) > 0",
		"embedding <=>",
		"::vector",
		"vectorActiveMemories",
	}
	for _, fragment := range required {
		if !strings.Contains(text, fragment) {
			t.Fatalf("postgres Prefetch should use pgvector SQL path; missing %q", fragment)
		}
	}
}
