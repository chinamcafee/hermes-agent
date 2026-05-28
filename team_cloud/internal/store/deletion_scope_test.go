package store

import "testing"

func TestNormalizeDeletionScopeAllowlist(t *testing.T) {
	tests := []struct {
		name string
		in   string
		want string
	}{
		{name: "team memory", in: "team_memory", want: "team_memory"},
		{name: "team memory spaced uppercase", in: " TEAM_MEMORY ", want: "team_memory"},
		{name: "team soul", in: "team_soul", want: "team_soul"},
		{name: "team soul spaced uppercase", in: " TEAM_SOUL ", want: "team_soul"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := NormalizeDeletionScope(tt.in)
			if err != nil {
				t.Fatalf("NormalizeDeletionScope(%q) error = %v", tt.in, err)
			}
			if got != tt.want {
				t.Fatalf("NormalizeDeletionScope(%q) = %q, want %q", tt.in, got, tt.want)
			}
		})
	}
}

func TestNormalizeDeletionScopeRejectsPersonalAndUnknown(t *testing.T) {
	for _, scope := range []string{"personal_memory", " PERSONAL_MEMORY ", "arbitrary_scope", "", " "} {
		t.Run(scope, func(t *testing.T) {
			if got, err := NormalizeDeletionScope(scope); err == nil || got != "" {
				t.Fatalf("NormalizeDeletionScope(%q) = %q, %v; want unsupported_deletion_scope", scope, got, err)
			}
		})
	}
}
