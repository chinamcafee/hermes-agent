package authn

import (
	"context"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"sync"
	"time"

	"github.com/redis/go-redis/v9"
)

var ErrSessionNotFound = errors.New("dashboard_session_not_found")

type MemorySessionStore struct {
	mu       sync.RWMutex
	sessions map[string]Session
}

func NewMemorySessionStore() *MemorySessionStore {
	return &MemorySessionStore{sessions: map[string]Session{}}
}

func (s *MemorySessionStore) Create(_ context.Context, session Session, _ time.Duration) (string, error) {
	token, err := newOpaqueToken()
	if err != nil {
		return "", err
	}
	session.Token = token
	s.mu.Lock()
	defer s.mu.Unlock()
	s.sessions[sessionKey(token)] = session
	return token, nil
}

func (s *MemorySessionStore) Get(_ context.Context, token string) (Session, error) {
	s.mu.RLock()
	session, ok := s.sessions[sessionKey(token)]
	s.mu.RUnlock()
	if !ok {
		return Session{}, ErrSessionNotFound
	}
	if !session.ExpiresAt.After(time.Now().UTC()) {
		s.mu.Lock()
		delete(s.sessions, sessionKey(token))
		s.mu.Unlock()
		return Session{}, errors.New("dashboard_session_expired")
	}
	return session, nil
}

func (s *MemorySessionStore) Ping(context.Context) error {
	return nil
}

type RedisSessionStore struct {
	client *redis.Client
	prefix string
}

func NewRedisSessionStore(client *redis.Client, prefix string) *RedisSessionStore {
	if prefix == "" {
		prefix = "team-cloud-go:session:"
	}
	return &RedisSessionStore{client: client, prefix: prefix}
}

func (s *RedisSessionStore) Create(ctx context.Context, session Session, ttl time.Duration) (string, error) {
	token, err := newOpaqueToken()
	if err != nil {
		return "", err
	}
	session.Token = token
	raw, err := json.Marshal(session)
	if err != nil {
		return "", err
	}
	if err := s.client.Set(ctx, s.prefix+sessionKey(token), raw, ttl).Err(); err != nil {
		return "", err
	}
	return token, nil
}

func (s *RedisSessionStore) Get(ctx context.Context, token string) (Session, error) {
	raw, err := s.client.Get(ctx, s.prefix+sessionKey(token)).Bytes()
	if errors.Is(err, redis.Nil) {
		return Session{}, ErrSessionNotFound
	}
	if err != nil {
		return Session{}, err
	}
	var session Session
	if err := json.Unmarshal(raw, &session); err != nil {
		return Session{}, err
	}
	session.Token = token
	return session, nil
}

func (s *RedisSessionStore) Ping(ctx context.Context) error {
	return s.client.Ping(ctx).Err()
}

func newOpaqueToken() (string, error) {
	raw := make([]byte, 32)
	if _, err := rand.Read(raw); err != nil {
		return "", err
	}
	return "hcs_" + base64.RawURLEncoding.EncodeToString(raw), nil
}

func sessionKey(token string) string {
	sum := sha256.Sum256([]byte(token))
	return hex.EncodeToString(sum[:])
}
