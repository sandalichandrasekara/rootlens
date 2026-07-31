package api

import (
	"encoding/json"
	"fmt"
	"math/rand"
	"net/http"
	"os"
	"path/filepath"
	"time"

	"github.com/sandalichandrasekara/rootlens/pkg/collector"
	"github.com/sandalichandrasekara/rootlens/pkg/config"
	"github.com/sandalichandrasekara/rootlens/pkg/metrics"
	"github.com/sandalichandrasekara/rootlens/pkg/rca"
	"github.com/sandalichandrasekara/rootlens/pkg/storage"
	"github.com/sandalichandrasekara/rootlens/pkg/types"
	"github.com/sandalichandrasekara/rootlens/pkg/workload"
	"github.com/sirupsen/logrus"
)

// Server holds API dependencies
type Server struct {
	store             *storage.Store
	rabbitMQCollector *collector.RabbitMQCollector
	k8sCollector      *collector.K8sCollector
	kedaCollector     *collector.KEDACollector
	rcaEngine         *rca.Engine
	workloadGen       *workload.Generator
	logger            *logrus.Logger
	podLabelSelector  string // label selector for consumer pods (env: POD_LABEL_SELECTOR)
	scaledObjectName  string // KEDA ScaledObject name (env: KEDA_SCALED_OBJECT_NAME)
}

// NewServer creates a new API server
func NewServer(store *storage.Store, cfg types.Config) (*Server, error) {
	logger := logrus.New()

	mgmtPort := 15672
	if cfg.RabbitMQ.TLS {
		mgmtPort = 443
	}
	rabbitMQCollector := collector.NewRabbitMQCollector(
		cfg.RabbitMQ.Host,
		mgmtPort,
		cfg.RabbitMQ.Username,
		cfg.RabbitMQ.Password,
		cfg.RabbitMQ.QueueName,
		cfg.RabbitMQ.VHost,
		cfg.RabbitMQ.TLS,
	)

	homeDir, err := os.UserHomeDir()
	if err != nil {
		LogError("get home directory", err)
		homeDir = "/root"
	}
	kubeconfigPath := filepath.Join(homeDir, ".kube", "config")

	kedaCollector, err := collector.NewKEDACollector(kubeconfigPath, "default")
	if err != nil {
		LogWarn("KEDA collector initialization", fmt.Sprintf("not available: %v", err))
	}

	var k8sCollector *collector.K8sCollector
	k8sCollector, err = collector.NewK8sCollector(kubeconfigPath, "default")
	if err != nil {
		LogWarn("K8s collector initialization", fmt.Sprintf("not available (OK for Cloud Run): %v", err))
		k8sCollector = nil
	}

	rcaEngine := rca.NewEngineWithML(cfg.RCA, cfg.ML, logger)

	if rcaEngine.MLEnabled && rcaEngine.ExplainerRouter != nil {
		waitForMLService(rcaEngine, logger)
	}

	var workloadGen *workload.Generator
	workloadGen, err = workload.NewGenerator(
		cfg.RabbitMQ.Host,
		cfg.RabbitMQ.Port,
		cfg.RabbitMQ.Username,
		cfg.RabbitMQ.Password,
		cfg.RabbitMQ.QueueName,
		cfg.RabbitMQ.VHost,
		cfg.RabbitMQ.TLS,
	)
	if err != nil {
		LogWarn("Workload generator initialization", fmt.Sprintf("RabbitMQ not available (OK for Cloud Run): %v", err))
		workloadGen = nil
	}

	podLabelSelector := os.Getenv("POD_LABEL_SELECTOR")
	if podLabelSelector == "" {
		podLabelSelector = "app=consumer"
	}
	scaledObjectName := os.Getenv("KEDA_SCALED_OBJECT_NAME")
	if scaledObjectName == "" {
		scaledObjectName = "rabbitmq-consumer-scaler"
	}

	return &Server{
		store:             store,
		rabbitMQCollector: rabbitMQCollector,
		k8sCollector:      k8sCollector,
		rcaEngine:         rcaEngine,
		workloadGen:       workloadGen,
		kedaCollector:     kedaCollector,
		logger:            logger,
		podLabelSelector:  podLabelSelector,
		scaledObjectName:  scaledObjectName,
	}, nil
}

// waitForMLService polls the ML health endpoint until it reports ready or the
// timeout (30 s) is exceeded. This prevents the first RCA call from returning
// "ml_unavailable" because the Python service is still loading models.
func waitForMLService(engine *rca.Engine, logger *logrus.Logger) {
	const maxWait = 30 * time.Second
	const pollInterval = 1 * time.Second

	serviceURL := engine.ExplainerRouter.Client.ServiceURL
	logger.Infof("Waiting for ML service at %s to be ready...", serviceURL)

	client := &http.Client{Timeout: 2 * time.Second}
	deadline := time.Now().Add(maxWait)
	for time.Now().Before(deadline) {
		resp, err := client.Get(serviceURL + "/health")
		if err == nil {
			resp.Body.Close()
			if resp.StatusCode == http.StatusOK {
				logger.Info("ML service is ready")
				return
			}
			logger.Debugf("ML service not ready yet (status %d), retrying...", resp.StatusCode)
		} else {
			logger.Debugf("ML service not reachable yet: %v, retrying...", err)
		}
		time.Sleep(pollInterval)
	}
	logger.Warn("ML service did not become ready within timeout — will use graceful fallback")
}

// HandleGetMetrics returns current system metrics
func (s *Server) HandleGetMetrics(w http.ResponseWriter, r *http.Request) {
	rabbitMetrics, err := s.rabbitMQCollector.Collect()
	if err != nil {
		LogWarn("collect RabbitMQ metrics", fmt.Sprintf("RabbitMQ unavailable: %v", err))
		cachedMetrics := s.store.GetMetrics()
		if cachedMetrics != nil {
			if err := json.NewEncoder(w).Encode(cachedMetrics); err != nil {
				LogError("encode cached metrics response", err)
			}
			return
		}
		syntheticMetrics := &storage.MetricsSnapshot{
			Timestamp:       time.Now(),
			QueueDepth:      0,
			ConsumerCount:   0,
			PodCount:        0,
			DesiredReplicas: 1,
			MessageRate:     0,
		}
		if err := json.NewEncoder(w).Encode(syntheticMetrics); err != nil {
			LogError("encode synthetic metrics response", err)
		}
		return
	}

	var podMetrics []types.K8sMetrics
	podCount := 1
	if s.k8sCollector != nil {
		var errK8s error
		podMetrics, errK8s = s.k8sCollector.CollectPodMetrics(s.podLabelSelector)
		if errK8s != nil {
			LogWarn("collect pod metrics", fmt.Sprintf("K8s unavailable: %v", errK8s))
			cachedMetrics := s.store.GetMetrics()
			if cachedMetrics != nil {
				podCount = cachedMetrics.PodCount
			} else {
				podCount = 1
			}
		} else {
			podCount = len(podMetrics)
		}
	}

	snapshot := &storage.MetricsSnapshot{
		Timestamp:       rabbitMetrics.Timestamp,
		QueueDepth:      rabbitMetrics.MessageCount,
		ConsumerCount:   rabbitMetrics.ConsumerCount,
		PodCount:        podCount,
		DesiredReplicas: calculateDesiredReplicas(rabbitMetrics.MessageCount),
		MessageRate:     rabbitMetrics.MessageRate,
	}

	s.store.UpdateMetrics(snapshot)
	metrics.UpdateQueueMetrics(rabbitMetrics.MessageCount, rabbitMetrics.ConsumerCount)

	if err := json.NewEncoder(w).Encode(snapshot); err != nil {
		LogError("encode metrics response", err)
	}
}

// HandleGetLatestRCA returns the most recent RCA result
func (s *Server) HandleGetLatestRCA(w http.ResponseWriter, r *http.Request) {
	result := s.store.GetLatestRCA()
	if result == nil {
		if err := json.NewEncoder(w).Encode(map[string]string{"message": "no RCA results available"}); err != nil {
			LogError("encode no RCA results response", err)
		}
		return
	}

	if err := json.NewEncoder(w).Encode(result); err != nil {
		LogError("encode RCA result response", err)
	}
}

// HandleGetRCAHistory returns all RCA results
func (s *Server) HandleGetRCAHistory(w http.ResponseWriter, r *http.Request) {
	history := s.store.GetRCAHistory()
	if err := json.NewEncoder(w).Encode(history); err != nil {
		LogError("encode RCA history response", err)
	}
}

// HandleClearRCAHistory deletes all stored RCA results
func (s *Server) HandleClearRCAHistory(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodDelete {
		WriteError(w, http.StatusMethodNotAllowed, "METHOD_NOT_ALLOWED", "Use DELETE", nil)
		return
	}
	s.store.ClearRCAHistory()
	json.NewEncoder(w).Encode(map[string]string{"status": "cleared"})
}

// HandleGetRCAStats returns RCA statistics
func (s *Server) HandleGetRCAStats(w http.ResponseWriter, r *http.Request) {
	stats := s.store.GetRCAStats()
	if err := json.NewEncoder(w).Encode(stats); err != nil {
		LogError("encode RCA stats response", err)
	}
}

// HandleRunRCA performs RCA analysis with ML enhancement
func (s *Server) HandleRunRCA(w http.ResponseWriter, r *http.Request) {
	var rabbitMetrics *types.RabbitMQMetrics
	var err error

	if s.rabbitMQCollector != nil {
		rabbitMetrics, err = s.rabbitMQCollector.Collect()
	}

	// Cloud Run mode: use metrics from store (populated by workload generation)
	if s.rabbitMQCollector == nil || err != nil {
		cachedMetrics := s.store.GetMetrics()
		if cachedMetrics == nil || cachedMetrics.QueueDepth == 0 {
			WriteError(w, http.StatusBadRequest, "NO_WORKLOAD",
				"No active workload detected. Generate a workload first, then run RCA.", nil)
			return
		}

		now := time.Now()
		queueDepth := cachedMetrics.QueueDepth
		desiredReplicas := cachedMetrics.DesiredReplicas

		// Pick a random delay scenario to produce varied root causes
		scenarios := []struct {
			coldStartMs  int
			schedulingMs int
			metricLagMs  int
		}{
			{35000, 5000, 20000},  // Cold Start dominant
			{8000, 15000, 20000},  // Scheduling dominant
			{8000, 5000, 50000},   // Metric Lag dominant
		}
		sc := scenarios[rand.Intn(len(scenarios))]

		podMetrics := []types.K8sMetrics{
			{
				PodName:            fmt.Sprintf("consumer-%d", now.UnixMilli()%10000),
				Phase:              "Running",
				ScheduledTime:      timePtr(now.Add(-time.Duration(sc.coldStartMs+sc.schedulingMs) * time.Millisecond)),
				ContainerStartTime: timePtr(now.Add(-time.Duration(sc.coldStartMs) * time.Millisecond)),
				ReadyTime:          timePtr(now),
				NodeName:           "gke-node-1",
			},
		}

		telemetry := &types.TelemetryData{
			Timestamp: now,
			RabbitMQMetrics: types.RabbitMQMetrics{
				QueueName:     "rootlens-queue",
				MessageCount:  queueDepth,
				MessageRate:   cachedMetrics.MessageRate,
				ConsumerCount: cachedMetrics.ConsumerCount,
				Timestamp:     now,
			},
			KEDAMetrics: types.KEDAMetrics{
				CurrentReplicas:  1,
				DesiredReplicas:  desiredReplicas,
				LastScalingEvent: now.Add(-time.Duration(sc.metricLagMs) * time.Millisecond),
				IsFromKEDA:       false,
			},
		}

		rcaStart := time.Now()
		enhancedResult := s.rcaEngine.AnalyzeWithML(r.Context(), telemetry, podMetrics)
		rcaDuration := time.Since(rcaStart).Seconds()

		timestamp := time.Now()
		enhancedResult.Timestamp = timestamp.Format(time.RFC3339)
		enhancedResult.DetectedAt = timestamp.Format(time.RFC3339)
		enhancedResult.Round()

		metrics.RecordRCAAnalysis(enhancedResult.RootCause, enhancedResult.MethodAgreement, enhancedResult.FinalConfidence, rcaDuration)
		metrics.RecordRootCause(enhancedResult.RootCause, enhancedResult.SubCause)

		s.store.AddRCAResult(*enhancedResult)

		w.Header().Set("Content-Type", "application/json")
		if err := json.NewEncoder(w).Encode(enhancedResult); err != nil {
			LogError("encode simulated RCA response", err)
		}
		return
	}

	var podMetrics []types.K8sMetrics
	if s.k8sCollector != nil {
		podMetrics, err = s.k8sCollector.CollectPodMetrics(s.podLabelSelector)
		if err != nil {
			LogWarn("collect pod metrics", fmt.Sprintf("K8s unavailable, using simulated: %v", err))
			podMetrics = simulatePodMetrics(rabbitMetrics.MessageCount, rabbitMetrics.MessageRate)
		}
	} else {
		podMetrics = simulatePodMetrics(rabbitMetrics.MessageCount, rabbitMetrics.MessageRate)
	}

	var kedaMetrics *types.KEDAMetrics
	if s.kedaCollector != nil {
		kedaMetrics, err = s.kedaCollector.Collect(s.scaledObjectName)
		if err != nil {
			kedaMetrics = &types.KEDAMetrics{
				CurrentReplicas:  len(podMetrics),
				DesiredReplicas:  calculateDesiredReplicas(rabbitMetrics.MessageCount),
				LastScalingEvent: findEarliestScheduledTime(podMetrics),
				IsFromKEDA:       false,
			}
		} else {
			kedaMetrics.IsFromKEDA = true
		}
	} else {
		kedaMetrics = &types.KEDAMetrics{
			CurrentReplicas:  len(podMetrics),
			DesiredReplicas:  calculateDesiredReplicas(rabbitMetrics.MessageCount),
			LastScalingEvent: findEarliestScheduledTime(podMetrics),
			IsFromKEDA:       false,
		}
	}

	telemetry := &types.TelemetryData{
		Timestamp:       rabbitMetrics.Timestamp,
		RabbitMQMetrics: *rabbitMetrics,
		KEDAMetrics:     *kedaMetrics,
	}

	metrics.UpdateQueueMetrics(rabbitMetrics.MessageCount, rabbitMetrics.ConsumerCount)
	metrics.UpdateKEDAMetrics(kedaMetrics.DesiredReplicas, kedaMetrics.CurrentReplicas)

	rcaStart := time.Now()
	enhancedResult := s.rcaEngine.AnalyzeWithML(r.Context(), telemetry, podMetrics)
	rcaDuration := time.Since(rcaStart).Seconds()

	now := time.Now()
	enhancedResult.Timestamp = now.Format(time.RFC3339)
	enhancedResult.DetectedAt = now.Format(time.RFC3339)

	enhancedResult.Round()

	metrics.RecordRCAAnalysis(enhancedResult.RootCause, enhancedResult.MethodAgreement, enhancedResult.FinalConfidence, rcaDuration)
	metrics.RecordRootCause(enhancedResult.RootCause, enhancedResult.SubCause)
	if enhancedResult.MethodAgreement == "explainer_success" {
		metrics.MLServiceAvailable.Set(1)
	} else if enhancedResult.MethodAgreement == "ml_unavailable" {
		metrics.MLServiceAvailable.Set(0)
	}

	s.store.AddRCAResult(*enhancedResult)

	w.Header().Set("Content-Type", "application/json")
	if err := json.NewEncoder(w).Encode(enhancedResult); err != nil {
		LogError("encode enhanced RCA response", err)
	}
}

// WorkloadRequest represents workload generation request
type WorkloadRequest struct {
	Count int    `json:"count"`
	Size  int    `json:"size"`
	Mode  string `json:"mode"`
}

// HandleGenerateWorkload generates synthetic workload
func (s *Server) HandleGenerateWorkload(w http.ResponseWriter, r *http.Request) {
	r.Body = http.MaxBytesReader(w, r.Body, 1<<16)
	var req WorkloadRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		WriteError(w, http.StatusBadRequest, "INVALID_REQUEST", "invalid request body",
			map[string]interface{}{"error": err.Error()})
		return
	}

	validationErrors := ValidateWorkloadRequest(&req)
	if len(validationErrors) > 0 {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		response := map[string]interface{}{
			"error":   "VALIDATION_ERROR",
			"message": "Invalid request parameters",
			"errors":  validationErrors,
		}
		if err := json.NewEncoder(w).Encode(response); err != nil {
			LogError("encode validation error response", err)
		}
		return
	}

	if req.Count == 0 {
		req.Count = 500
	}
	if req.Size == 0 {
		req.Size = 1024
	}
	if req.Mode == "" {
		req.Mode = "spike"
	}

	if s.workloadGen == nil {
		// Cloud Run mode: simulate workload by updating metrics store
		// Queue depth increases, but RCA is NOT run until user clicks "Run RCA Now"
		now := time.Now()
		existing := s.store.GetMetrics()
		currentDepth := 0
		if existing != nil {
			currentDepth = existing.QueueDepth
		}
		newDepth := currentDepth + req.Count
		desiredReplicas := calculateDesiredReplicas(newDepth)

		s.store.UpdateMetrics(&storage.MetricsSnapshot{
			Timestamp:       now,
			QueueDepth:      newDepth,
			ConsumerCount:   desiredReplicas,
			PodCount:        1,
			DesiredReplicas: desiredReplicas,
			MessageRate:     float64(req.Count) / 5.0,
		})
		metrics.UpdateQueueMetrics(newDepth, desiredReplicas)

		w.Header().Set("Content-Type", "application/json")
		if err := json.NewEncoder(w).Encode(map[string]string{
			"message": fmt.Sprintf("Generated %d messages successfully", req.Count),
		}); err != nil {
			LogError("encode simulated workload response", err)
		}
		return
	}

	var err error
	if req.Mode == "spike" {
		err = s.workloadGen.GenerateSpike(req.Count, req.Size)
	} else {
		err = s.workloadGen.GenerateSustained(100, 60, req.Size)
	}

	if err != nil {
		WriteInternalError(w, "generate workload", err)
		return
	}

	if err := json.NewEncoder(w).Encode(map[string]string{
		"message": fmt.Sprintf("Generated %d messages successfully", req.Count),
	}); err != nil {
		LogError("encode workload generation response", err)
	}
}

// HandlePurgeQueue purges the RabbitMQ queue
func (s *Server) HandlePurgeQueue(w http.ResponseWriter, r *http.Request) {
	if s.workloadGen == nil {
		// Cloud Run mode: reset simulated queue depth to zero
		s.store.UpdateMetrics(&storage.MetricsSnapshot{
			Timestamp:       time.Now(),
			QueueDepth:      0,
			ConsumerCount:   0,
			PodCount:        1,
			DesiredReplicas: 1,
			MessageRate:     0,
		})
		metrics.UpdateQueueMetrics(0, 0)
		w.Header().Set("Content-Type", "application/json")
		if err := json.NewEncoder(w).Encode(map[string]string{"message": "Queue purged successfully"}); err != nil {
			LogError("encode simulated purge response", err)
		}
		return
	}

	if err := s.workloadGen.PurgeQueue(); err != nil {
		WriteInternalError(w, "purge queue", err)
		return
	}

	if err := json.NewEncoder(w).Encode(map[string]string{"message": "Queue purged successfully"}); err != nil {
		LogError("encode purge queue response", err)
	}
}

func calculateDesiredReplicas(queueDepth int) int {
	replicas := queueDepth / config.MessagesPerPod
	if replicas < 1 {
		replicas = 1
	}
	if replicas > 10 {
		replicas = 10
	}
	return replicas
}

// HandleHealthCheck returns server health status
func (s *Server) HandleHealthCheck(w http.ResponseWriter, r *http.Request) {
	rabbitConnected := false
	if s.rabbitMQCollector != nil {
		_, err := s.rabbitMQCollector.Collect()
		rabbitConnected = err == nil
	}

	mlAvailable := s.rcaEngine != nil && s.rcaEngine.MLEnabled

	resp := map[string]interface{}{
		"status": "healthy",
		"rabbitmq": map[string]bool{
			"connected": rabbitConnected,
		},
		"ml_service": map[string]bool{
			"available": mlAvailable,
		},
	}
	if err := json.NewEncoder(w).Encode(resp); err != nil {
		LogError("encode health check response", err)
	}
}

// findEarliestScheduledTime returns the earliest pod scheduled time
func findEarliestScheduledTime(podMetrics []types.K8sMetrics) time.Time {
	var earliest time.Time
	for _, pod := range podMetrics {
		if pod.ScheduledTime != nil {
			if earliest.IsZero() || pod.ScheduledTime.Before(earliest) {
				earliest = *pod.ScheduledTime
			}
		}
	}
	return earliest
}

// simulatePodMetrics generates realistic pod metrics for Cloud Run mode
// Simulates KEDA autoscaling behavior based on queue depth
func simulatePodMetrics(queueDepth int, messageRate float64) []types.K8sMetrics {
	now := time.Now()
	desiredReplicas := calculateDesiredReplicas(queueDepth)

	var podMetrics []types.K8sMetrics

	isScalingUp := queueDepth > 100 && messageRate > 10

	for i := 0; i < desiredReplicas; i++ {
		podName := fmt.Sprintf("consumer-pod-%d", i+1)

		var scheduledTime, containerStartTime, readyTime *time.Time
		var phase string

		if i == 0 {
			st := now.Add(-5 * time.Minute)
			ct := st.Add(500 * time.Millisecond)
			rt := ct.Add(1 * time.Second)
			scheduledTime = &st
			containerStartTime = &ct
			readyTime = &rt
			phase = "Running"
		} else if isScalingUp && i >= desiredReplicas-2 {
			coldStartMs := 2000 + (i * 500)
			schedulingMs := 500 + (i * 300)

			st := now.Add(-time.Duration(coldStartMs+schedulingMs) * time.Millisecond)
			ct := now.Add(-time.Duration(coldStartMs) * time.Millisecond)
			scheduledTime = &st
			containerStartTime = &ct

			if coldStartMs > 3000 {
				phase = "Pending"
			} else {
				rt := now.Add(-500 * time.Millisecond)
				readyTime = &rt
				phase = "Running"
			}
		} else {
			st := now.Add(-time.Duration(3-i) * time.Minute)
			ct := st.Add(800 * time.Millisecond)
			rt := ct.Add(1200 * time.Millisecond)
			scheduledTime = &st
			containerStartTime = &ct
			readyTime = &rt
			phase = "Running"
		}

		podMetrics = append(podMetrics, types.K8sMetrics{
			PodName:            podName,
			Phase:              phase,
			ScheduledTime:      scheduledTime,
			ContainerStartTime: containerStartTime,
			ReadyTime:          readyTime,
			NodeName:           "cloudrun-simulated-node",
		})
	}

	return podMetrics
}

// TestRCARequest for injecting synthetic test data
type TestRCARequest struct {
	QueueDepth        int `json:"queue_depth"`
	MessageRate       int `json:"message_rate"`
	ConsumerCount     int `json:"consumer_count"`
	CurrentReplicas   int `json:"current_replicas"`
	DesiredReplicas   int `json:"desired_replicas"`
	ColdStartDelayMs  int `json:"cold_start_delay_ms"`
	SchedulingDelayMs int `json:"scheduling_delay_ms"`
	MetricLagMs       int `json:"metric_lag_ms"`
}

// HandleTestRCA runs RCA with injected synthetic data and ML enhancement
func (s *Server) HandleTestRCA(w http.ResponseWriter, r *http.Request) {
	r.Body = http.MaxBytesReader(w, r.Body, 1<<16)
	var req TestRCARequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		WriteError(w, http.StatusBadRequest, "INVALID_REQUEST", "invalid request body",
			map[string]interface{}{"error": err.Error()})
		return
	}

	validationErrors := ValidateTestRCARequest(&req)
	if len(validationErrors) > 0 {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		response := map[string]interface{}{
			"error":   "VALIDATION_ERROR",
			"message": "Invalid test RCA parameters",
			"errors":  validationErrors,
		}
		if err := json.NewEncoder(w).Encode(response); err != nil {
			LogError("encode test RCA validation error response", err)
		}
		return
	}

	now := time.Now()

	podMetrics := []types.K8sMetrics{
		{
			PodName:            "synthetic-pod-1",
			Phase:              "Running",
			ScheduledTime:      timePtr(now.Add(-time.Duration(req.ColdStartDelayMs+req.SchedulingDelayMs) * time.Millisecond)),
			ContainerStartTime: timePtr(now.Add(-time.Duration(req.ColdStartDelayMs) * time.Millisecond)),
			ReadyTime:          timePtr(now),
			NodeName:           "synthetic-node",
		},
	}

	telemetry := &types.TelemetryData{
		Timestamp: now,
		RabbitMQMetrics: types.RabbitMQMetrics{
			QueueName:     "test-queue",
			MessageCount:  req.QueueDepth,
			MessageRate:   float64(req.MessageRate),
			ConsumerCount: req.ConsumerCount,
			Timestamp:     now,
		},
		KEDAMetrics: types.KEDAMetrics{
			CurrentReplicas:  req.CurrentReplicas,
			DesiredReplicas:  req.DesiredReplicas,
			LastScalingEvent: now.Add(-time.Duration(req.MetricLagMs) * time.Millisecond),
			IsFromKEDA:       false,
		},
	}

	rcaStart := time.Now()
	enhancedResult := s.rcaEngine.AnalyzeWithML(r.Context(), telemetry, podMetrics)
	rcaDuration := time.Since(rcaStart).Seconds()

	timestamp := time.Now()
	enhancedResult.Timestamp = timestamp.Format(time.RFC3339)
	enhancedResult.DetectedAt = timestamp.Format(time.RFC3339)

	enhancedResult.Round()

	metrics.RecordRCAAnalysis(enhancedResult.RootCause, enhancedResult.MethodAgreement, enhancedResult.FinalConfidence, rcaDuration)
	metrics.RecordRootCause(enhancedResult.RootCause, enhancedResult.SubCause)
	if enhancedResult.MethodAgreement == "explainer_success" {
		metrics.MLServiceAvailable.Set(1)
	} else if enhancedResult.MethodAgreement == "ml_unavailable" {
		metrics.MLServiceAvailable.Set(0)
	}

	s.store.AddRCAResult(*enhancedResult)

	w.Header().Set("Content-Type", "application/json")
	if err := json.NewEncoder(w).Encode(enhancedResult); err != nil {
		LogError("encode test RCA response", err)
	}
}

func timePtr(t time.Time) *time.Time {
	return &t
}
