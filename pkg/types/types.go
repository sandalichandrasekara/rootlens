package types

import "time"

// RootCauseType represents the classification of scaling delay
type RootCauseType string

const (
	ColdStart            RootCauseType = "POD_COLD_START"
	SchedulingDelay      RootCauseType = "SCHEDULING_CONTENTION"
	MetricPropagationLag RootCauseType = "METRIC_PROPAGATION_LAG"
	Unknown              RootCauseType = "UNKNOWN"
)

// TelemetryData holds all collected metrics
type TelemetryData struct {
	Timestamp         time.Time
	RabbitMQMetrics   RabbitMQMetrics
	KEDAMetrics       KEDAMetrics
	KubernetesMetrics K8sMetrics
}

// RabbitMQMetrics contains RabbitMQ queue metrics
type RabbitMQMetrics struct {
	QueueName     string
	MessageCount  int
	ConsumerCount int
	MessageRate   float64
	Timestamp     time.Time
}

// KEDAMetrics contains KEDA scaler metrics
type KEDAMetrics struct {
	ScalerName       string
	CurrentReplicas  int
	DesiredReplicas  int
	MetricValue      float64
	LastScalingEvent time.Time
	IsFromKEDA       bool                `json:"is_from_keda"`
	KEDAConfig       *ScaledObjectConfig `json:"keda_config,omitempty"`
}

// ScaledObjectConfig contains KEDA ScaledObject configuration
type ScaledObjectConfig struct {
	// Scaling bounds
	MinReplicas int `json:"min_replicas"`
	MaxReplicas int `json:"max_replicas"`

	// Timing configuration
	PollingInterval int `json:"polling_interval_seconds"`
	CooldownPeriod  int `json:"cooldown_period_seconds"`

	// Trigger configuration
	TriggerType      string `json:"trigger_type"`
	TriggerThreshold int    `json:"trigger_threshold"`

	// Status
	IsActive bool `json:"is_active"`
	IsPaused bool `json:"is_paused"`
	IsReady  bool `json:"is_ready"`
}

// K8sMetrics contains Kubernetes pod metrics
type K8sMetrics struct {
	PodName            string
	Phase              string
	ReadyTime          *time.Time
	ScheduledTime      *time.Time
	ContainerStartTime *time.Time
	NodeName           string

	// Event-derived metrics (populated by EventCollector)
	ImagePullDuration       time.Duration `json:"image_pull_duration,omitempty"`
	ImagePullErrors         int           `json:"image_pull_errors,omitempty"`
	ImageNotFound           bool          `json:"image_not_found,omitempty"`
	ImagePullBackOff        bool          `json:"image_pull_backoff,omitempty"`
	ImageErrorMessage       string        `json:"image_error_message,omitempty"`
	ReadinessProbeFailures  int           `json:"readiness_probe_failures,omitempty"`
	SchedulingFailureReason string        `json:"scheduling_failure_reason,omitempty"`
	InitContainerDuration   time.Duration `json:"init_container_duration,omitempty"`
}

// ContributingCause represents a single root cause with its contribution
type ContributingCause struct {
	Type         RootCauseType `json:"type"`
	DelaySeconds float64       `json:"delay_seconds"`
	Contribution float64       `json:"contribution"`
	Evidence     string        `json:"evidence"`
}

// DiagnosticResult holds the RCA output
type DiagnosticResult struct {
	RootCause          RootCauseType          `json:"root_cause"`
	Confidence         float64                `json:"confidence"`
	ContributingCauses []ContributingCause    `json:"contributing_causes"`
	Timeline           *ScalingTimeline       `json:"timeline,omitempty"`
	DetectedAt         time.Time              `json:"detected_at"`
	Evidence           []string               `json:"evidence"`
	Recommendations    []string               `json:"recommendations"`
	Metrics            map[string]interface{} `json:"metrics"`
}

// TimelineEventType represents the type of scaling event
type TimelineEventType string

const (
	EventQueueThreshold   TimelineEventType = "QUEUE_THRESHOLD_BREACH"
	EventKEDADecision     TimelineEventType = "KEDA_SCALING_DECISION"
	EventPodScheduled     TimelineEventType = "POD_SCHEDULED"
	EventContainerStarted TimelineEventType = "CONTAINER_STARTED"
	EventPodReady         TimelineEventType = "POD_READY"
)

// TimelineEvent represents a single event in the scaling timeline
type TimelineEvent struct {
	RelativeTime string            `json:"relative_time"`
	Timestamp    time.Time         `json:"timestamp"`
	Event        TimelineEventType `json:"event"`
	Description  string            `json:"description"`
}

// ScalingTimeline represents the full timeline of a scaling event
type ScalingTimeline struct {
	Events                     []TimelineEvent   `json:"events"`
	TotalScalingLatencySeconds float64           `json:"total_scaling_latency_seconds"`
	Breakdown                  TimelineBreakdown `json:"breakdown"`
}

// TimelineBreakdown shows delay contribution per phase
type TimelineBreakdown struct {
	KEDAReactionSeconds float64 `json:"keda_reaction_seconds"`
	SchedulingSeconds   float64 `json:"scheduling_seconds"`
	ColdStartSeconds    float64 `json:"cold_start_seconds"`
}
