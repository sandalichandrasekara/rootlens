package types

// Config holds application configuration
type Config struct {
	Kubernetes K8sConfig
	RabbitMQ   RabbitMQConfig
	KEDA       KEDAConfig
	Collection CollectionConfig
	RCA        RCAConfig
	ML         MLConfig
}

// K8sConfig holds Kubernetes configuration
type K8sConfig struct {
	Namespace      string
	KubeconfigPath string
}

// RabbitMQConfig holds RabbitMQ configuration
type RabbitMQConfig struct {
	Host      string
	Port      int
	Username  string
	Password  string
	QueueName string
	VHost     string
	TLS       bool
}

// KEDAConfig holds KEDA configuration
type KEDAConfig struct {
	Namespace  string
	ScalerName string
}

// CollectionConfig holds data collection configuration
type CollectionConfig struct {
	IntervalSeconds int
	RetentionPeriod int
}

// RCAConfig holds RCA engine configuration
type RCAConfig struct {
	ColdStartThresholdSeconds  int
	SchedulingThresholdSeconds int
	MetricLagThresholdSeconds  int
}

// MLConfig holds ML service configuration
type MLConfig struct {
	Enabled         bool
	ServiceURL      string
	TimeoutSeconds  int
	RuleWeight      float64
	MLWeight        float64
	FallbackOnError bool
}
