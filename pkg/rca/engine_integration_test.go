// Build integration

package rca

import (
	"context"
	"os"
	"testing"
	"time"

	"github.com/sandalichandrasekara/rootlens/pkg/ml"
	"github.com/sandalichandrasekara/rootlens/pkg/types"
	"github.com/sirupsen/logrus"
)

// Integration tests for ML Explainer

func getMLServiceURL() string {
	url := os.Getenv("ML_SERVICE_URL")
	if url == "" {
		url = "http://localhost:5000"
	}
	return url
}

func setupMLEngine(t *testing.T) *Engine {
	logger := logrus.New()
	logger.SetLevel(logrus.DebugLevel)

	mlCfg := types.MLConfig{
		Enabled:        true,
		ServiceURL:     getMLServiceURL(),
		TimeoutSeconds: 5,
	}

	rcaCfg := types.RCAConfig{
		ColdStartThresholdSeconds:  5,
		SchedulingThresholdSeconds: 3,
		MetricLagThresholdSeconds:  2,
	}

	engine := NewEngineWithML(rcaCfg, mlCfg, logger)

	// Verify ML service is available by checking explainer status
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	if engine.ExplainerRouter == nil || engine.ExplainerRouter.Client == nil {
		t.Skip("ML service not configured - skipping integration test")
	}

	_, err := engine.ExplainerRouter.Client.GetExplainersStatus(ctx)
	if err != nil {
		t.Skipf("ML service not available: %v - skipping integration test", err)
	}

	return engine
}

func TestIntegration_ColdStartWithSubCause(t *testing.T) {
	engine := setupMLEngine(t)

	now := time.Now()

	// Create pod metrics that indicate cold start (image pull scenario)
	// Cold start = ReadyTime - ContainerStartTime = 15s (DOMINANT)
	// Scheduling = ContainerStartTime - ScheduledTime = 2s
	// Metric lag = Timestamp - LastScalingEvent = 5s
	podMetrics := []types.K8sMetrics{
		{
			PodName:            "test-consumer-abc123",
			Phase:              "Running",
			ScheduledTime:      ptrTime(now.Add(-17 * time.Second)),
			ContainerStartTime: ptrTime(now.Add(-15 * time.Second)), // 2s scheduling
			ReadyTime:          ptrTime(now),                        // 15s cold start (DOMINANT)
			// Event-derived metrics for explainer
			ImagePullDuration:      45 * time.Second, // Long image pull
			ImagePullErrors:        0,
			ReadinessProbeFailures: 1,
			InitContainerDuration:  0,
		},
	}

	telemetry := &types.TelemetryData{
		Timestamp: now,
		RabbitMQMetrics: types.RabbitMQMetrics{
			QueueName:     "tasks",
			MessageCount:  500,
			ConsumerCount: 1,
			MessageRate:   50.0,
			Timestamp:     now,
		},
		KEDAMetrics: types.KEDAMetrics{
			ScalerName:       "rabbitmq-scaler",
			CurrentReplicas:  1,
			DesiredReplicas:  5,
			LastScalingEvent: now.Add(-5 * time.Second), // 5s metric lag (smaller than cold start)
			IsFromKEDA:       true,
			KEDAConfig: &types.ScaledObjectConfig{
				MinReplicas:     1,
				MaxReplicas:     10,
				PollingInterval: 30,
				CooldownPeriod:  300,
			},
		},
	}

	ctx := context.Background()
	result := engine.AnalyzeWithML(ctx, telemetry, podMetrics)

	// Verify primary classification
	if result.RootCause != "POD_COLD_START" {
		t.Errorf("Expected POD_COLD_START, got %s", result.RootCause)
	}

	// Verify sub-cause is returned
	if result.SubCause == "" {
		t.Error("Expected sub-cause to be set for cold start")
	}

	t.Logf("Root Cause: %s (confidence: %.2f)", result.RootCause, result.RuleBasedConfidence)
	t.Logf("Sub-Cause: %s (confidence: %.2f)", result.SubCause, result.SubCauseConfidence)
	t.Logf("Method Agreement: %s", result.MethodAgreement)

	// Verify sub-cause recommendations
	if len(result.SubCauseRecommendations) == 0 {
		t.Error("Expected sub-cause recommendations")
	} else {
		t.Logf("Recommendations: %v", result.SubCauseRecommendations[:1])
	}
}

func TestIntegration_SchedulingWithSubCause(t *testing.T) {
	engine := setupMLEngine(t)

	now := time.Now()

	// Create pod metrics that indicate scheduling delay
	// Scheduling = ContainerStartTime - ScheduledTime = 15s (DOMINANT)
	// Cold start = ReadyTime - ContainerStartTime = 2s
	// Metric lag = Timestamp - LastScalingEvent = 5s
	podMetrics := []types.K8sMetrics{
		{
			PodName:            "test-consumer-def456",
			Phase:              "Running",
			ScheduledTime:      ptrTime(now.Add(-17 * time.Second)),
			ContainerStartTime: ptrTime(now.Add(-2 * time.Second)), // 15s scheduling (DOMINANT)
			ReadyTime:          ptrTime(now),                       // 2s cold start
			// Scheduling failure info
			SchedulingFailureReason: "InsufficientCPU",
		},
	}

	telemetry := &types.TelemetryData{
		Timestamp: now,
		RabbitMQMetrics: types.RabbitMQMetrics{
			QueueName:     "tasks",
			MessageCount:  300,
			ConsumerCount: 1,
			MessageRate:   30.0,
			Timestamp:     now,
		},
		KEDAMetrics: types.KEDAMetrics{
			ScalerName:       "rabbitmq-scaler",
			CurrentReplicas:  1,
			DesiredReplicas:  3,
			LastScalingEvent: now.Add(-5 * time.Second), // 5s metric lag (smaller than scheduling)
			IsFromKEDA:       true,
		},
	}

	ctx := context.Background()
	result := engine.AnalyzeWithML(ctx, telemetry, podMetrics)

	// Verify primary classification
	if result.RootCause != "SCHEDULING_CONTENTION" {
		t.Errorf("Expected SCHEDULING_CONTENTION, got %s", result.RootCause)
	}

	// Verify sub-cause is returned
	if result.SubCause == "" {
		t.Error("Expected sub-cause to be set for scheduling delay")
	}

	t.Logf("Root Cause: %s (confidence: %.2f)", result.RootCause, result.RuleBasedConfidence)
	t.Logf("Sub-Cause: %s (confidence: %.2f)", result.SubCause, result.SubCauseConfidence)

	// The sub-cause should relate to insufficient resources given the failure reason
	expectedSubCauses := []string{"insufficient_resources", "resource_quota_exceeded", "taint_conflict", "node_affinity_mismatch", "pdb_violation"}
	found := false
	for _, expected := range expectedSubCauses {
		if result.SubCause == expected {
			found = true
			break
		}
	}
	if !found && result.SubCause != "undetermined" {
		t.Errorf("Unexpected sub-cause: %s", result.SubCause)
	}
}

func TestIntegration_MetricPropagationWithSubCause(t *testing.T) {
	engine := setupMLEngine(t)

	now := time.Now()

	// Create pod metrics where metric lag is dominant
	podMetrics := []types.K8sMetrics{
		{
			PodName:            "test-consumer-ghi789",
			Phase:              "Running",
			ScheduledTime:      ptrTime(now.Add(-3 * time.Second)),
			ContainerStartTime: ptrTime(now.Add(-2 * time.Second)), // 1s scheduling
			ReadyTime:          ptrTime(now.Add(-1 * time.Second)), // 1s cold start
		},
	}

	telemetry := &types.TelemetryData{
		Timestamp: now,
		RabbitMQMetrics: types.RabbitMQMetrics{
			QueueName:     "tasks",
			MessageCount:  800,
			ConsumerCount: 2,
			MessageRate:   100.0,
			Timestamp:     now,
		},
		KEDAMetrics: types.KEDAMetrics{
			ScalerName:       "rabbitmq-scaler",
			CurrentReplicas:  2,
			DesiredReplicas:  5,
			LastScalingEvent: now.Add(-90 * time.Second), // 90s ago - significant metric lag
			IsFromKEDA:       true,
			KEDAConfig: &types.ScaledObjectConfig{
				MinReplicas:     1,
				MaxReplicas:     10,
				PollingInterval: 30,
				CooldownPeriod:  300,
			},
		},
	}

	ctx := context.Background()
	result := engine.AnalyzeWithML(ctx, telemetry, podMetrics)

	// Verify primary classification
	if result.RootCause != "METRIC_PROPAGATION_LAG" {
		t.Errorf("Expected METRIC_PROPAGATION_LAG, got %s", result.RootCause)
	}

	// Verify sub-cause is returned
	if result.SubCause == "" {
		t.Error("Expected sub-cause to be set for metric propagation lag")
	}

	t.Logf("Root Cause: %s (confidence: %.2f)", result.RootCause, result.RuleBasedConfidence)
	t.Logf("Sub-Cause: %s (confidence: %.2f)", result.SubCause, result.SubCauseConfidence)

	// Valid sub-causes for metric propagation
	expectedSubCauses := []string{"metrics_server_lag", "hpa_sync_delay", "prometheus_scrape_gap", "keda_polling_delay"}
	found := false
	for _, expected := range expectedSubCauses {
		if result.SubCause == expected {
			found = true
			break
		}
	}
	if !found && result.SubCause != "undetermined" {
		t.Errorf("Unexpected sub-cause: %s", result.SubCause)
	}
}

func TestIntegration_ExplainersStatus(t *testing.T) {
	logger := logrus.New()
	client := ml.NewExplainerClient(getMLServiceURL(), 5*time.Second, logger)

	ctx := context.Background()
	status, err := client.GetExplainersStatus(ctx)
	if err != nil {
		t.Skipf("ML service not available: %v", err)
	}

	t.Logf("Explainers Status: %+v", status.Explainers)

	// Verify all explainers are loaded
	expectedExplainers := []string{"cold_start", "scheduling", "metric_propagation"}
	for _, name := range expectedExplainers {
		loaded, exists := status.Explainers[name]
		if !exists {
			t.Errorf("Explainer %s not found in status", name)
		} else if !loaded {
			t.Errorf("Explainer %s not loaded", name)
		}
	}
}
