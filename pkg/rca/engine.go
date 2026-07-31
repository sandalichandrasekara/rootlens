package rca

import (
	"context"
	"fmt"
	"time"

	"github.com/sandalichandrasekara/rootlens/pkg/ml"
	"github.com/sandalichandrasekara/rootlens/pkg/types"
	"github.com/sirupsen/logrus"
)

type Engine struct {
	config          types.RCAConfig
	MLEnabled       bool                // Enable/disable ML explainers
	ExplainerRouter *ml.ExplainerRouter // Sub-cause explainer router
	Logger          *logrus.Logger      // Logger for ML operations
	RuleWeight      float64             // Weight for rule-based confidence (default 0.6)
	MLWeight        float64             // Weight for ML confidence (default 0.4)
	mlTimeout       time.Duration       // Timeout for ML explainer calls
}

func NewEngine(config types.RCAConfig) *Engine {
	return &Engine{
		config: config,
	}
}

// NewEngineWithML creates an RCA engine with optional ML explainer enhancement.
func NewEngineWithML(rcaCfg types.RCAConfig, mlCfg types.MLConfig, logger *logrus.Logger) *Engine {
	ruleWeight := mlCfg.RuleWeight
	mlWeight := mlCfg.MLWeight
	if ruleWeight == 0 || mlWeight == 0 {
		ruleWeight = 0.6
		mlWeight = 0.4
	}
	total := ruleWeight + mlWeight
	if total != 1.0 && total > 0 {
		ruleWeight = ruleWeight / total
		mlWeight = mlWeight / total
	}

	mlTimeout := time.Duration(mlCfg.TimeoutSeconds) * time.Second
	if mlTimeout <= 0 {
		mlTimeout = 5 * time.Second
	}

	e := &Engine{
		config:     rcaCfg,
		Logger:     logger,
		RuleWeight: ruleWeight,
		MLWeight:   mlWeight,
		mlTimeout:  mlTimeout,
	}

	if mlCfg.Enabled {
		explainerClient := ml.NewExplainerClient(mlCfg.ServiceURL, mlTimeout, logger)
		e.ExplainerRouter = ml.NewExplainerRouter(explainerClient, logger)
		e.MLEnabled = true
	}

	return e
}

// Analyze performs root cause analysis on telemetry data
func (e *Engine) Analyze(
	telemetry *types.TelemetryData,
	podMetrics []types.K8sMetrics,
) (*types.DiagnosticResult, error) {

	result := &types.DiagnosticResult{
		DetectedAt:         time.Now(),
		Evidence:           []string{},
		Recommendations:    []string{},
		Metrics:            make(map[string]interface{}),
		ContributingCauses: []types.ContributingCause{},
	}

	if len(podMetrics) == 0 {
		result.RootCause = types.Unknown
		result.Confidence = 0.0
		result.Evidence = append(result.Evidence, "No consumer pods found")
		return result, nil
	}

	recentPods := e.hasRecentPodCreation(podMetrics, 60*time.Second)
	scalingInProgress := telemetry.KEDAMetrics.DesiredReplicas >
		telemetry.KEDAMetrics.CurrentReplicas

	if !scalingInProgress && !recentPods {
		result.RootCause = types.Unknown
		result.Confidence = 0.0
		result.Evidence = append(result.Evidence, "No recent scaling event detected")
		return result, nil
	}

	if telemetry.RabbitMQMetrics.MessageCount == 0 && !recentPods {
		result.RootCause = types.Unknown
		result.Confidence = 0.0
		result.Evidence = append(
			result.Evidence,
			"No message backlog or recent scaling activity detected",
		)
		return result, nil
	}

	coldStartDelay := e.detectColdStart(podMetrics)
	schedulingDelay := e.detectSchedulingDelay(podMetrics)
	metricLag := e.detectMetricLag(telemetry)

	result = e.classifyRootCause(
		coldStartDelay,
		schedulingDelay,
		metricLag,
		telemetry,
		podMetrics,
	)

	return result, nil
}

// hasRecentPodCreation checks if any pods were created recently
func (e *Engine) hasRecentPodCreation(
	podMetrics []types.K8sMetrics,
	within time.Duration,
) bool {
	now := time.Now()
	for _, pod := range podMetrics {
		if pod.ScheduledTime != nil {
			if now.Sub(*pod.ScheduledTime) <= within {
				return true
			}
		}
	}
	return false
}

func (e *Engine) detectColdStart(podMetrics []types.K8sMetrics) time.Duration {
	var maxColdStart time.Duration

	for _, pod := range podMetrics {
		if pod.ContainerStartTime != nil && pod.ReadyTime != nil {
			d := pod.ReadyTime.Sub(*pod.ContainerStartTime)
			if d > maxColdStart {
				maxColdStart = d
			}
		}
	}
	return maxColdStart
}

func (e *Engine) detectSchedulingDelay(podMetrics []types.K8sMetrics) time.Duration {
	var maxSchedulingDelay time.Duration

	for _, pod := range podMetrics {
		if pod.ScheduledTime != nil && pod.ContainerStartTime != nil {
			d := pod.ContainerStartTime.Sub(*pod.ScheduledTime)
			if d > maxSchedulingDelay {
				maxSchedulingDelay = d
			}
		}
	}
	return maxSchedulingDelay
}

func (e *Engine) detectMetricLag(telemetry *types.TelemetryData) time.Duration {
	if !telemetry.KEDAMetrics.LastScalingEvent.IsZero() {
		lag := telemetry.Timestamp.Sub(telemetry.KEDAMetrics.LastScalingEvent)
		if lag < 0 {
			lag = 0
		}
		return lag
	}
	return 0
}

// classifyRootCause classifies by dominant delay and tracks all contributing causes
func (e *Engine) classifyRootCause(
	coldStart,
	scheduling,
	metricLag time.Duration,
	telemetry *types.TelemetryData,
	podMetrics []types.K8sMetrics,
) *types.DiagnosticResult {

	result := &types.DiagnosticResult{
		DetectedAt:         time.Now(),
		Evidence:           []string{},
		Recommendations:    []string{},
		Metrics:            make(map[string]interface{}),
		ContributingCauses: []types.ContributingCause{},
	}

	coldStartThreshold :=
		time.Duration(e.config.ColdStartThresholdSeconds) * time.Second
	schedulingThreshold :=
		time.Duration(e.config.SchedulingThresholdSeconds) * time.Second
	metricLagThreshold :=
		time.Duration(e.config.MetricLagThresholdSeconds) * time.Second

	result.Metrics["cold_start_delay_seconds"] = coldStart.Seconds()
	result.Metrics["scheduling_delay_seconds"] = scheduling.Seconds()
	result.Metrics["metric_lag_seconds"] = metricLag.Seconds()
	result.Metrics["queue_depth"] = telemetry.RabbitMQMetrics.MessageCount
	result.Metrics["desired_replicas"] = telemetry.KEDAMetrics.DesiredReplicas
	result.Metrics["current_replicas"] = telemetry.KEDAMetrics.CurrentReplicas

	minDelay := 100 * time.Millisecond
	if coldStart < minDelay && scheduling < minDelay && metricLag < minDelay {
		result.RootCause = types.Unknown
		result.Confidence = 0.3
		result.Evidence = append(
			result.Evidence,
			"No significant delays detected - system performing optimally",
		)
		return result
	}

	if coldStart >= scheduling && coldStart >= metricLag {
		result.RootCause = types.ColdStart
		if coldStart >= coldStartThreshold {
			result.Confidence = 0.85
		} else {
			result.Confidence = 0.70
		}
		result.Evidence = append(
			result.Evidence,
			fmt.Sprintf("Pod cold start is dominant delay: %.2fs", coldStart.Seconds()),
		)
		result.Recommendations = append(
			result.Recommendations,
			"Consider pod pre-warming or reducing container image size",
		)

	} else if scheduling >= coldStart && scheduling >= metricLag {
		result.RootCause = types.SchedulingDelay
		if scheduling >= schedulingThreshold {
			result.Confidence = 0.80
		} else {
			result.Confidence = 0.65
		}
		result.Evidence = append(
			result.Evidence,
			fmt.Sprintf("Pod scheduling is dominant delay: %.2fs", scheduling.Seconds()),
		)
		result.Recommendations = append(
			result.Recommendations,
			"Check cluster resource availability",
		)

	} else {
		result.RootCause = types.MetricPropagationLag
		if metricLag >= metricLagThreshold {
			result.Confidence = 0.75
		} else {
			result.Confidence = 0.60
		}
		result.Evidence = append(
			result.Evidence,
			fmt.Sprintf("Metric propagation is dominant delay: %.2fs", metricLag.Seconds()),
		)
		result.Recommendations = append(
			result.Recommendations,
			"Reduce KEDA polling interval",
		)
	}

	totalDelay := coldStart + scheduling + metricLag
	if totalDelay > 0 {
		if coldStart >= minDelay {
			result.ContributingCauses = append(result.ContributingCauses,
				types.ContributingCause{
					Type:         types.ColdStart,
					DelaySeconds: coldStart.Seconds(),
					Contribution: (coldStart.Seconds() / totalDelay.Seconds()) * 100,
					Evidence:     fmt.Sprintf("Container initialization: %.2fs", coldStart.Seconds()),
				},
			)
		}

		if scheduling >= minDelay {
			result.ContributingCauses = append(result.ContributingCauses,
				types.ContributingCause{
					Type:         types.SchedulingDelay,
					DelaySeconds: scheduling.Seconds(),
					Contribution: (scheduling.Seconds() / totalDelay.Seconds()) * 100,
					Evidence:     fmt.Sprintf("Pod scheduling: %.2fs", scheduling.Seconds()),
				},
			)
		}

		if metricLag >= minDelay {
			result.ContributingCauses = append(result.ContributingCauses,
				types.ContributingCause{
					Type:         types.MetricPropagationLag,
					DelaySeconds: metricLag.Seconds(),
					Contribution: (metricLag.Seconds() / totalDelay.Seconds()) * 100,
					Evidence:     fmt.Sprintf("KEDA metric propagation: %.2fs", metricLag.Seconds()),
				},
			)
		}
	}

	return result
}

// AnalyzeWithML performs RCA analysis and enhances it with ML sub-cause explanations
func (e *Engine) AnalyzeWithML(ctx context.Context, telemetry *types.TelemetryData, podMetrics []types.K8sMetrics) *types.EnhancedRCAResult {
	ruleResult, err := e.Analyze(telemetry, podMetrics)
	if err != nil && e.Logger != nil {
		e.Logger.Warnf("Rule-based Analyze returned an error: %v", err)
	}

	result := &types.EnhancedRCAResult{
		RootCause:           string(ruleResult.RootCause),
		RuleBasedConfidence: ruleResult.Confidence,
		FinalConfidence:     ruleResult.Confidence,
		Evidence:            ruleResult.Evidence,
		Recommendations:     ruleResult.Recommendations,
		Timestamp:           time.Now().Format(time.RFC3339),
		DetectedAt:          ruleResult.DetectedAt.Format(time.RFC3339),
	}

	if !e.MLEnabled || e.ExplainerRouter == nil {
		result.MethodAgreement = "ml_disabled"
		return result
	}

	e.addSubCauseExplanation(ctx, result, ruleResult.RootCause, telemetry, podMetrics)

	mlSucceeded := result.SubCauseConfidence > 0 &&
		result.SubCause != "" &&
		result.SubCause != "undetermined" &&
		result.SubCause != "ml_unavailable"

	if mlSucceeded {
		result.MLConfidence = result.SubCauseConfidence
		combined := (result.RuleBasedConfidence * e.RuleWeight) + (result.MLConfidence * e.MLWeight)
		if combined > 1.0 {
			combined = 1.0
		} else if combined < 0.0 {
			combined = 0.0
		}
		result.FinalConfidence = combined
	}

	if result.RootCause == string(types.Unknown) {
		result.MethodAgreement = "no_scaling_detected"
	} else if mlSucceeded {
		result.MethodAgreement = "explainer_success"
	} else if result.SubCause == "ml_unavailable" {
		// ML service was unreachable — graceful degradation to rule-based only
		result.MethodAgreement = "ml_unavailable"
	} else {
		// ML responded but confidence was too low to use
		result.MethodAgreement = "explainer_fallback"
	}

	if e.Logger != nil {
		e.Logger.Debugf("RCA enhanced: root_cause=%s (rule_conf: %.2f, ml_conf: %.2f, final: %.2f), sub_cause=%s",
			result.RootCause, result.RuleBasedConfidence, result.MLConfidence, result.FinalConfidence,
			result.SubCause)
	}

	return result
}

// addSubCauseExplanation calls the appropriate explainer and adds sub-cause to result
func (e *Engine) addSubCauseExplanation(
	ctx context.Context,
	result *types.EnhancedRCAResult,
	rootCause types.RootCauseType,
	telemetry *types.TelemetryData,
	podMetrics []types.K8sMetrics,
) {
	if e.ExplainerRouter == nil || rootCause == types.Unknown {
		return
	}

	var explainerMetrics map[string]interface{}

	switch rootCause {
	case types.ColdStart:
		if len(podMetrics) > 0 {
			explainerMetrics = ml.PrepareMetricsForColdStart(&podMetrics[0])
		}
	case types.SchedulingDelay:
		if len(podMetrics) > 0 {
			explainerMetrics = ml.PrepareMetricsForScheduling(&podMetrics[0], telemetry)
		}
	case types.MetricPropagationLag:
		metricLag := e.detectMetricLag(telemetry)
		explainerMetrics = ml.PrepareMetricsForMetricPropagation(telemetry, metricLag.Seconds())
	default:
		return
	}

	if explainerMetrics == nil {
		return
	}

	explainerCtx, cancel := context.WithTimeout(ctx, e.mlTimeout)
	defer cancel()

	subCauseResult := e.ExplainerRouter.ExplainWithFallback(explainerCtx, rootCause, explainerMetrics)
	if subCauseResult == nil {
		if e.Logger != nil {
			e.Logger.Warnf("ML explainer returned nil for root cause %s — no sub-cause will be reported", rootCause)
		}
		return
	}

	result.SubCause = subCauseResult.SubCause
	result.SubCauseConfidence = subCauseResult.Confidence
	result.SubCauseProbabilities = subCauseResult.Probabilities
	result.SubCauseRecommendations = subCauseResult.Recommendations

	if subCauseResult.Success {
		result.SubCauseExplanation = &subCauseResult.Explanation
	}

	if e.Logger != nil {
		e.Logger.Debugf("Sub-cause identified: %s (confidence: %.2f) for root cause %s",
			subCauseResult.SubCause, subCauseResult.Confidence, rootCause)
	}
}
