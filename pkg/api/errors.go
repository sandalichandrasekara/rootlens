package api

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
)

// ErrorResponse represents a structured error response
type ErrorResponse struct {
	Error   string                 `json:"error"`
	Message string                 `json:"message"`
	Details map[string]interface{} `json:"details,omitempty"`
}

// DataSourceInfo indicates where data came from
type DataSourceInfo struct {
	IsFromKEDA      bool   `json:"is_from_keda"`
	IsFromCache     bool   `json:"is_from_cache"`
	IsFallback      bool   `json:"is_fallback"`
	DataSourceNotes string `json:"data_source_notes,omitempty"`
}

// LogError logs an error with context
func LogError(operation string, err error, details ...string) {
	if err == nil {
		return
	}
	msg := fmt.Sprintf("[ERROR] %s: %v", operation, err)
	if len(details) > 0 {
		msg += fmt.Sprintf(" (%s)", details[0])
	}
	log.Print(msg)
}

// LogWarn logs a warning with context
func LogWarn(operation string, msg string) {
	log.Printf("[WARN] %s: %s", operation, msg)
}

// LogInfo logs an info message
func LogInfo(msg string) {
	log.Printf("[INFO] %s", msg)
}

// WriteError writes a structured error response
func WriteError(w http.ResponseWriter, statusCode int, errType string, message string, details map[string]interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(statusCode)

	response := ErrorResponse{
		Error:   errType,
		Message: message,
		Details: details,
	}

	json.NewEncoder(w).Encode(response)
}

// WriteInternalError writes a 500 error
func WriteInternalError(w http.ResponseWriter, operation string, err error) {
	LogError(operation, err)
	WriteError(w, http.StatusInternalServerError, "INTERNAL_ERROR",
		fmt.Sprintf("Failed to %s", operation),
		map[string]interface{}{"error": err.Error()})
}

// WriteValidationError writes a 400 error
func WriteValidationError(w http.ResponseWriter, field string, message string) {
	WriteError(w, http.StatusBadRequest, "VALIDATION_ERROR", "Invalid request",
		map[string]interface{}{"field": field, "message": message})
}

// RecoveryLog represents a recovery action taken
type RecoveryLog struct {
	Operation string `json:"operation"`
	Action    string `json:"action"`
	Reason    string `json:"reason"`
}

// ResponseWithFallback wraps a response with fallback information
type ResponseWithFallback struct {
	Data       interface{}    `json:"data"`
	Source     DataSourceInfo `json:"source"`
	Recoveries []RecoveryLog  `json:"recoveries,omitempty"`
}
