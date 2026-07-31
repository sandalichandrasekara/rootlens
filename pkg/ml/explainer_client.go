package ml

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"

	pkgmetrics "github.com/sandalichandrasekara/rootlens/pkg/metrics"
	"github.com/sandalichandrasekara/rootlens/pkg/types"
	"github.com/sirupsen/logrus"
)

// ExplainerClient handles communication with ML explainer endpoints
type ExplainerClient struct {
	ServiceURL string
	Timeout    time.Duration
	HTTPClient *http.Client
	Logger     *logrus.Logger
}

// ExplainerRequest is the request sent to explainer endpoints
type ExplainerRequest struct {
	Metrics map[string]interface{} `json:"metrics"`
}

// SubCauseResult contains the explainer response
type SubCauseResult struct {
	Success         bool                      `json:"success"`
	SubCause        string                    `json:"sub_cause"`
	Confidence      float64                   `json:"confidence"`
	Probabilities   map[string]float64        `json:"probabilities"`
	Explanation     types.SubCauseExplanation `json:"explanation"`
	Recommendations []string                  `json:"recommendations"`
	Error           string                    `json:"error,omitempty"`
	Details         string                    `json:"details,omitempty"`
}

// ExplainersStatus contains the status of all explainer models
type ExplainersStatus struct {
	Success    bool            `json:"success"`
	Explainers map[string]bool `json:"explainers"`
}

// NewExplainerClient creates a new explainer client
func NewExplainerClient(serviceURL string, timeout time.Duration, logger *logrus.Logger) *ExplainerClient {
	return &ExplainerClient{
		ServiceURL: serviceURL,
		Timeout:    timeout,
		HTTPClient: &http.Client{
			Timeout: timeout,
		},
		Logger: logger,
	}
}

// ExplainColdStart calls the cold start explainer endpoint
func (c *ExplainerClient) ExplainColdStart(ctx context.Context, metrics map[string]interface{}) (*SubCauseResult, error) {
	return c.callExplainer(ctx, "/explain/cold-start", metrics)
}

// ExplainScheduling calls the scheduling explainer endpoint
func (c *ExplainerClient) ExplainScheduling(ctx context.Context, metrics map[string]interface{}) (*SubCauseResult, error) {
	return c.callExplainer(ctx, "/explain/scheduling", metrics)
}

// ExplainMetricPropagation calls the metric propagation explainer endpoint
func (c *ExplainerClient) ExplainMetricPropagation(ctx context.Context, metrics map[string]interface{}) (*SubCauseResult, error) {
	return c.callExplainer(ctx, "/explain/metric-propagation", metrics)
}

// callExplainer makes the HTTP call to the specified explainer endpoint
func (c *ExplainerClient) callExplainer(ctx context.Context, endpoint string, metrics map[string]interface{}) (*SubCauseResult, error) {
	req := ExplainerRequest{
		Metrics: metrics,
	}

	reqBody, err := json.Marshal(req)
	if err != nil {
		c.Logger.Errorf("Failed to marshal explainer request: %v", err)
		return nil, fmt.Errorf("request marshaling failed: %w", err)
	}

	httpReq, err := http.NewRequestWithContext(
		ctx,
		"POST",
		fmt.Sprintf("%s%s", c.ServiceURL, endpoint),
		bytes.NewBuffer(reqBody),
	)
	if err != nil {
		c.Logger.Errorf("Failed to create HTTP request: %v", err)
		return nil, fmt.Errorf("http request creation failed: %w", err)
	}

	httpReq.Header.Set("Content-Type", "application/json")

	c.Logger.Debugf("Calling explainer: %s", httpReq.URL)
	startTime := time.Now()

	resp, err := c.HTTPClient.Do(httpReq)
	if err != nil {
		c.Logger.Warnf("Explainer call failed: %v", err)
		return nil, fmt.Errorf("explainer call failed: %w", err)
	}
	defer resp.Body.Close()

	duration := time.Since(startTime)
	c.Logger.Debugf("Explainer responded in %v", duration)

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		c.Logger.Errorf("Failed to read response body: %v", err)
		pkgmetrics.RecordMLRequest(endpoint, false, duration.Seconds())
		return nil, fmt.Errorf("response body read failed: %w", err)
	}

	var result SubCauseResult
	if err := json.Unmarshal(body, &result); err != nil {
		c.Logger.Errorf("Failed to parse explainer response: %v. Body: %s", err, string(body))
		pkgmetrics.RecordMLRequest(endpoint, false, duration.Seconds())
		return nil, fmt.Errorf("response parsing failed: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		c.Logger.Warnf("Explainer returned status %d: %s", resp.StatusCode, result.Error)
		pkgmetrics.RecordMLRequest(endpoint, false, duration.Seconds())
		return nil, fmt.Errorf("explainer error (status %d): %s", resp.StatusCode, result.Error)
	}

	if !result.Success {
		c.Logger.Warnf("Explainer failed: %s", result.Error)
		pkgmetrics.RecordMLRequest(endpoint, false, duration.Seconds())
		return nil, fmt.Errorf("explainer failed: %s", result.Error)
	}

	pkgmetrics.RecordMLRequest(endpoint, true, duration.Seconds())
	c.Logger.Debugf("Explainer result: %s (confidence: %.2f)", result.SubCause, result.Confidence)
	return &result, nil
}

// GetExplainersStatus checks which explainer models are loaded
func (c *ExplainerClient) GetExplainersStatus(ctx context.Context) (*ExplainersStatus, error) {
	httpReq, err := http.NewRequestWithContext(
		ctx,
		"GET",
		fmt.Sprintf("%s/explainers/status", c.ServiceURL),
		nil,
	)
	if err != nil {
		return nil, fmt.Errorf("request creation failed: %w", err)
	}

	resp, err := c.HTTPClient.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("status check failed: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("response read failed: %w", err)
	}

	var status ExplainersStatus
	if err := json.Unmarshal(body, &status); err != nil {
		return nil, fmt.Errorf("response parsing failed: %w", err)
	}

	return &status, nil
}

// IsExplainerAvailable checks if a specific explainer is available
func (c *ExplainerClient) IsExplainerAvailable(ctx context.Context, explainerName string) bool {
	status, err := c.GetExplainersStatus(ctx)
	if err != nil {
		c.Logger.Debugf("Failed to get explainer status: %v", err)
		return false
	}

	available, exists := status.Explainers[explainerName]
	return exists && available
}
