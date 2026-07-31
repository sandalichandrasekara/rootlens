package storage

import (
	"math"
	"sync"
	"time"

	"github.com/sandalichandrasekara/rootlens/pkg/types"
)

// Store holds in-memory data for the dashboard
type Store struct {
	mu             sync.RWMutex
	currentMetrics *MetricsSnapshot
	rcaHistory     []types.EnhancedRCAResult
	maxHistorySize int
}

// MetricsSnapshot represents current system state
type MetricsSnapshot struct {
	Timestamp       time.Time `json:"timestamp"`
	QueueDepth      int       `json:"queue_depth"`
	ConsumerCount   int       `json:"consumer_count"`
	PodCount        int       `json:"pod_count"`
	DesiredReplicas int       `json:"desired_replicas"`
	MessageRate     float64   `json:"message_rate"`
}

// NewStore creates a new storage instance
func NewStore() *Store {
	return &Store{
		rcaHistory:     make([]types.EnhancedRCAResult, 0),
		maxHistorySize: 50,
	}
}

// UpdateMetrics updates current metrics snapshot
func (s *Store) UpdateMetrics(metrics *MetricsSnapshot) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.currentMetrics = metrics
}

// GetMetrics returns current metrics
func (s *Store) GetMetrics() *MetricsSnapshot {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.currentMetrics
}

// AddRCAResult adds a new RCA result to history
func (s *Store) AddRCAResult(result types.EnhancedRCAResult) {
	s.mu.Lock()
	defer s.mu.Unlock()

	s.rcaHistory = append(s.rcaHistory, result)

	if len(s.rcaHistory) > s.maxHistorySize {
		s.rcaHistory = s.rcaHistory[1:]
	}
}

// GetLatestRCA returns a copy of the most recent RCA result.
// Returns a pointer to the copy (nil if history is empty).
func (s *Store) GetLatestRCA() *types.EnhancedRCAResult {
	s.mu.RLock()
	defer s.mu.RUnlock()

	if len(s.rcaHistory) == 0 {
		return nil
	}

	result := s.rcaHistory[len(s.rcaHistory)-1]
	return &result
}

// GetRCAHistory returns all RCA results
func (s *Store) GetRCAHistory() []types.EnhancedRCAResult {
	s.mu.RLock()
	defer s.mu.RUnlock()

	history := make([]types.EnhancedRCAResult, len(s.rcaHistory))
	copy(history, s.rcaHistory)
	return history
}

// ClearRCAHistory removes all RCA results from the store
func (s *Store) ClearRCAHistory() {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.rcaHistory = make([]types.EnhancedRCAResult, 0)
}

// GetRCAStats returns statistics about RCA results
func (s *Store) GetRCAStats() map[string]interface{} {
	s.mu.RLock()
	defer s.mu.RUnlock()

	stats := make(map[string]interface{})
	stats["total_analyses"] = len(s.rcaHistory)

	if len(s.rcaHistory) == 0 {
		return stats
	}

	coldStarts := 0
	schedulingDelays := 0
	metricLags := 0
	unknown := 0
	totalConfidence := 0.0

	for _, result := range s.rcaHistory {
		switch result.RootCause {
		case string(types.ColdStart):
			coldStarts++
		case string(types.SchedulingDelay):
			schedulingDelays++
		case string(types.MetricPropagationLag):
			metricLags++
		case string(types.Unknown):
			unknown++
		default:
			unknown++
		}
		totalConfidence += result.FinalConfidence
	}

	stats["cold_starts"] = coldStarts
	stats["scheduling_delays"] = schedulingDelays
	stats["metric_lags"] = metricLags
	stats["unknown"] = unknown
	stats["avg_confidence"] = math.Round(totalConfidence/float64(len(s.rcaHistory))*10000) / 10000

	return stats
}
