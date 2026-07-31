package config

import (
	"os"
	"strconv"

	"github.com/sandalichandrasekara/rootlens/pkg/types"
)

// DefaultRCAConfig returns the RCA engine configuration from environment variables.
func DefaultRCAConfig() types.RCAConfig {
	return types.RCAConfig{
		ColdStartThresholdSeconds:  getEnvInt("RCA_COLD_START_THRESHOLD", 2),
		SchedulingThresholdSeconds: getEnvInt("RCA_SCHEDULING_THRESHOLD", 1),
		MetricLagThresholdSeconds:  getEnvInt("RCA_METRIC_LAG_THRESHOLD", 5),
	}
}

const MessagesPerPod = 50

// LoadRabbitMQConfig loads RabbitMQ configuration from environment variables
func LoadRabbitMQConfig() types.RabbitMQConfig {
	cfg := types.RabbitMQConfig{
		Host:      getEnv("RABBITMQ_HOST", "localhost"),
		Username:  getEnv("RABBITMQ_USERNAME", "guest"),
		Password:  getEnv("RABBITMQ_PASSWORD", "guest"),
		QueueName: getEnv("RABBITMQ_QUEUE", "rootlens-tasks"),
		Port:      getEnvInt("RABBITMQ_PORT", 5672),
		VHost:     getEnv("RABBITMQ_VHOST", "/"),
		TLS:       getEnvBool("RABBITMQ_TLS", false),
	}
	return cfg
}

func getEnv(key, defaultValue string) string {
	if value, exists := os.LookupEnv(key); exists {
		return value
	}
	return defaultValue
}

func getEnvInt(key string, defaultValue int) int {
	if value, exists := os.LookupEnv(key); exists {
		if intVal, err := strconv.Atoi(value); err == nil {
			return intVal
		}
	}
	return defaultValue
}

// LoadMLConfig loads ML service configuration from environment variables.
func LoadMLConfig() types.MLConfig {
	return types.MLConfig{
		Enabled:         getEnvBool("ML_ENABLED", true),
		ServiceURL:      getEnv("ML_SERVICE_URL", "http://localhost:5000"),
		TimeoutSeconds:  getEnvInt("ML_TIMEOUT_SECONDS", 2),
		RuleWeight:      getEnvFloat("ML_RULE_WEIGHT", 0.6),
		MLWeight:        getEnvFloat("ML_WEIGHT", 0.4),
		FallbackOnError: getEnvBool("ML_FALLBACK_ON_ERROR", true),
	}
}

func getEnvBool(key string, defaultValue bool) bool {
	if value, exists := os.LookupEnv(key); exists {
		return value == "true" || value == "1" || value == "yes"
	}
	return defaultValue
}

func getEnvFloat(key string, defaultValue float64) float64 {
	if value, exists := os.LookupEnv(key); exists {
		if floatVal, err := strconv.ParseFloat(value, 64); err == nil {
			return floatVal
		}
	}
	return defaultValue
}
