package authn

import (
	"context"
	"crypto"
	"crypto/rsa"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"math/big"
	"net/http"
	"strings"
	"sync"
	"time"

	"hermes-agent/team_cloud/internal/config"
)

type Principal struct {
	Subject  string
	Email    string
	OrgID    string
	MemberID string
	Role     string
	Method   string
}

type Session struct {
	Token     string    `json:"-"`
	Subject   string    `json:"sub"`
	Email     string    `json:"email,omitempty"`
	OrgID     string    `json:"org_id"`
	MemberID  string    `json:"member_id"`
	Role      string    `json:"role"`
	ExpiresAt time.Time `json:"expires_at"`
}

type SessionStore interface {
	Create(ctx context.Context, session Session, ttl time.Duration) (string, error)
	Get(ctx context.Context, token string) (Session, error)
	Ping(ctx context.Context) error
}

type Authenticator struct {
	issuer   string
	audience string
	jwksURL  string
	sessions SessionStore
	client   *http.Client
	mu       sync.RWMutex
	keys     map[string]*rsa.PublicKey
}

func New(cfg config.Config, sessions SessionStore) *Authenticator {
	if sessions == nil {
		sessions = NewMemorySessionStore()
	}
	return &Authenticator{
		issuer:   cfg.CasdoorIssuer,
		audience: cfg.CasdoorAudience,
		jwksURL:  cfg.CasdoorJWKSURL,
		sessions: sessions,
		client:   &http.Client{Timeout: 5 * time.Second},
		keys:     map[string]*rsa.PublicKey{},
	}
}

func (a *Authenticator) Authenticate(ctx context.Context, r *http.Request) (Principal, error) {
	authHeader := r.Header.Get("Authorization")
	bearer := strings.TrimPrefix(authHeader, "Bearer ")
	if bearer == "" || bearer == authHeader {
		return Principal{}, errors.New("bearer_token_required")
	}
	if !strings.Contains(bearer, ".") {
		return a.verifySessionToken(ctx, bearer)
	}
	if a.issuer == "" || a.audience == "" || a.jwksURL == "" {
		return Principal{}, errors.New("jwt_auth_not_configured")
	}
	return a.verifyJWT(ctx, bearer)
}

func (a *Authenticator) IssueSessionToken(ctx context.Context, principal Principal, now time.Time, ttl time.Duration) (string, time.Time, error) {
	if principal.Subject == "" || principal.OrgID == "" || principal.MemberID == "" || principal.Role == "" {
		return "", time.Time{}, errors.New("dashboard_session_principal_incomplete")
	}
	expiresAt := now.Add(ttl).UTC()
	token, err := a.sessions.Create(ctx, Session{
		Subject:   principal.Subject,
		Email:     principal.Email,
		OrgID:     principal.OrgID,
		MemberID:  principal.MemberID,
		Role:      principal.Role,
		ExpiresAt: expiresAt,
	}, ttl)
	if err != nil {
		return "", time.Time{}, err
	}
	return token, expiresAt, nil
}

func (a *Authenticator) verifySessionToken(ctx context.Context, token string) (Principal, error) {
	session, err := a.sessions.Get(ctx, token)
	if err != nil {
		return Principal{}, err
	}
	if session.ExpiresAt.IsZero() || !session.ExpiresAt.After(time.Now().UTC()) {
		return Principal{}, errors.New("dashboard_session_expired")
	}
	if session.Subject == "" || session.OrgID == "" || session.MemberID == "" || session.Role == "" {
		return Principal{}, errors.New("dashboard_session_incomplete")
	}
	return Principal{
		Subject:  session.Subject,
		Email:    session.Email,
		OrgID:    session.OrgID,
		MemberID: session.MemberID,
		Role:     session.Role,
		Method:   "dashboard_session",
	}, nil
}

func (a *Authenticator) verifyJWT(ctx context.Context, token string) (Principal, error) {
	parts := strings.Split(token, ".")
	if len(parts) != 3 {
		return Principal{}, errors.New("malformed_jwt")
	}
	var header map[string]any
	if err := decodeSegment(parts[0], &header); err != nil {
		return Principal{}, fmt.Errorf("decode_jwt_header: %w", err)
	}
	if header["alg"] != "RS256" {
		return Principal{}, errors.New("unsupported_jwt_alg")
	}
	kid, _ := header["kid"].(string)
	if kid == "" {
		return Principal{}, errors.New("missing_jwt_kid")
	}
	key, err := a.key(ctx, kid)
	if err != nil {
		return Principal{}, err
	}
	signingInput := parts[0] + "." + parts[1]
	signature, err := base64.RawURLEncoding.DecodeString(parts[2])
	if err != nil {
		return Principal{}, fmt.Errorf("decode_jwt_signature: %w", err)
	}
	sum := sha256.Sum256([]byte(signingInput))
	if err := rsa.VerifyPKCS1v15(key, crypto.SHA256, sum[:], signature); err != nil {
		return Principal{}, errors.New("invalid_jwt_signature")
	}

	var claims map[string]any
	if err := decodeSegment(parts[1], &claims); err != nil {
		return Principal{}, fmt.Errorf("decode_jwt_claims: %w", err)
	}
	if claims["iss"] != a.issuer {
		return Principal{}, errors.New("invalid_jwt_issuer")
	}
	if !audienceContains(claims["aud"], a.audience) {
		return Principal{}, errors.New("invalid_jwt_audience")
	}
	exp, ok := numericClaim(claims["exp"])
	if !ok || time.Unix(exp, 0).Before(time.Now().Add(-30*time.Second)) {
		return Principal{}, errors.New("jwt_expired")
	}
	return Principal{
		Subject:  stringClaim(claims, "sub"),
		Email:    stringClaim(claims, "email"),
		OrgID:    stringClaim(claims, "hermes_org_id"),
		MemberID: stringClaim(claims, "hermes_member_id"),
		Role:     stringClaim(claims, "hermes_role"),
		Method:   "casdoor_jwt",
	}, nil
}

func (a *Authenticator) key(ctx context.Context, kid string) (*rsa.PublicKey, error) {
	a.mu.RLock()
	key, ok := a.keys[kid]
	a.mu.RUnlock()
	if ok {
		return key, nil
	}
	if err := a.refreshKeys(ctx); err != nil {
		return nil, err
	}
	a.mu.RLock()
	defer a.mu.RUnlock()
	key, ok = a.keys[kid]
	if !ok {
		return nil, errors.New("jwks_key_not_found")
	}
	return key, nil
}

func (a *Authenticator) refreshKeys(ctx context.Context) error {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, a.jwksURL, nil)
	if err != nil {
		return err
	}
	resp, err := a.client.Do(req)
	if err != nil {
		return fmt.Errorf("fetch_jwks: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return fmt.Errorf("fetch_jwks_status_%d", resp.StatusCode)
	}
	var jwks struct {
		Keys []struct {
			Kty string `json:"kty"`
			Kid string `json:"kid"`
			N   string `json:"n"`
			E   string `json:"e"`
		} `json:"keys"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&jwks); err != nil {
		return fmt.Errorf("decode_jwks: %w", err)
	}
	keys := map[string]*rsa.PublicKey{}
	for _, jwk := range jwks.Keys {
		if jwk.Kty != "RSA" || jwk.Kid == "" {
			continue
		}
		nBytes, err := base64.RawURLEncoding.DecodeString(jwk.N)
		if err != nil {
			return fmt.Errorf("decode_jwk_n: %w", err)
		}
		eBytes, err := base64.RawURLEncoding.DecodeString(jwk.E)
		if err != nil {
			return fmt.Errorf("decode_jwk_e: %w", err)
		}
		e := new(big.Int).SetBytes(eBytes).Int64()
		keys[jwk.Kid] = &rsa.PublicKey{N: new(big.Int).SetBytes(nBytes), E: int(e)}
	}
	a.mu.Lock()
	a.keys = keys
	a.mu.Unlock()
	return nil
}

func decodeSegment(segment string, target any) error {
	raw, err := base64.RawURLEncoding.DecodeString(segment)
	if err != nil {
		return err
	}
	return json.Unmarshal(raw, target)
}

func audienceContains(value any, want string) bool {
	switch typed := value.(type) {
	case string:
		return typed == want
	case []any:
		for _, item := range typed {
			if s, ok := item.(string); ok && s == want {
				return true
			}
		}
	}
	return false
}

func numericClaim(value any) (int64, bool) {
	switch typed := value.(type) {
	case float64:
		return int64(typed), true
	case int64:
		return typed, true
	case json.Number:
		n, err := typed.Int64()
		return n, err == nil
	default:
		return 0, false
	}
}

func stringClaim(claims map[string]any, key string) string {
	value, _ := claims[key].(string)
	return value
}
