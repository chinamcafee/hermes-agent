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

	"hermes-agent/team_cloud_go/internal/config"
)

type Principal struct {
	Subject  string
	Email    string
	OrgID    string
	MemberID string
	Method   string
}

type Authenticator struct {
	serviceToken string
	issuer       string
	audience     string
	jwksURL      string
	client       *http.Client
	mu           sync.RWMutex
	keys         map[string]*rsa.PublicKey
}

func New(cfg config.Config) *Authenticator {
	return &Authenticator{
		serviceToken: cfg.ServiceToken,
		issuer:       cfg.CasdoorIssuer,
		audience:     cfg.CasdoorAudience,
		jwksURL:      cfg.CasdoorJWKSURL,
		client:       &http.Client{Timeout: 5 * time.Second},
		keys:         map[string]*rsa.PublicKey{},
	}
}

func (a *Authenticator) Authenticate(ctx context.Context, r *http.Request) (Principal, error) {
	authHeader := r.Header.Get("Authorization")
	bearer := strings.TrimPrefix(authHeader, "Bearer ")
	headerToken := r.Header.Get("X-Hermes-Team-Cloud-Token")
	if a.serviceToken != "" && (bearer == a.serviceToken || headerToken == a.serviceToken) {
		return Principal{Subject: "service:team-cloud", Method: "service_token"}, nil
	}
	if bearer == "" || bearer == authHeader {
		return Principal{}, errors.New("invalid_service_token")
	}
	if a.issuer == "" || a.audience == "" || a.jwksURL == "" {
		return Principal{}, errors.New("jwt_auth_not_configured")
	}
	return a.verifyJWT(ctx, bearer)
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
