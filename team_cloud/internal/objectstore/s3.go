package objectstore

import (
	"bytes"
	"context"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"time"
)

type ObjectStore interface {
	Ping(ctx context.Context) error
	Put(ctx context.Context, key string, payload []byte, contentType string) error
	Get(ctx context.Context, key string) ([]byte, error)
}

type S3Config struct {
	Endpoint        string
	Bucket          string
	Region          string
	AccessKeyID     string
	SecretAccessKey string
}

type S3 struct {
	endpoint        string
	bucket          string
	region          string
	accessKeyID     string
	secretAccessKey string
	client          *http.Client
}

func NewS3(cfg S3Config) (*S3, error) {
	endpoint := strings.TrimRight(strings.TrimSpace(cfg.Endpoint), "/")
	if endpoint == "" || cfg.Bucket == "" || cfg.AccessKeyID == "" || cfg.SecretAccessKey == "" {
		return nil, fmt.Errorf("s3 endpoint, bucket, access key, and secret key are required")
	}
	parsed, err := url.Parse(endpoint)
	if err != nil || parsed.Scheme == "" || parsed.Host == "" {
		return nil, fmt.Errorf("invalid s3 endpoint %q", cfg.Endpoint)
	}
	region := cfg.Region
	if region == "" {
		region = "us-east-1"
	}
	return &S3{
		endpoint:        endpoint,
		bucket:          strings.Trim(cfg.Bucket, "/"),
		region:          region,
		accessKeyID:     cfg.AccessKeyID,
		secretAccessKey: cfg.SecretAccessKey,
		client:          &http.Client{Timeout: 10 * time.Second},
	}, nil
}

func (s *S3) Ping(ctx context.Context) error {
	req, err := http.NewRequestWithContext(ctx, http.MethodHead, s.endpoint+"/"+s.bucket, nil)
	if err != nil {
		return err
	}
	s.sign(req, nil, time.Now().UTC())
	resp, err := s.client.Do(req)
	if err != nil {
		return fmt.Errorf("backup_object_store_ping: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return fmt.Errorf("backup_object_store_status_%d", resp.StatusCode)
	}
	return nil
}

func (s *S3) Put(ctx context.Context, key string, payload []byte, contentType string) error {
	req, err := http.NewRequestWithContext(ctx, http.MethodPut, s.endpoint+"/"+s.bucket+"/"+strings.TrimLeft(key, "/"), bytes.NewReader(payload))
	if err != nil {
		return err
	}
	if contentType != "" {
		req.Header.Set("Content-Type", contentType)
	}
	s.sign(req, payload, time.Now().UTC())
	resp, err := s.client.Do(req)
	if err != nil {
		return fmt.Errorf("backup_object_put: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		detail, _ := io.ReadAll(io.LimitReader(resp.Body, 2048))
		if len(detail) > 0 {
			return fmt.Errorf("backup_object_put_status_%d: %s", resp.StatusCode, strings.TrimSpace(string(detail)))
		}
		return fmt.Errorf("backup_object_put_status_%d", resp.StatusCode)
	}
	return nil
}

func (s *S3) Get(ctx context.Context, key string) ([]byte, error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, s.endpoint+"/"+s.bucket+"/"+strings.TrimLeft(key, "/"), nil)
	if err != nil {
		return nil, err
	}
	s.sign(req, nil, time.Now().UTC())
	resp, err := s.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("backup_object_get: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		detail, _ := io.ReadAll(io.LimitReader(resp.Body, 2048))
		if len(detail) > 0 {
			return nil, fmt.Errorf("backup_object_get_status_%d: %s", resp.StatusCode, strings.TrimSpace(string(detail)))
		}
		return nil, fmt.Errorf("backup_object_get_status_%d", resp.StatusCode)
	}
	return io.ReadAll(resp.Body)
}

func (s *S3) sign(req *http.Request, payload []byte, now time.Time) {
	payloadHashBytes := sha256.Sum256(payload)
	payloadHash := hex.EncodeToString(payloadHashBytes[:])
	amzDate := now.Format("20060102T150405Z")
	dateStamp := now.Format("20060102")
	req.Header.Set("X-Amz-Date", amzDate)
	req.Header.Set("X-Amz-Content-Sha256", payloadHash)
	req.Header.Set("Host", req.URL.Host)

	signedHeaders := "host;x-amz-content-sha256;x-amz-date"
	canonicalHeaders := "host:" + req.URL.Host + "\n" +
		"x-amz-content-sha256:" + payloadHash + "\n" +
		"x-amz-date:" + amzDate + "\n"
	canonicalRequest := strings.Join([]string{
		req.Method,
		req.URL.EscapedPath(),
		req.URL.RawQuery,
		canonicalHeaders,
		signedHeaders,
		payloadHash,
	}, "\n")
	credentialScope := dateStamp + "/" + s.region + "/s3/aws4_request"
	canonicalHash := sha256.Sum256([]byte(canonicalRequest))
	stringToSign := "AWS4-HMAC-SHA256\n" + amzDate + "\n" + credentialScope + "\n" + hex.EncodeToString(canonicalHash[:])
	signature := hex.EncodeToString(hmacSHA256(signingKey(s.secretAccessKey, dateStamp, s.region), []byte(stringToSign)))
	req.Header.Set("Authorization", "AWS4-HMAC-SHA256 Credential="+s.accessKeyID+"/"+credentialScope+", SignedHeaders="+signedHeaders+", Signature="+signature)
}

func signingKey(secret, dateStamp, region string) []byte {
	kDate := hmacSHA256([]byte("AWS4"+secret), []byte(dateStamp))
	kRegion := hmacSHA256(kDate, []byte(region))
	kService := hmacSHA256(kRegion, []byte("s3"))
	return hmacSHA256(kService, []byte("aws4_request"))
}

func hmacSHA256(key, data []byte) []byte {
	mac := hmac.New(sha256.New, key)
	mac.Write(data)
	return mac.Sum(nil)
}
