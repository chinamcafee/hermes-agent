package config

import "testing"

func TestFromEnvLoadsPostgresAndMigrationSettings(t *testing.T) {
	t.Setenv("TEAM_CLOUD_SERVICE_NAME", "hermes-team-cloud")
	t.Setenv("TEAM_CLOUD_DATABASE_URL", "postgres://hermes:secret@postgres:5432/team_cloud?sslmode=disable")
	t.Setenv("TEAM_CLOUD_REDIS_ADDR", "redis:6379")
	t.Setenv("TEAM_CLOUD_REDIS_PASSWORD", "redis-secret")
	t.Setenv("TEAM_CLOUD_REDIS_DB", "2")
	t.Setenv("TEAM_CLOUD_SESSION_TTL_SECONDS", "7200")
	t.Setenv("TEAM_CLOUD_AUTO_MIGRATE", "false")
	t.Setenv("TEAM_CLOUD_BIND_ADDR", ":9090")
	t.Setenv("TEAM_CLOUD_CASDOOR_ISSUER", "https://casdoor.example")
	t.Setenv("TEAM_CLOUD_CASDOOR_AUDIENCE", "hermes-team-cloud")
	t.Setenv("TEAM_CLOUD_CASDOOR_JWKS_URL", "https://casdoor.example/.well-known/jwks")
	t.Setenv("TEAM_CLOUD_AUTHZ_MODE", "spicedb_http")
	t.Setenv("TEAM_CLOUD_AUTHZ_ENDPOINT", "http://spicedb:8443")
	t.Setenv("TEAM_CLOUD_AUTHZ_TOKEN", "spicedb-token")
	t.Setenv("TEAM_CLOUD_BACKUP_OBJECT_MODE", "s3")
	t.Setenv("TEAM_CLOUD_BACKUP_S3_ENDPOINT", "http://minio:9000")
	t.Setenv("TEAM_CLOUD_BACKUP_S3_BUCKET", "personal-backups")
	t.Setenv("TEAM_CLOUD_BACKUP_S3_REGION", "us-east-1")
	t.Setenv("TEAM_CLOUD_BACKUP_S3_ACCESS_KEY_ID", "minio")
	t.Setenv("TEAM_CLOUD_BACKUP_S3_SECRET_ACCESS_KEY", "secret")
	t.Setenv("TEAM_CLOUD_BACKUP_ENCRYPTION_KEY", "backup-key")
	t.Setenv("TEAM_CLOUD_BACKUP_SCHEDULER_ENABLED", "true")
	t.Setenv("TEAM_CLOUD_BACKUP_SCHEDULER_INTERVAL_SECONDS", "60")
	t.Setenv("TEAM_CLOUD_DASHBOARD_ENABLED", "false")
	t.Setenv("TEAM_CLOUD_DASHBOARD_DIR", "/srv/team-cloud-go/dashboard")

	cfg := FromEnv()

	if cfg.ServiceName != "hermes-team-cloud" {
		t.Fatalf("ServiceName = %q", cfg.ServiceName)
	}
	if cfg.DatabaseURL == "" {
		t.Fatal("DatabaseURL was not loaded")
	}
	if cfg.RedisAddr != "redis:6379" || cfg.RedisPassword != "redis-secret" || cfg.RedisDB != 2 || cfg.SessionTTLSeconds != 7200 {
		t.Fatalf("redis/session config not loaded: %#v", cfg)
	}
	if cfg.AutoMigrate {
		t.Fatal("AutoMigrate should be false when TEAM_CLOUD_AUTO_MIGRATE=false")
	}
	if cfg.BindAddr != ":9090" {
		t.Fatalf("BindAddr = %q", cfg.BindAddr)
	}
	if cfg.CasdoorIssuer == "" || cfg.CasdoorAudience == "" || cfg.CasdoorJWKSURL == "" {
		t.Fatalf("casdoor config not loaded: %#v", cfg)
	}
	if cfg.AuthzMode != "spicedb_http" || cfg.AuthzEndpoint == "" || cfg.AuthzToken == "" {
		t.Fatalf("authz config not loaded: %#v", cfg)
	}
	if cfg.BackupObjectMode != "s3" || cfg.BackupS3Endpoint == "" || cfg.BackupS3Bucket == "" || cfg.BackupEncryptionKey == "" {
		t.Fatalf("backup object config not loaded: %#v", cfg)
	}
	if !cfg.BackupSchedulerEnabled || cfg.BackupSchedulerIntervalSeconds != 60 {
		t.Fatalf("backup scheduler config not loaded: %#v", cfg)
	}
	if cfg.DashboardEnabled || cfg.DashboardDir != "/srv/team-cloud-go/dashboard" {
		t.Fatalf("dashboard config not loaded: %#v", cfg)
	}
}
