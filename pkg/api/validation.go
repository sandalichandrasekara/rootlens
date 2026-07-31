package api

import (
	"encoding/json"
	"fmt"
	"net/http"
)

// ValidationError represents a validation error
type ValidationError struct {
	Field   string
	Message string
}

// ValidateWorkloadRequest validates the workload generation request
func ValidateWorkloadRequest(req *WorkloadRequest) []ValidationError {
	var errors []ValidationError

	if req.Count <= 0 {
		errors = append(errors, ValidationError{
			Field:   "count",
			Message: "count must be greater than 0",
		})
	}
	if req.Count > 10000 {
		errors = append(errors, ValidationError{
			Field:   "count",
			Message: "count must not exceed 10000 to prevent DoS",
		})
	}

	if req.Size <= 0 {
		errors = append(errors, ValidationError{
			Field:   "size",
			Message: "size must be greater than 0 bytes",
		})
	}
	if req.Size > 10*1024*1024 {
		errors = append(errors, ValidationError{
			Field:   "size",
			Message: "size must not exceed 10MB",
		})
	}

	if req.Mode != "" && req.Mode != "spike" && req.Mode != "sustained" {
		errors = append(errors, ValidationError{
			Field:   "mode",
			Message: fmt.Sprintf("mode must be 'spike' or 'sustained', got '%s'", req.Mode),
		})
	}

	return errors
}

// ValidateTestRCARequest validates the test RCA request
func ValidateTestRCARequest(req *TestRCARequest) []ValidationError {
	var errors []ValidationError

	if req.ColdStartDelayMs < 0 {
		errors = append(errors, ValidationError{
			Field:   "cold_start_delay_ms",
			Message: "cold start delay cannot be negative",
		})
	}
	if req.ColdStartDelayMs > 60000 {
		errors = append(errors, ValidationError{
			Field:   "cold_start_delay_ms",
			Message: "cold start delay cannot exceed 60000ms",
		})
	}

	if req.SchedulingDelayMs < 0 {
		errors = append(errors, ValidationError{
			Field:   "scheduling_delay_ms",
			Message: "scheduling delay cannot be negative",
		})
	}
	if req.SchedulingDelayMs > 30000 {
		errors = append(errors, ValidationError{
			Field:   "scheduling_delay_ms",
			Message: "scheduling delay cannot exceed 30000ms",
		})
	}

	if req.MetricLagMs < 0 {
		errors = append(errors, ValidationError{
			Field:   "metric_lag_ms",
			Message: "metric lag cannot be negative",
		})
	}
	if req.MetricLagMs > 30000 {
		errors = append(errors, ValidationError{
			Field:   "metric_lag_ms",
			Message: "metric lag cannot exceed 30000ms",
		})
	}

	if req.QueueDepth < 0 {
		errors = append(errors, ValidationError{
			Field:   "queue_depth",
			Message: "queue depth cannot be negative",
		})
	}
	if req.QueueDepth > 1000000 {
		errors = append(errors, ValidationError{
			Field:   "queue_depth",
			Message: "queue depth cannot exceed 1000000",
		})
	}

	if req.CurrentReplicas < 0 {
		errors = append(errors, ValidationError{
			Field:   "current_replicas",
			Message: "current replicas cannot be negative",
		})
	}
	if req.CurrentReplicas > 100 {
		errors = append(errors, ValidationError{
			Field:   "current_replicas",
			Message: "current replicas cannot exceed 100",
		})
	}

	if req.DesiredReplicas < 0 {
		errors = append(errors, ValidationError{
			Field:   "desired_replicas",
			Message: "desired replicas cannot be negative",
		})
	}
	if req.DesiredReplicas > 100 {
		errors = append(errors, ValidationError{
			Field:   "desired_replicas",
			Message: "desired replicas cannot exceed 100",
		})
	}

	if req.MessageRate < 0 {
		errors = append(errors, ValidationError{
			Field:   "message_rate",
			Message: "message rate cannot be negative",
		})
	}
	if req.MessageRate > 100000 {
		errors = append(errors, ValidationError{
			Field:   "message_rate",
			Message: "message rate cannot exceed 100000",
		})
	}

	if req.ConsumerCount < 0 {
		errors = append(errors, ValidationError{
			Field:   "consumer_count",
			Message: "consumer count cannot be negative",
		})
	}
	if req.ConsumerCount > 1000 {
		errors = append(errors, ValidationError{
			Field:   "consumer_count",
			Message: "consumer count cannot exceed 1000",
		})
	}

	return errors
}

// ValidationErrorResponse is the JSON response structure for validation errors
type ValidationErrorResponse struct {
	Errors  []ValidationError `json:"errors"`
	Message string            `json:"message"`
}

// WriteValidationErrors writes validation errors to HTTP response using json.Encoder
func WriteValidationErrors(w http.ResponseWriter, errors []ValidationError) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusBadRequest)

	response := ValidationErrorResponse{
		Errors:  errors,
		Message: "validation failed",
	}
	json.NewEncoder(w).Encode(response)
}
