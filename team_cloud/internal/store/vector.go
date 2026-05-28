package store

import (
	"fmt"
	"math"
	"sort"
	"strconv"
	"strings"
)

func Float64Slice(value any) []float64 {
	switch typed := value.(type) {
	case []float64:
		return append([]float64(nil), typed...)
	case []any:
		out := make([]float64, 0, len(typed))
		for _, item := range typed {
			switch n := item.(type) {
			case float64:
				out = append(out, n)
			case float32:
				out = append(out, float64(n))
			case int:
				out = append(out, float64(n))
			case jsonNumber:
				parsed, err := strconv.ParseFloat(n.String(), 64)
				if err != nil {
					return nil
				}
				out = append(out, parsed)
			default:
				return nil
			}
		}
		return out
	default:
		return nil
	}
}

type jsonNumber interface {
	String() string
}

func VectorLiteral(values []float64) string {
	if len(values) == 0 {
		return ""
	}
	parts := make([]string, len(values))
	for i, value := range values {
		parts[i] = strconv.FormatFloat(value, 'f', -1, 64)
	}
	return "[" + strings.Join(parts, ",") + "]"
}

func ParseVectorLiteral(value string) []float64 {
	value = strings.TrimSpace(value)
	value = strings.TrimPrefix(strings.TrimSuffix(value, "]"), "[")
	if value == "" {
		return nil
	}
	parts := strings.Split(value, ",")
	out := make([]float64, 0, len(parts))
	for _, part := range parts {
		parsed, err := strconv.ParseFloat(strings.TrimSpace(part), 64)
		if err != nil {
			return nil
		}
		out = append(out, parsed)
	}
	return out
}

func RankPrefetchItems(items []MemoryItem, query, projectID string, queryEmbedding []float64, limit int) []MemoryItem {
	if limit <= 0 {
		limit = 8
	}
	filtered := make([]MemoryItem, 0, len(items))
	for _, item := range items {
		if projectID != "" && item.ProjectID != "" && item.ProjectID != projectID {
			continue
		}
		filtered = append(filtered, item)
	}
	if len(queryEmbedding) > 0 {
		type scored struct {
			item  MemoryItem
			score float64
		}
		scoredItems := []scored{}
		for _, item := range filtered {
			if len(item.Embedding) != len(queryEmbedding) {
				continue
			}
			scoredItems = append(scoredItems, scored{item: item, score: CosineSimilarity(queryEmbedding, item.Embedding)})
		}
		sort.Slice(scoredItems, func(i, j int) bool {
			if math.Abs(scoredItems[i].score-scoredItems[j].score) < 1e-12 {
				return scoredItems[i].item.ID < scoredItems[j].item.ID
			}
			return scoredItems[i].score > scoredItems[j].score
		})
		out := make([]MemoryItem, 0, len(scoredItems))
		for _, item := range scoredItems {
			out = append(out, item.item)
		}
		if len(out) > limit {
			return out[:limit]
		}
		return out
	}
	out := []MemoryItem{}
	for _, item := range filtered {
		if MatchesQuery(item.Content, query) {
			out = append(out, item)
		}
	}
	sort.Slice(out, func(i, j int) bool { return out[i].ID < out[j].ID })
	if len(out) > limit {
		return out[:limit]
	}
	return out
}

func CosineSimilarity(a, b []float64) float64 {
	if len(a) == 0 || len(a) != len(b) {
		return 0
	}
	var dot, normA, normB float64
	for i := range a {
		dot += a[i] * b[i]
		normA += a[i] * a[i]
		normB += b[i] * b[i]
	}
	if normA == 0 || normB == 0 {
		return 0
	}
	return dot / (math.Sqrt(normA) * math.Sqrt(normB))
}

func MatchesQuery(content, query string) bool {
	query = strings.TrimSpace(strings.ToLower(query))
	if query == "" {
		return true
	}
	content = strings.ToLower(content)
	for _, token := range strings.Fields(query) {
		if strings.Contains(content, token) {
			return true
		}
	}
	return false
}

func ValidateEmbedding(values []float64) error {
	for _, value := range values {
		if math.IsNaN(value) || math.IsInf(value, 0) {
			return fmt.Errorf("embedding contains non-finite value")
		}
	}
	return nil
}
