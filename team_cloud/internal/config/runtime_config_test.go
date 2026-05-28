package config

import "testing"

func TestFromEnvIgnoresRemovedRuntimeConfigPath(t *testing.T) {
	t.Setenv("TEAM_CLOUD_RUNTIME_CONFIG_PATH", "/tmp/removed-runtime-config.json")

	cfg := FromEnv()

	if cfg.DatabaseURL != "" {
		t.Fatalf("DatabaseURL should only come from explicit env after runtime config removal, got %q", cfg.DatabaseURL)
	}
}
