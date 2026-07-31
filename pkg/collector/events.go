package collector

import (
	"context"
	"fmt"
	"strings"
	"sync"
	"time"

	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/watch"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/tools/clientcmd"
)

// EventRecord represents a single Kubernetes event
type EventRecord struct {
	Timestamp time.Time `json:"timestamp"`
	Type      string    `json:"type"`
	Reason    string    `json:"reason"`
	Message   string    `json:"message"`
	Count     int32     `json:"count"`
}

// PodEventSummary contains analyzed events for a specific pod
type PodEventSummary struct {
	PodName string        `json:"pod_name"`
	Events  []EventRecord `json:"events"`

	// SCHEDULING EVENTS
	ScheduledAt       *time.Time `json:"scheduled_at,omitempty"`
	SchedulingFailed  bool       `json:"scheduling_failed"`
	SchedulingReason  string     `json:"scheduling_reason,omitempty"`
	SchedulingMessage string     `json:"scheduling_message,omitempty"`
	Preempted         bool       `json:"preempted"`
	PreemptedBy       string     `json:"preempted_by,omitempty"`

	// IMAGE EVENTS
	ImagePullStart    *time.Time    `json:"image_pull_start,omitempty"`
	ImagePullEnd      *time.Time    `json:"image_pull_end,omitempty"`
	ImagePullDuration time.Duration `json:"image_pull_duration"`
	ImagePullErrors   int           `json:"image_pull_errors"`
	ImageNotFound     bool          `json:"image_not_found"`
	ImagePullBackOff  bool          `json:"image_pull_backoff"`
	ImageErrorMessage string        `json:"image_error_message,omitempty"`
	InvalidImageName  bool          `json:"invalid_image_name"`
	InspectFailed     bool          `json:"inspect_failed"`

	// CONTAINER EVENTS
	ContainerCreated   bool       `json:"container_created"`
	ContainerStarted   bool       `json:"container_started"`
	ContainerStartedAt *time.Time `json:"container_started_at,omitempty"`
	ContainerKilled    bool       `json:"container_killed"`
	ContainerBackOff   bool       `json:"container_backoff"`
	BackOffCount       int        `json:"backoff_count"`
	CrashLoopBackOff   bool       `json:"crash_loop_backoff"`
	ContainerExitCode  int        `json:"container_exit_code,omitempty"`
	RestartCount       int        `json:"restart_count"`

	// PROBE EVENTS
	LivenessFailures  int    `json:"liveness_failures"`
	ReadinessFailures int    `json:"readiness_failures"`
	StartupFailures   int    `json:"startup_failures"`
	ProbeErrorMessage string `json:"probe_error_message,omitempty"`

	// VOLUME EVENTS
	VolumeMounted      bool   `json:"volume_mounted"`
	VolumeMountFailed  bool   `json:"volume_mount_failed"`
	VolumeAttached     bool   `json:"volume_attached"`
	VolumeAttachFailed bool   `json:"volume_attach_failed"`
	VolumeErrorMessage string `json:"volume_error_message,omitempty"`
	PVCPending         bool   `json:"pvc_pending"`

	// NETWORK EVENTS
	NetworkNotReady     bool   `json:"network_not_ready"`
	SandboxCreateFailed bool   `json:"sandbox_create_failed"`
	NetworkErrorMessage string `json:"network_error_message,omitempty"`
	HostPortConflict    bool   `json:"host_port_conflict"`

	// RESOURCE EVENTS
	OOMKilled         bool   `json:"oom_killed"`
	Evicted           bool   `json:"evicted"`
	EvictionReason    string `json:"eviction_reason,omitempty"`
	ResourceExhausted bool   `json:"resource_exhausted"`

	// NODE EVENTS
	NodeNotReady     bool   `json:"node_not_ready"`
	NodeAffinity     bool   `json:"node_affinity_mismatch"`
	NodeErrorMessage string `json:"node_error_message,omitempty"`

	// SECURITY/ADMISSION EVENTS
	FailedValidation  bool   `json:"failed_validation"`
	ValidationMessage string `json:"validation_message,omitempty"`
	SecurityViolation bool   `json:"security_violation"`

	// INIT CONTAINER EVENTS
	InitContainerFailed  bool   `json:"init_container_failed"`
	InitContainerMessage string `json:"init_container_message,omitempty"`

	// SUMMARY FLAGS
	HasWarnings bool `json:"has_warnings"`
	HasErrors   bool `json:"has_errors"`
}

// RingBuffer stores events with automatic expiration
type RingBuffer struct {
	events []corev1.Event
	mu     sync.RWMutex
	maxAge time.Duration
}

// NewRingBuffer creates a buffer that keeps events for maxAge duration
func NewRingBuffer(maxAge time.Duration) *RingBuffer {
	return &RingBuffer{
		events: make([]corev1.Event, 0, 1000),
		maxAge: maxAge,
	}
}

// Add inserts an event and removes expired ones
func (rb *RingBuffer) Add(event corev1.Event) {
	rb.mu.Lock()
	defer rb.mu.Unlock()

	// Remove expired events
	cutoff := time.Now().Add(-rb.maxAge)
	filtered := rb.events[:0]
	for _, e := range rb.events {
		eventTime := e.LastTimestamp.Time
		if eventTime.IsZero() {
			eventTime = e.EventTime.Time
		}
		if eventTime.After(cutoff) {
			filtered = append(filtered, e)
		}
	}
	rb.events = filtered

	// Add new event
	rb.events = append(rb.events, event)
}

// GetForPod returns all events for a specific pod
func (rb *RingBuffer) GetForPod(podName string, since time.Duration) []corev1.Event {
	rb.mu.RLock()
	defer rb.mu.RUnlock()

	cutoff := time.Now().Add(-since)
	var result []corev1.Event

	for _, e := range rb.events {
		if e.InvolvedObject.Name != podName {
			continue
		}
		eventTime := e.LastTimestamp.Time
		if eventTime.IsZero() {
			eventTime = e.EventTime.Time
		}
		if eventTime.After(cutoff) {
			result = append(result, e)
		}
	}

	return result
}

// EventCollector watches and collects Kubernetes events for pods
type EventCollector struct {
	clientset   *kubernetes.Clientset
	namespace   string
	eventBuffer *RingBuffer
	watcher     watch.Interface
	stopCh      chan struct{}
	mu          sync.Mutex
	watching    bool
}

// NewEventCollector creates a new event collector
func NewEventCollector(kubeconfigPath, namespace string) (*EventCollector, error) {
	config, err := clientcmd.BuildConfigFromFlags("", kubeconfigPath)
	if err != nil {
		return nil, fmt.Errorf("failed to build kubeconfig: %w", err)
	}

	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		return nil, fmt.Errorf("failed to create clientset: %w", err)
	}

	return &EventCollector{
		clientset:   clientset,
		namespace:   namespace,
		eventBuffer: NewRingBuffer(5 * time.Minute),
		stopCh:      make(chan struct{}),
	}, nil
}

// NewEventCollectorWithClientset creates an event collector with an existing clientset
func NewEventCollectorWithClientset(clientset *kubernetes.Clientset, namespace string) *EventCollector {
	return &EventCollector{
		clientset:   clientset,
		namespace:   namespace,
		eventBuffer: NewRingBuffer(5 * time.Minute),
		stopCh:      make(chan struct{}),
	}
}

// StartWatching begins watching events for pods
func (e *EventCollector) StartWatching(labelSelector string) error {
	e.mu.Lock()
	defer e.mu.Unlock()

	if e.watching {
		return nil
	}

	if err := e.loadExistingEvents(); err != nil {
		return fmt.Errorf("failed to load existing events: %w", err)
	}

	watcher, err := e.clientset.CoreV1().Events(e.namespace).Watch(context.Background(), metav1.ListOptions{})
	if err != nil {
		return fmt.Errorf("failed to start event watcher: %w", err)
	}

	e.watcher = watcher
	e.watching = true
	go e.processEvents()

	return nil
}

// loadExistingEvents loads recent events
func (e *EventCollector) loadExistingEvents() error {
	events, err := e.clientset.CoreV1().Events(e.namespace).List(context.Background(), metav1.ListOptions{})
	if err != nil {
		return err
	}

	for _, event := range events.Items {
		e.eventBuffer.Add(event)
	}

	return nil
}

// processEvents handles incoming events from the watcher
func (e *EventCollector) processEvents() {
	for {
		select {
		case <-e.stopCh:
			return
		case event, ok := <-e.watcher.ResultChan():
			if !ok {
				e.mu.Lock()
				e.watching = false
				e.mu.Unlock()
				return
			}

			if event.Type == watch.Added || event.Type == watch.Modified {
				if k8sEvent, ok := event.Object.(*corev1.Event); ok {
					e.eventBuffer.Add(*k8sEvent)
				}
			}
		}
	}
}

// Stop stops the event watcher
func (e *EventCollector) Stop() {
	e.mu.Lock()
	defer e.mu.Unlock()

	if !e.watching {
		return
	}

	close(e.stopCh)
	if e.watcher != nil {
		e.watcher.Stop()
	}
	e.watching = false
}

// GetPodEvents retrieves and analyzes events for a specific pod
func (e *EventCollector) GetPodEvents(podName string, since time.Duration) (*PodEventSummary, error) {
	events := e.eventBuffer.GetForPod(podName, since)

	summary := &PodEventSummary{
		PodName: podName,
		Events:  make([]EventRecord, 0, len(events)),
	}

	for _, event := range events {
		eventTime := event.LastTimestamp.Time
		if eventTime.IsZero() {
			eventTime = event.EventTime.Time
		}

		record := EventRecord{
			Timestamp: eventTime,
			Type:      event.Type,
			Reason:    event.Reason,
			Message:   event.Message,
			Count:     event.Count,
		}
		summary.Events = append(summary.Events, record)

		if event.Type == "Warning" {
			summary.HasWarnings = true
		}

		// Analyze the event
		e.analyzeEvent(summary, &event)
	}

	// Calculate image pull duration
	if summary.ImagePullStart != nil && summary.ImagePullEnd != nil {
		summary.ImagePullDuration = summary.ImagePullEnd.Sub(*summary.ImagePullStart)
	}

	return summary, nil
}

// analyzeEvent extracts meaningful information from all event types
func (e *EventCollector) analyzeEvent(summary *PodEventSummary, event *corev1.Event) {
	eventTime := event.LastTimestamp.Time
	if eventTime.IsZero() {
		eventTime = event.EventTime.Time
	}

	msg := strings.ToLower(event.Message)

	switch event.Reason {
	// SCHEDULING EVENTS
	case "Scheduled":
		summary.ScheduledAt = &eventTime

	case "FailedScheduling":
		summary.SchedulingFailed = true
		summary.SchedulingMessage = event.Message
		summary.SchedulingReason = parseSchedulingReason(event.Message)
		summary.HasErrors = true

	case "Preempted":
		summary.Preempted = true
		summary.PreemptedBy = event.Message

	// IMAGE EVENTS
	case "Pulling":
		if summary.ImagePullStart == nil || eventTime.Before(*summary.ImagePullStart) {
			summary.ImagePullStart = &eventTime
		}

	case "Pulled":
		if summary.ImagePullEnd == nil || eventTime.After(*summary.ImagePullEnd) {
			summary.ImagePullEnd = &eventTime
		}

	case "ErrImagePull":
		summary.ImagePullErrors++
		summary.ImageErrorMessage = event.Message
		if isImageNotFoundError(event.Message) {
			summary.ImageNotFound = true
		}
		summary.HasErrors = true

	case "ImagePullBackOff":
		summary.ImagePullBackOff = true
		summary.ImagePullErrors++
		if summary.ImageErrorMessage == "" {
			summary.ImageErrorMessage = event.Message
		}
		summary.HasErrors = true

	case "ErrImageNeverPull":
		summary.ImageNotFound = true
		summary.ImagePullErrors++
		summary.ImageErrorMessage = event.Message
		summary.HasErrors = true

	case "InvalidImageName":
		summary.InvalidImageName = true
		summary.ImageErrorMessage = event.Message
		summary.HasErrors = true

	case "InspectFailed":
		summary.InspectFailed = true
		summary.ImageErrorMessage = event.Message
		summary.HasErrors = true

	case "Failed":
		// Generic failure - check what type
		if strings.Contains(msg, "pull") || strings.Contains(msg, "image") {
			summary.ImagePullErrors++
			summary.ImageErrorMessage = event.Message
			if isImageNotFoundError(event.Message) {
				summary.ImageNotFound = true
			}
		} else if strings.Contains(msg, "mount") || strings.Contains(msg, "volume") {
			summary.VolumeMountFailed = true
			summary.VolumeErrorMessage = event.Message
		} else if strings.Contains(msg, "attach") {
			summary.VolumeAttachFailed = true
			summary.VolumeErrorMessage = event.Message
		}
		summary.HasErrors = true

	// CONTAINER EVENTS
	case "Created":
		summary.ContainerCreated = true

	case "Started":
		summary.ContainerStarted = true
		summary.ContainerStartedAt = &eventTime

	case "Killing", "Killed":
		summary.ContainerKilled = true

	case "BackOff":
		summary.ContainerBackOff = true
		summary.BackOffCount += int(event.Count)
		if strings.Contains(msg, "crash") || strings.Contains(msg, "restart") {
			summary.CrashLoopBackOff = true
		}
		summary.HasErrors = true

	case "ExceededGracePeriod":
		summary.ContainerKilled = true

	// PROBE EVENTS
	case "Unhealthy":
		if strings.Contains(msg, "liveness") {
			summary.LivenessFailures += int(event.Count)
		} else if strings.Contains(msg, "readiness") {
			summary.ReadinessFailures += int(event.Count)
		} else if strings.Contains(msg, "startup") {
			summary.StartupFailures += int(event.Count)
		}
		summary.ProbeErrorMessage = event.Message
		summary.HasWarnings = true

	case "ProbeWarning":
		summary.ProbeErrorMessage = event.Message
		summary.HasWarnings = true

	// VOLUME EVENTS
	case "SuccessfulMountVolume":
		summary.VolumeMounted = true

	case "FailedMount":
		summary.VolumeMountFailed = true
		summary.VolumeErrorMessage = event.Message
		summary.HasErrors = true

	case "SuccessfulAttachVolume":
		summary.VolumeAttached = true

	case "FailedAttachVolume":
		summary.VolumeAttachFailed = true
		summary.VolumeErrorMessage = event.Message
		summary.HasErrors = true

	case "VolumeResizeFailed":
		summary.VolumeErrorMessage = event.Message
		summary.HasErrors = true

	case "ProvisioningFailed":
		summary.PVCPending = true
		summary.VolumeErrorMessage = event.Message
		summary.HasErrors = true

	// NETWORK EVENTS
	case "NetworkNotReady":
		summary.NetworkNotReady = true
		summary.NetworkErrorMessage = event.Message
		summary.HasErrors = true

	case "FailedCreatePodSandBox":
		summary.SandboxCreateFailed = true
		summary.NetworkErrorMessage = event.Message
		summary.HasErrors = true

	case "HostPortConflict":
		summary.HostPortConflict = true
		summary.NetworkErrorMessage = event.Message
		summary.HasErrors = true

	// RESOURCE EVENTS
	case "OOMKilling", "OOMKilled":
		summary.OOMKilled = true
		summary.HasErrors = true

	case "SystemOOM":
		summary.OOMKilled = true
		summary.ResourceExhausted = true
		summary.HasErrors = true

	case "Evicted":
		summary.Evicted = true
		summary.EvictionReason = event.Message
		summary.HasErrors = true

	// NODE EVENTS
	case "NodeNotReady":
		summary.NodeNotReady = true
		summary.NodeErrorMessage = event.Message
		summary.HasWarnings = true

	case "NodeSelectorMismatching", "NodeAffinityMismatch":
		summary.NodeAffinity = true
		summary.NodeErrorMessage = event.Message

	case "FailedAttachNode":
		summary.NodeErrorMessage = event.Message
		summary.HasErrors = true

	// SECURITY/ADMISSION EVENTS
	case "FailedValidation":
		summary.FailedValidation = true
		summary.ValidationMessage = event.Message
		summary.HasErrors = true

	case "FailedPostStartHook", "FailedPreStopHook":
		summary.HasWarnings = true

	// INIT CONTAINER EVENTS
	case "FailedInit":
		summary.InitContainerFailed = true
		summary.InitContainerMessage = event.Message
		summary.HasErrors = true
	}
}

// isImageNotFoundError checks if the error message indicates image not found
func isImageNotFoundError(message string) bool {
	msg := strings.ToLower(message)
	return strings.Contains(msg, "not found") ||
		strings.Contains(msg, "manifest unknown") ||
		strings.Contains(msg, "manifest not found") ||
		strings.Contains(msg, "repository does not exist") ||
		strings.Contains(msg, "pull access denied") ||
		strings.Contains(msg, "unauthorized") ||
		strings.Contains(msg, "authentication required") ||
		strings.Contains(msg, "denied") ||
		strings.Contains(msg, "forbidden") ||
		strings.Contains(msg, "404") ||
		strings.Contains(msg, "no such image") ||
		strings.Contains(msg, "image not found")
}

// parseSchedulingReason extracts the specific reason from a FailedScheduling message
func parseSchedulingReason(message string) string {
	msg := strings.ToLower(message)

	switch {
	case strings.Contains(msg, "insufficient cpu"):
		return "InsufficientCPU"
	case strings.Contains(msg, "insufficient memory"):
		return "InsufficientMemory"
	case strings.Contains(msg, "insufficient ephemeral-storage"):
		return "InsufficientStorage"
	case strings.Contains(msg, "insufficient pods"):
		return "TooManyPods"
	case strings.Contains(msg, "didn't match pod's node affinity"):
		return "NodeAffinityMismatch"
	case strings.Contains(msg, "didn't match pod anti-affinity"):
		return "PodAntiAffinityConflict"
	case strings.Contains(msg, "node(s) had taint"):
		return "TaintToleration"
	case strings.Contains(msg, "persistentvolumeclaim"):
		return "PVCNotBound"
	case strings.Contains(msg, "pod disruption budget"):
		return "PDBViolation"
	case strings.Contains(msg, "unschedulable"):
		return "NodeUnschedulable"
	case strings.Contains(msg, "node selector"):
		return "NodeSelectorMismatch"
	case strings.Contains(msg, "didn't have free ports"):
		return "PortConflict"
	case strings.Contains(msg, "had volume node affinity conflict"):
		return "VolumeNodeAffinityConflict"
	case strings.Contains(msg, "exceeds the available"):
		return "ResourceQuotaExceeded"
	case strings.Contains(msg, "didn't match pod topology spread"):
		return "TopologySpreadConstraint"
	default:
		return "Unknown"
	}
}

// GetPodEventsDirectly fetches events directly from API
func (e *EventCollector) GetPodEventsDirectly(ctx context.Context, podName string) (*PodEventSummary, error) {
	events, err := e.clientset.CoreV1().Events(e.namespace).List(ctx, metav1.ListOptions{
		FieldSelector: fmt.Sprintf("involvedObject.name=%s", podName),
	})
	if err != nil {
		return nil, fmt.Errorf("failed to list events for pod %s: %w", podName, err)
	}

	summary := &PodEventSummary{
		PodName: podName,
		Events:  make([]EventRecord, 0, len(events.Items)),
	}

	for _, event := range events.Items {
		eventTime := event.LastTimestamp.Time
		if eventTime.IsZero() {
			eventTime = event.EventTime.Time
		}

		record := EventRecord{
			Timestamp: eventTime,
			Type:      event.Type,
			Reason:    event.Reason,
			Message:   event.Message,
			Count:     event.Count,
		}
		summary.Events = append(summary.Events, record)

		if event.Type == "Warning" {
			summary.HasWarnings = true
		}

		e.analyzeEvent(summary, &event)
	}

	if summary.ImagePullStart != nil && summary.ImagePullEnd != nil {
		summary.ImagePullDuration = summary.ImagePullEnd.Sub(*summary.ImagePullStart)
	}

	return summary, nil
}
