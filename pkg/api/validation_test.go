package api

import (
	"testing"
)

func TestValidateWorkloadRequest(t *testing.T) {
	tests := []struct {
		name     string
		req      *WorkloadRequest
		hasError bool
	}{
		{
			name:     "valid spike request",
			req:      &WorkloadRequest{Count: 500, Size: 1024, Mode: "spike"},
			hasError: false,
		},
		{
			name:     "valid sustained request",
			req:      &WorkloadRequest{Count: 100, Size: 2048, Mode: "sustained"},
			hasError: false,
		},
		{
			name:     "count too high",
			req:      &WorkloadRequest{Count: 20000, Size: 1024, Mode: "spike"},
			hasError: true,
		},
		{
			name:     "count zero",
			req:      &WorkloadRequest{Count: 0, Size: 1024, Mode: "spike"},
			hasError: true,
		},
		{
			name:     "size too large",
			req:      &WorkloadRequest{Count: 500, Size: 20 * 1024 * 1024, Mode: "spike"},
			hasError: true,
		},
		{
			name:     "invalid mode",
			req:      &WorkloadRequest{Count: 500, Size: 1024, Mode: "invalid"},
			hasError: true,
		},
		{
			name:     "default mode",
			req:      &WorkloadRequest{Count: 500, Size: 1024, Mode: ""},
			hasError: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			errors := ValidateWorkloadRequest(tt.req)
			if (len(errors) > 0) != tt.hasError {
				t.Errorf("expected hasError=%v, got %v (errors: %v)", tt.hasError, len(errors) > 0, errors)
			}
		})
	}
}

func TestValidateTestRCARequest(t *testing.T) {
	tests := []struct {
		name     string
		req      *TestRCARequest
		hasError bool
	}{
		{
			name: "valid request",
			req: &TestRCARequest{
				ColdStartDelayMs:  5000,
				SchedulingDelayMs: 3000,
				MetricLagMs:       2000,
				QueueDepth:        100,
				CurrentReplicas:   1,
				DesiredReplicas:   5,
			},
			hasError: false,
		},
		{
			name: "negative cold start delay",
			req: &TestRCARequest{
				ColdStartDelayMs: -1000,
			},
			hasError: true,
		},
		{
			name: "cold start delay too high",
			req: &TestRCARequest{
				ColdStartDelayMs: 70000,
			},
			hasError: true,
		},
		{
			name: "negative queue depth",
			req: &TestRCARequest{
				QueueDepth: -100,
			},
			hasError: true,
		},
		{
			name: "replicas too high",
			req: &TestRCARequest{
				CurrentReplicas: 200,
			},
			hasError: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			errors := ValidateTestRCARequest(tt.req)
			if (len(errors) > 0) != tt.hasError {
				t.Errorf("expected hasError=%v, got %v (errors: %v)", tt.hasError, len(errors) > 0, errors)
			}
		})
	}
}
