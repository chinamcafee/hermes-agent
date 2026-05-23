package httpapi_test

import (
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"hermes-agent/team_cloud_go/internal/config"
	"hermes-agent/team_cloud_go/internal/httpapi"
	"hermes-agent/team_cloud_go/internal/store/memory"
)

func newDashboardServer(t *testing.T) http.Handler {
	t.Helper()
	dashboardDir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dashboardDir, "index.html"), []byte("<!doctype html><title>Hermes Team Cloud Dashboard</title><main id=\"root\"></main>"), 0o644); err != nil {
		t.Fatalf("write dashboard index: %v", err)
	}
	if err := os.MkdirAll(filepath.Join(dashboardDir, "assets"), 0o755); err != nil {
		t.Fatalf("mkdir dashboard assets: %v", err)
	}
	if err := os.WriteFile(filepath.Join(dashboardDir, "assets", "app.js"), []byte("window.__dashboard_loaded = true;"), 0o644); err != nil {
		t.Fatalf("write dashboard asset: %v", err)
	}
	server, err := httpapi.NewServer(config.Config{
		ServiceName:      "team-cloud-go",
		ServiceToken:     "team-token",
		DashboardEnabled: true,
		DashboardDir:     dashboardDir,
	}, memory.New())
	if err != nil {
		t.Fatalf("NewServer() error = %v", err)
	}
	return server
}

func TestDashboardStaticRootRedirectsToSlash(t *testing.T) {
	handler := newDashboardServer(t)
	req := httptest.NewRequest(http.MethodGet, "/dashboard", nil)
	rec := httptest.NewRecorder()

	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusPermanentRedirect {
		t.Fatalf("dashboard redirect status = %d body=%s", rec.Code, rec.Body.String())
	}
	if got := rec.Header().Get("Location"); got != "/dashboard/" {
		t.Fatalf("dashboard redirect Location = %q", got)
	}
}

func TestDashboardStaticServesIndexAssetsAndRouteFallback(t *testing.T) {
	handler := newDashboardServer(t)

	index := httptest.NewRecorder()
	handler.ServeHTTP(index, httptest.NewRequest(http.MethodGet, "/dashboard/", nil))
	if index.Code != http.StatusOK {
		t.Fatalf("dashboard index status = %d body=%s", index.Code, index.Body.String())
	}
	if contentType := index.Header().Get("Content-Type"); !strings.Contains(contentType, "text/html") {
		t.Fatalf("dashboard index content-type = %q", contentType)
	}
	if !strings.Contains(index.Body.String(), "Hermes Team Cloud Dashboard") {
		t.Fatalf("dashboard index body = %s", index.Body.String())
	}

	asset := httptest.NewRecorder()
	handler.ServeHTTP(asset, httptest.NewRequest(http.MethodGet, "/dashboard/assets/app.js", nil))
	if asset.Code != http.StatusOK {
		t.Fatalf("dashboard asset status = %d body=%s", asset.Code, asset.Body.String())
	}
	if !strings.Contains(asset.Body.String(), "__dashboard_loaded") {
		t.Fatalf("dashboard asset body = %s", asset.Body.String())
	}

	fallback := httptest.NewRecorder()
	handler.ServeHTTP(fallback, httptest.NewRequest(http.MethodGet, "/dashboard/settings/bootstrap", nil))
	if fallback.Code != http.StatusOK {
		t.Fatalf("dashboard fallback status = %d body=%s", fallback.Code, fallback.Body.String())
	}
	if !strings.Contains(fallback.Body.String(), "Hermes Team Cloud Dashboard") {
		t.Fatalf("dashboard fallback body = %s", fallback.Body.String())
	}
}

func TestDashboardStaticCanBeDisabled(t *testing.T) {
	server, err := httpapi.NewServer(config.Config{
		ServiceName:      "team-cloud-go",
		ServiceToken:     "team-token",
		DashboardEnabled: false,
		DashboardDir:     t.TempDir(),
	}, memory.New())
	if err != nil {
		t.Fatalf("NewServer() error = %v", err)
	}

	rec := httptest.NewRecorder()
	server.ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/dashboard/", nil))
	if rec.Code != http.StatusNotFound {
		t.Fatalf("disabled dashboard status = %d body=%s", rec.Code, rec.Body.String())
	}
}
