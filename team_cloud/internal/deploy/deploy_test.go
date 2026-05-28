package deploy

import (
	"os"
	"strings"
	"testing"
)

func TestContainerAndKubernetesAssets(t *testing.T) {
	dockerfile, err := os.ReadFile("../../Dockerfile")
	if err != nil {
		t.Fatalf("read Dockerfile: %v", err)
	}
	dockerText := string(dockerfile)
	for _, fragment := range []string{
		"node:22-alpine AS dashboard-build",
		"npm ci",
		"npm run build",
		"golang:1.24",
		"team-cloud-server",
		"/usr/share/team-cloud-go/dashboard",
		"USER nonroot",
	} {
		if !strings.Contains(dockerText, fragment) {
			t.Fatalf("Dockerfile missing %q", fragment)
		}
	}

	manifest, err := os.ReadFile("../../deploy/kubernetes/team-cloud-go.yaml")
	if err != nil {
		t.Fatalf("read Kubernetes manifest: %v", err)
	}
	manifestText := string(manifest)
	if strings.Contains(manifestText, "TEAM_CLOUD_SERVICE_TOKEN") {
		t.Fatalf("Kubernetes manifest must not contain removed service token settings")
	}
	for _, fragment := range []string{
		"kind: Deployment",
		"kind: ConfigMap",
		"hermes-team-cloud-go-authz-schema",
		"/v1/schema/write",
		"definition organization",
		"permission read_team = read",
		"TEAM_CLOUD_DATABASE_URL",
		"TEAM_CLOUD_REDIS_ADDR",
		"TEAM_CLOUD_REDIS_PASSWORD",
		"TEAM_CLOUD_REDIS_DB",
		"TEAM_CLOUD_SESSION_TTL_SECONDS",
		"TEAM_CLOUD_CASDOOR_ISSUER",
		"TEAM_CLOUD_CASDOOR_AUDIENCE",
		"TEAM_CLOUD_CASDOOR_JWKS_URL",
		"TEAM_CLOUD_AUTHZ_MODE",
		"TEAM_CLOUD_AUTHZ_ENDPOINT",
		"TEAM_CLOUD_AUTHZ_TOKEN",
		"TEAM_CLOUD_BACKUP_OBJECT_MODE",
		"TEAM_CLOUD_BACKUP_S3_ENDPOINT",
		"TEAM_CLOUD_BACKUP_S3_BUCKET",
		"TEAM_CLOUD_BACKUP_S3_ACCESS_KEY_ID",
		"TEAM_CLOUD_BACKUP_S3_SECRET_ACCESS_KEY",
		"TEAM_CLOUD_BACKUP_ENCRYPTION_KEY",
		"TEAM_CLOUD_BACKUP_SCHEDULER_ENABLED",
		"TEAM_CLOUD_BACKUP_SCHEDULER_INTERVAL_SECONDS",
		"TEAM_CLOUD_DASHBOARD_DIR",
		"/readyz",
		"command:\n            - redis-server",
		"runAsUser: 65532",
		"runAsGroup: 65532",
		"readOnlyRootFilesystem: true",
	} {
		if !strings.Contains(manifestText, fragment) {
			t.Fatalf("Kubernetes manifest missing %q", fragment)
		}
	}
}
