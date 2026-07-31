package collector

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestRabbitMQCollector(t *testing.T) {
	// Create a mock RabbitMQ API server
	mockServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Verify basic auth
		user, pass, ok := r.BasicAuth()
		if !ok || user != "testuser" || pass != "testpass" {
			w.WriteHeader(http.StatusUnauthorized)
			return
		}

		// Return mock queue stats
		response := map[string]interface{}{
			"name":           "test-queue",
			"messages":       1000,
			"consumers":      5,
			"messages_ready": 950,
			"messages_details": map[string]interface{}{
				"rate": 10.5,
			},
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(response)
	}))
	defer mockServer.Close()

	collector := NewRabbitMQCollector(
		"localhost",
		8080,
		"testuser",
		"testpass",
		"test-queue",
		"/",
		false,
	)

	// Override the collector's URL for testing
	collector.host = mockServer.Listener.Addr().String()
	collector.port = 80

	if collector.queueName != "test-queue" {
		t.Errorf("expected queue name 'test-queue', got '%s'", collector.queueName)
	}

	if collector.queueName != "test-queue" {
		t.Errorf("expected queue name 'test-queue', got '%s'", collector.queueName)
	}

	if collector.username != "testuser" {
		t.Errorf("expected username 'testuser', got '%s'", collector.username)
	}
}
