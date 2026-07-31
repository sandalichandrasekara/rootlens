package ml

import (
	"context"
	"fmt"

	"github.com/sandalichandrasekara/rootlens/pkg/types"
	"github.com/sirupsen/logrus"
)

// ExplainerRouter routes RCA results to the appropriate sub-cause explainer
type ExplainerRouter struct {
	Client *ExplainerClient
	Logger *logrus.Logger
}

// NewExplainerRouter creates a new explainer router
func NewExplainerRouter(client *ExplainerClient, logger *logrus.Logger) *ExplainerRouter {
	return &ExplainerRouter{
		Client: client,
		Logger: logger,
	}
}

// Explain routes to the appropriate explainer based on root cause category
func (r *ExplainerRouter) Explain(ctx context.Context, rootCause types.RootCauseType, metrics map[string]interface{}) (*SubCauseResult, error) {
	switch rootCause {
	case types.ColdStart:
		r.Logger.Debug("Routing to Cold Start explainer")
		return r.Client.ExplainColdStart(ctx, metrics)

	case types.SchedulingDelay:
		r.Logger.Debug("Routing to Scheduling explainer")
		return r.Client.ExplainScheduling(ctx, metrics)

	case types.MetricPropagationLag:
		r.Logger.Debug("Routing to Metric Propagation explainer")
		return r.Client.ExplainMetricPropagation(ctx, metrics)

	case types.Unknown:
		r.Logger.Debug("Root cause is UNKNOWN - no explainer available")
		return nil, nil // No explanation for unknown root cause

	default:
		r.Logger.Warnf("Unknown root cause type: %s", rootCause)
		return nil, fmt.Errorf("no explainer for root cause: %s", rootCause)
	}
}

// ExplainWithFallback attempts explanation with graceful fallback.
// Returns SubCause "ml_unavailable" when the ML service cannot be reached,
// and "undetermined" when the service responds but confidence is too low (<0.5).
func (r *ExplainerRouter) ExplainWithFallback(ctx context.Context, rootCause types.RootCauseType, metrics map[string]interface{}) *SubCauseResult {
	if rootCause == types.Unknown {
		return nil
	}

	result, err := r.Explain(ctx, rootCause, metrics)
	if err != nil {
		// ML service unreachable or returned an error — caller will set "ml_unavailable"
		r.Logger.Warnf("Explainer failed for %s: %v", rootCause, err)
		return &SubCauseResult{
			Success:    false,
			SubCause:   "ml_unavailable",
			Confidence: 0,
			Error:      err.Error(),
		}
	}

	// Check confidence threshold - if too low, mark as undetermined
	if result != nil && result.Confidence < 0.5 {
		r.Logger.Infof("Low confidence (%.2f) for %s sub-cause, marking as undetermined", result.Confidence, rootCause)
		result.SubCause = "undetermined"
	}

	return result
}

// PrepareMetricsForColdStart converts K8sMetrics to the format expected by cold start explainer
func PrepareMetricsForColdStart(k8sMetrics *types.K8sMetrics) map[string]interface{} {
	metrics := make(map[string]interface{})

	metrics["image_pull_duration_seconds"] = k8sMetrics.ImagePullDuration.Seconds()
	metrics["image_pull_errors"] = float64(k8sMetrics.ImagePullErrors)
	metrics["image_not_found"] = k8sMetrics.ImageNotFound
	metrics["image_pull_backoff"] = k8sMetrics.ImagePullBackOff
	metrics["image_error_message"] = k8sMetrics.ImageErrorMessage

	metrics["init_container_duration_seconds"] = k8sMetrics.InitContainerDuration.Seconds()
	metrics["readiness_probe_failures"] = float64(k8sMetrics.ReadinessProbeFailures)

	var containerCreateDuration float64
	if k8sMetrics.ContainerStartTime != nil && k8sMetrics.ScheduledTime != nil {
		containerCreateDuration = k8sMetrics.ContainerStartTime.Sub(*k8sMetrics.ScheduledTime).Seconds()
		// Subtract init container time if present
		containerCreateDuration -= k8sMetrics.InitContainerDuration.Seconds()
		if containerCreateDuration < 0 {
			containerCreateDuration = 0
		}
	}
	metrics["container_create_duration_seconds"] = containerCreateDuration

	var totalColdStart float64
	if k8sMetrics.ReadyTime != nil && k8sMetrics.ScheduledTime != nil {
		totalColdStart = k8sMetrics.ReadyTime.Sub(*k8sMetrics.ScheduledTime).Seconds()
	}
	metrics["total_cold_start_seconds"] = totalColdStart

	metrics["is_first_pull_on_node"] = 0.0
	metrics["image_size_estimate_mb"] = 100.0
	metrics["init_container_count"] = 0.0
	metrics["readiness_probe_period_seconds"] = 10.0
	metrics["readiness_probe_timeout_seconds"] = 1.0

	return metrics
}

// PrepareMetricsForScheduling converts K8sMetrics to the format expected by scheduling explainer
func PrepareMetricsForScheduling(k8sMetrics *types.K8sMetrics, telemetry *types.TelemetryData) map[string]interface{} {
	metrics := make(map[string]interface{})

	var schedulingDuration float64
	if k8sMetrics.ScheduledTime != nil && k8sMetrics.ContainerStartTime != nil {
		d := k8sMetrics.ContainerStartTime.Sub(*k8sMetrics.ScheduledTime).Seconds()
		if d > 0 {
			schedulingDuration = d
		}
	}
	metrics["scheduling_duration_seconds"] = schedulingDuration
	metrics["scheduling_attempts"] = 1.0
	metrics["has_node_selector"] = 0.0
	metrics["has_node_affinity"] = 0.0
	metrics["has_tolerations"] = 0.0
	metrics["pod_priority"] = 0.0
	metrics["cpu_request_millicores"] = 100.0
	metrics["memory_request_mb"] = 128.0
	metrics["node_count_in_cluster"] = 3.0
	metrics["available_cpu_millicores"] = 4000.0
	metrics["scheduling_failure_reason"] = k8sMetrics.SchedulingFailureReason

	return metrics
}

// PrepareMetricsForMetricPropagation converts telemetry to format expected by metric propagation explainer
func PrepareMetricsForMetricPropagation(telemetry *types.TelemetryData, metricLagSeconds float64) map[string]interface{} {
	metrics := make(map[string]interface{})

	metrics["metric_lag_seconds"] = metricLagSeconds

	if telemetry.KEDAMetrics.KEDAConfig != nil {
		metrics["keda_polling_interval_seconds"] = float64(telemetry.KEDAMetrics.KEDAConfig.PollingInterval)
		metrics["keda_cooldown_period_seconds"] = float64(telemetry.KEDAMetrics.KEDAConfig.CooldownPeriod)
		metrics["trigger_threshold"] = float64(telemetry.KEDAMetrics.KEDAConfig.TriggerThreshold)
	} else {
		metrics["keda_polling_interval_seconds"] = 30.0
		metrics["keda_cooldown_period_seconds"] = 300.0
		metrics["trigger_threshold"] = 100.0
	}

	metrics["current_replicas"] = float64(telemetry.KEDAMetrics.CurrentReplicas)
	metrics["desired_replicas"] = float64(telemetry.KEDAMetrics.DesiredReplicas)
	metrics["queue_depth_at_lag"] = float64(telemetry.RabbitMQMetrics.MessageCount)

	if !telemetry.KEDAMetrics.LastScalingEvent.IsZero() {
		metrics["time_since_last_scale_seconds"] = telemetry.Timestamp.Sub(telemetry.KEDAMetrics.LastScalingEvent).Seconds()
	} else {
		metrics["time_since_last_scale_seconds"] = 0.0
	}

	metrics["hpa_sync_period_seconds"] = 15.0

	return metrics
}
