package httpapi_test

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"hermes-agent/team_cloud/internal/config"
)

func TestBootstrapRuntimeConfigEndpointIsRemoved(t *testing.T) {
	handler := newBootstrapV2Server(t, config.Config{
		ServiceName:      "team-cloud-go",
		DashboardEnabled: true,
		DashboardDir:     "dashboard/out",
	})
	rec := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodPut, "/v1/bootstrap/runtime-config", strings.NewReader(`{}`))
	req.Header.Set("Content-Type", "application/json")

	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusNotFound {
		t.Fatalf("runtime config status = %d body=%s", rec.Code, rec.Body.String())
	}
}
