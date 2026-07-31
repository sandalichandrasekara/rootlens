package rca

import (
	"testing"
	"time"

	"github.com/sandalichandrasekara/rootlens/pkg/types"
)

func TestAnalyzeNoPods(t *testing.T) {
	engine := NewEngine(types.RCAConfig{
		ColdStartThresholdSeconds:  5,
		SchedulingThresholdSeconds: 3,
		MetricLagThresholdSeconds:  2,
	})

	telemetry := &types.TelemetryData{
		Timestamp: time.Now(),
		RabbitMQMetrics: types.RabbitMQMetrics{
			MessageCount: 100,
			Timestamp:    time.Now(),
		},
		KEDAMetrics: types.KEDAMetrics{
			CurrentReplicas: 1,
			DesiredReplicas: 5,
		},
	}

	result, err := engine.Analyze(telemetry, []types.K8sMetrics{})
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if result.RootCause != types.Unknown {
		t.Errorf("expected Unknown root cause for no pods, got %s", result.RootCause)
	}
}

func TestAnalyzeColdStart(t *testing.T) {
	engine := NewEngine(types.RCAConfig{
		ColdStartThresholdSeconds:  2,
		SchedulingThresholdSeconds: 1,
		MetricLagThresholdSeconds:  1,
	})

	now := time.Now()
	// Cold start = 3s (dominant), Scheduling = 0.5s, MetricLag = 1s
	podMetrics := []types.K8sMetrics{
		{
			PodName:            "test-pod",
			Phase:              "Running",
			ScheduledTime:      ptrTime(now.Add(-4 * time.Second)),         // 4s ago
			ContainerStartTime: ptrTime(now.Add(-3500 * time.Millisecond)), // 3.5s ago (0.5s scheduling)
			ReadyTime:          ptrTime(now.Add(-500 * time.Millisecond)),  // 0.5s ago (3s cold start - dominant)
		},
	}

	telemetry := &types.TelemetryData{
		Timestamp: now,
		RabbitMQMetrics: types.RabbitMQMetrics{
			MessageCount: 100,
			Timestamp:    now,
		},
		KEDAMetrics: types.KEDAMetrics{
			CurrentReplicas:  1,
			DesiredReplicas:  5,
			LastScalingEvent: now.Add(-1 * time.Second), // 1s metric lag (smaller than cold start)
		},
	}

	result, err := engine.Analyze(telemetry, podMetrics)
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if result.RootCause != types.ColdStart {
		t.Errorf("expected ColdStart root cause, got %s", result.RootCause)
	}

	if result.Confidence < 0.6 {
		t.Errorf("expected confidence >= 0.6, got %f", result.Confidence)
	}
}

func TestAnalyzeSchedulingDelay(t *testing.T) {
	engine := NewEngine(types.RCAConfig{
		ColdStartThresholdSeconds:  2,
		SchedulingThresholdSeconds: 2,
		MetricLagThresholdSeconds:  1,
	})

	now := time.Now()
	// Scheduling = 3s (dominant), Cold start = 0.5s, MetricLag = 1s
	podMetrics := []types.K8sMetrics{
		{
			PodName:            "test-pod",
			Phase:              "Running",
			ScheduledTime:      ptrTime(now.Add(-4 * time.Second)),        // 4s ago
			ContainerStartTime: ptrTime(now.Add(-1 * time.Second)),        // 1s ago (3s scheduling - dominant)
			ReadyTime:          ptrTime(now.Add(-500 * time.Millisecond)), // 0.5s ago (0.5s cold start)
		},
	}

	telemetry := &types.TelemetryData{
		Timestamp: now,
		RabbitMQMetrics: types.RabbitMQMetrics{
			MessageCount: 100,
			Timestamp:    now,
		},
		KEDAMetrics: types.KEDAMetrics{
			CurrentReplicas:  1,
			DesiredReplicas:  5,
			LastScalingEvent: now.Add(-1 * time.Second), // 1s metric lag (smaller than scheduling)
		},
	}

	result, err := engine.Analyze(telemetry, podMetrics)
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if result.RootCause != types.SchedulingDelay {
		t.Errorf("expected SchedulingDelay root cause, got %s", result.RootCause)
	}
}

func TestAnalyzeMetricLag(t *testing.T) {
	engine := NewEngine(types.RCAConfig{
		ColdStartThresholdSeconds:  1,
		SchedulingThresholdSeconds: 1,
		MetricLagThresholdSeconds:  2,
	})

	now := time.Now()
	podMetrics := []types.K8sMetrics{
		{
			PodName:            "test-pod",
			Phase:              "Running",
			ScheduledTime:      ptrTime(now.Add(-2 * time.Second)),
			ContainerStartTime: ptrTime(now.Add(-1 * time.Second)),
			ReadyTime:          ptrTime(now),
		},
	}

	telemetry := &types.TelemetryData{
		Timestamp: now,
		RabbitMQMetrics: types.RabbitMQMetrics{
			MessageCount: 100,
			Timestamp:    now,
		},
		KEDAMetrics: types.KEDAMetrics{
			CurrentReplicas:  1,
			DesiredReplicas:  5,
			LastScalingEvent: now.Add(-4 * time.Second), // 4s ago - largest delay
		},
	}

	result, err := engine.Analyze(telemetry, podMetrics)
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if result.RootCause != types.MetricPropagationLag {
		t.Errorf("expected MetricPropagationLag root cause, got %s", result.RootCause)
	}
}

// Helper function
func ptrTime(t time.Time) *time.Time {
	return &t
}
