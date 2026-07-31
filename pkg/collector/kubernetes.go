package collector

import (
	"context"
	"fmt"
	"time"

	"github.com/sandalichandrasekara/rootlens/pkg/types"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/tools/clientcmd"
)

type K8sCollector struct {
	clientset      *kubernetes.Clientset
	namespace      string
	eventCollector *EventCollector
}

func NewK8sCollector(kubeconfigPath, namespace string) (*K8sCollector, error) {
	config, err := clientcmd.BuildConfigFromFlags("", kubeconfigPath)
	if err != nil {
		return nil, fmt.Errorf("failed to build kubeconfig: %w", err)
	}

	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		return nil, fmt.Errorf("failed to create clientset: %w", err)
	}

	collector := &K8sCollector{
		clientset: clientset,
		namespace: namespace,
	}

	// Create EventCollector using the same clientset
	collector.eventCollector = NewEventCollectorWithClientset(clientset, namespace)

	return collector, nil
}

// SetEventCollector allows setting a custom event collector
func (k *K8sCollector) SetEventCollector(ec *EventCollector) {
	k.eventCollector = ec
}

// GetEventCollector returns the event collector (useful for starting/stopping watching)
func (k *K8sCollector) GetEventCollector() *EventCollector {
	return k.eventCollector
}

func (k *K8sCollector) CollectPodMetrics(labelSelector string) ([]types.K8sMetrics, error) {
	ctx := context.Background()

	pods, err := k.clientset.CoreV1().Pods(k.namespace).List(ctx, metav1.ListOptions{
		LabelSelector: labelSelector,
	})
	if err != nil {
		return nil, fmt.Errorf("failed to list pods: %w", err)
	}

	var metrics []types.K8sMetrics

	for _, pod := range pods.Items {
		metric := types.K8sMetrics{
			PodName:  pod.Name,
			Phase:    string(pod.Status.Phase),
			NodeName: pod.Spec.NodeName,
		}

		// Get scheduling time
		for _, condition := range pod.Status.Conditions {
			if condition.Type == corev1.PodScheduled && condition.Status == corev1.ConditionTrue {
				metric.ScheduledTime = &condition.LastTransitionTime.Time
			}
		}

		// Get container start time
		if len(pod.Status.ContainerStatuses) > 0 {
			if pod.Status.ContainerStatuses[0].State.Running != nil {
				startTime := pod.Status.ContainerStatuses[0].State.Running.StartedAt.Time
				metric.ContainerStartTime = &startTime
			}
		}

		// Get ready time
		for _, condition := range pod.Status.Conditions {
			if condition.Type == corev1.PodReady && condition.Status == corev1.ConditionTrue {
				metric.ReadyTime = &condition.LastTransitionTime.Time
			}
		}

		// Extract init container duration from pod status
		metric.InitContainerDuration = k.calculateInitContainerDuration(&pod)

		// Get event-derived metrics if EventCollector is available
		if k.eventCollector != nil {
			k.enrichWithEventMetrics(ctx, &metric, pod.Name)
		}

		metrics = append(metrics, metric)
	}

	return metrics, nil
}

// calculateInitContainerDuration calculates total time spent in init containers
func (k *K8sCollector) calculateInitContainerDuration(pod *corev1.Pod) time.Duration {
	if len(pod.Status.InitContainerStatuses) == 0 {
		return 0
	}

	var totalDuration time.Duration
	for _, initStatus := range pod.Status.InitContainerStatuses {
		// Check if init container has terminated
		if initStatus.State.Terminated != nil {
			started := initStatus.State.Terminated.StartedAt.Time
			finished := initStatus.State.Terminated.FinishedAt.Time
			if !started.IsZero() && !finished.IsZero() {
				totalDuration += finished.Sub(started)
			}
		}
	}

	return totalDuration
}

// enrichWithEventMetrics adds event-derived metrics to the K8sMetrics
func (k *K8sCollector) enrichWithEventMetrics(ctx context.Context, metric *types.K8sMetrics, podName string) {
	// Try to get events from buffer first (faster), fall back to direct API call
	eventSummary, err := k.eventCollector.GetPodEvents(podName, 10*time.Minute)
	if err != nil || len(eventSummary.Events) == 0 {
		// Fall back to direct API call
		eventSummary, err = k.eventCollector.GetPodEventsDirectly(ctx, podName)
		if err != nil {
			return // Silently skip if events unavailable
		}
	}

	// Populate event-derived fields
	metric.ImagePullDuration = eventSummary.ImagePullDuration
	metric.ImagePullErrors = eventSummary.ImagePullErrors
	metric.ImageNotFound = eventSummary.ImageNotFound
	metric.ImagePullBackOff = eventSummary.ImagePullBackOff
	metric.ImageErrorMessage = eventSummary.ImageErrorMessage
	metric.ReadinessProbeFailures = eventSummary.ReadinessFailures
	metric.SchedulingFailureReason = eventSummary.SchedulingReason
}
