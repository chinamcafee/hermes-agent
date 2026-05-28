package config

import (
	"os"
	"strconv"
	"strings"
)

type Config struct {
	ServiceName                    string
	Version                        string
	BindAddr                       string
	DatabaseURL                    string
	RedisAddr                      string
	RedisPassword                  string
	RedisDB                        int
	SessionTTLSeconds              int
	AutoMigrate                    bool
	CasdoorIssuer                  string
	CasdoorAudience                string
	CasdoorJWKSURL                 string
	AuthzMode                      string
	AuthzEndpoint                  string
	AuthzToken                     string
	BackupObjectMode               string
	BackupS3Endpoint               string
	BackupS3Bucket                 string
	BackupS3Region                 string
	BackupS3AccessKeyID            string
	BackupS3SecretAccessKey        string
	BackupEncryptionKey            string
	BackupRequirePreviewBefore     bool
	BackupSchedulerEnabled         bool
	BackupSchedulerIntervalSeconds int
	DashboardEnabled               bool
	DashboardDir                   string
}

func FromEnv() Config {
	cfg := Config{
		ServiceName:                    getenv("TEAM_CLOUD_SERVICE_NAME", "team-cloud-go"),
		Version:                        getenv("TEAM_CLOUD_VERSION", "0.1.0"),
		BindAddr:                       getenv("TEAM_CLOUD_BIND_ADDR", ":8780"),
		DatabaseURL:                    os.Getenv("TEAM_CLOUD_DATABASE_URL"),
		RedisAddr:                      os.Getenv("TEAM_CLOUD_REDIS_ADDR"),
		RedisPassword:                  os.Getenv("TEAM_CLOUD_REDIS_PASSWORD"),
		RedisDB:                        getenvIntAllowZero("TEAM_CLOUD_REDIS_DB", 0),
		SessionTTLSeconds:              getenvInt("TEAM_CLOUD_SESSION_TTL_SECONDS", 43200),
		AutoMigrate:                    getenvBool("TEAM_CLOUD_AUTO_MIGRATE", true),
		CasdoorIssuer:                  os.Getenv("TEAM_CLOUD_CASDOOR_ISSUER"),
		CasdoorAudience:                os.Getenv("TEAM_CLOUD_CASDOOR_AUDIENCE"),
		CasdoorJWKSURL:                 os.Getenv("TEAM_CLOUD_CASDOOR_JWKS_URL"),
		AuthzMode:                      getenv("TEAM_CLOUD_AUTHZ_MODE", "local"),
		AuthzEndpoint:                  os.Getenv("TEAM_CLOUD_AUTHZ_ENDPOINT"),
		AuthzToken:                     os.Getenv("TEAM_CLOUD_AUTHZ_TOKEN"),
		BackupObjectMode:               getenv("TEAM_CLOUD_BACKUP_OBJECT_MODE", "database"),
		BackupS3Endpoint:               os.Getenv("TEAM_CLOUD_BACKUP_S3_ENDPOINT"),
		BackupS3Bucket:                 os.Getenv("TEAM_CLOUD_BACKUP_S3_BUCKET"),
		BackupS3Region:                 getenv("TEAM_CLOUD_BACKUP_S3_REGION", "us-east-1"),
		BackupS3AccessKeyID:            os.Getenv("TEAM_CLOUD_BACKUP_S3_ACCESS_KEY_ID"),
		BackupS3SecretAccessKey:        os.Getenv("TEAM_CLOUD_BACKUP_S3_SECRET_ACCESS_KEY"),
		BackupEncryptionKey:            os.Getenv("TEAM_CLOUD_BACKUP_ENCRYPTION_KEY"),
		BackupRequirePreviewBefore:     getenvBool("TEAM_CLOUD_BACKUP_REQUIRE_PREVIEW_BEFORE_RESTORE", true),
		BackupSchedulerEnabled:         getenvBool("TEAM_CLOUD_BACKUP_SCHEDULER_ENABLED", true),
		BackupSchedulerIntervalSeconds: getenvInt("TEAM_CLOUD_BACKUP_SCHEDULER_INTERVAL_SECONDS", 3600),
		DashboardEnabled:               getenvBool("TEAM_CLOUD_DASHBOARD_ENABLED", true),
		DashboardDir:                   getenv("TEAM_CLOUD_DASHBOARD_DIR", "dashboard/out"),
	}
	return cfg
}

func getenv(name, fallback string) string {
	value := os.Getenv(name)
	if value == "" {
		return fallback
	}
	return value
}

func getenvBool(name string, fallback bool) bool {
	value := strings.TrimSpace(strings.ToLower(os.Getenv(name)))
	if value == "" {
		return fallback
	}
	switch value {
	case "1", "true", "yes", "y", "on":
		return true
	case "0", "false", "no", "n", "off":
		return false
	default:
		return fallback
	}
}

func getenvInt(name string, fallback int) int {
	value := strings.TrimSpace(os.Getenv(name))
	if value == "" {
		return fallback
	}
	parsed, err := strconv.Atoi(value)
	if err != nil || parsed <= 0 {
		return fallback
	}
	return parsed
}

func getenvIntAllowZero(name string, fallback int) int {
	value := strings.TrimSpace(os.Getenv(name))
	if value == "" {
		return fallback
	}
	parsed, err := strconv.Atoi(value)
	if err != nil || parsed < 0 {
		return fallback
	}
	return parsed
}
