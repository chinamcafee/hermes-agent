package httpapi

import (
	"net/http"
	"os"
	"path/filepath"
	"strings"
)

func (s *Server) registerDashboardRoutes() {
	if !s.cfg.DashboardEnabled {
		return
	}
	s.mux.HandleFunc("/dashboard", func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/dashboard" {
			writeErrorText(w, http.StatusNotFound, "not_found")
			return
		}
		http.Redirect(w, r, "/dashboard/", http.StatusPermanentRedirect)
	})
	s.mux.HandleFunc("/dashboard/", s.dashboardStatic)
}

func (s *Server) dashboardStatic(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet && r.Method != http.MethodHead {
		writeErrorText(w, http.StatusMethodNotAllowed, "method_not_allowed")
		return
	}
	dir := strings.TrimSpace(s.cfg.DashboardDir)
	if dir == "" {
		writeErrorText(w, http.StatusNotFound, "dashboard_not_configured")
		return
	}
	root, err := filepath.Abs(dir)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err)
		return
	}
	relative := strings.TrimPrefix(r.URL.Path, "/dashboard/")
	if relative == "" {
		relative = "index.html"
	}
	candidate := filepath.Join(root, filepath.Clean(relative))
	if !strings.HasPrefix(candidate, root+string(os.PathSeparator)) && candidate != root {
		writeErrorText(w, http.StatusBadRequest, "invalid_dashboard_path")
		return
	}
	info, err := os.Stat(candidate)
	if err != nil || info.IsDir() {
		candidate = filepath.Join(root, "index.html")
		if _, indexErr := os.Stat(candidate); indexErr != nil {
			writeErrorText(w, http.StatusNotFound, "dashboard_not_found")
			return
		}
	}
	http.ServeFile(w, r, candidate)
}
