package metrics

import (
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
)

var (
	// RCA Analysis Metrics
	RCAAnalysisTotal = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "rootlens_rca_analysis_total",
			Help: "Total number of RCA analyses performed",
		},
		[]string{"root_cause", "method"},
	)

	RCAAnalysisDuration = promauto.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "rootlens_rca_analysis_duration_seconds",
			Help:    "Duration of RCA analysis in seconds",
			Buckets: prometheus.DefBuckets,
		},
		[]string{"root_cause"},
	)

	RCAConfidence = promauto.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "rootlens_rca_confidence",
			Help: "Confidence score of the last RCA analysis",
		},
		[]string{"root_cause", "confidence_type"},
	)

	// ML Service Metrics
	MLServiceRequestsTotal = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "rootlens_ml_requests_total",
			Help: "Total number of ML service requests",
		},
		[]string{"explainer", "status"},
	)

	MLServiceLatency = promauto.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "rootlens_ml_latency_seconds",
			Help:    "ML service request latency in seconds",
			Buckets: []float64{0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0},
		},
		[]string{"explainer"},
	)

	MLServiceAvailable = promauto.NewGauge(
		prometheus.GaugeOpts{
			Name: "rootlens_ml_service_available",
			Help: "Whether the ML service is available (1) or not (0)",
		},
	)

	// Queue Metrics
	QueueDepth = promauto.NewGauge(
		prometheus.GaugeOpts{
			Name: "rootlens_queue_depth",
			Help: "Current depth of the RabbitMQ queue",
		},
	)

	QueueConsumers = promauto.NewGauge(
		prometheus.GaugeOpts{
			Name: "rootlens_queue_consumers",
			Help: "Number of active queue consumers",
		},
	)

	MessagesPublished = promauto.NewCounter(
		prometheus.CounterOpts{
			Name: "rootlens_messages_published_total",
			Help: "Total number of messages published to queue",
		},
	)

	MessagesConsumed = promauto.NewCounter(
		prometheus.CounterOpts{
			Name: "rootlens_messages_consumed_total",
			Help: "Total number of messages consumed from queue",
		},
	)

	// KEDA Scaling Metrics
	KEDADesiredReplicas = promauto.NewGauge(
		prometheus.GaugeOpts{
			Name: "rootlens_keda_desired_replicas",
			Help: "Number of replicas desired by KEDA",
		},
	)

	KEDACurrentReplicas = promauto.NewGauge(
		prometheus.GaugeOpts{
			Name: "rootlens_keda_current_replicas",
			Help: "Current number of consumer replicas",
		},
	)

	// Root Cause Distribution
	RootCauseDistribution = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "rootlens_root_cause_distribution_total",
			Help: "Distribution of detected root causes",
		},
		[]string{"root_cause", "sub_cause"},
	)

	// API Request Metrics
	APIRequestsTotal = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "rootlens_api_requests_total",
			Help: "Total number of API requests",
		},
		[]string{"endpoint", "method", "status"},
	)

	APIRequestDuration = promauto.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "rootlens_api_request_duration_seconds",
			Help:    "API request duration in seconds",
			Buckets: prometheus.DefBuckets,
		},
		[]string{"endpoint"},
	)
)

// RecordRCAAnalysis records metrics for an RCA analysis
func RecordRCAAnalysis(rootCause string, method string, confidence float64, durationSeconds float64) {
	RCAAnalysisTotal.WithLabelValues(rootCause, method).Inc()
	RCAAnalysisDuration.WithLabelValues(rootCause).Observe(durationSeconds)
	RCAConfidence.WithLabelValues(rootCause, "final").Set(confidence)
}

// RecordMLRequest records metrics for an ML service request
func RecordMLRequest(explainer string, success bool, latencySeconds float64) {
	status := "success"
	if !success {
		status = "error"
	}
	MLServiceRequestsTotal.WithLabelValues(explainer, status).Inc()
	MLServiceLatency.WithLabelValues(explainer).Observe(latencySeconds)
}

// UpdateQueueMetrics updates queue-related metrics
func UpdateQueueMetrics(depth int, consumers int) {
	QueueDepth.Set(float64(depth))
	QueueConsumers.Set(float64(consumers))
}

// UpdateKEDAMetrics updates KEDA-related metrics
func UpdateKEDAMetrics(desired int, current int) {
	KEDADesiredReplicas.Set(float64(desired))
	KEDACurrentReplicas.Set(float64(current))
}

// RecordRootCause records a detected root cause
func RecordRootCause(rootCause string, subCause string) {
	RootCauseDistribution.WithLabelValues(rootCause, subCause).Inc()
}
