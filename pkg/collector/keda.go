package collector

import (
	"context"
	"fmt"
	"strconv"
	"time"

	"github.com/sandalichandrasekara/rootlens/pkg/types"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime/schema"
	"k8s.io/client-go/dynamic"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/tools/clientcmd"
)

type KEDACollector struct {
	dynamicClient dynamic.Interface
	clientset     *kubernetes.Clientset
	namespace     string
}

func NewKEDACollector(kubeconfigPath, namespace string) (*KEDACollector, error) {
	config, err := clientcmd.BuildConfigFromFlags("", kubeconfigPath)
	if err != nil {
		return nil, fmt.Errorf("failed to build kubeconfig: %w", err)
	}

	dynamicClient, err := dynamic.NewForConfig(config)
	if err != nil {
		return nil, fmt.Errorf("failed to create dynamic client: %w", err)
	}

	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		return nil, fmt.Errorf("failed to create clientset: %w", err)
	}

	return &KEDACollector{
		dynamicClient: dynamicClient,
		clientset:     clientset,
		namespace:     namespace,
	}, nil
}

func (k *KEDACollector) Collect(scaledObjectName string) (*types.KEDAMetrics, error) {
	ctx := context.Background()

	metrics := &types.KEDAMetrics{
		ScalerName: scaledObjectName,
		KEDAConfig: &types.ScaledObjectConfig{},
	}

	gvr := schema.GroupVersionResource{
		Group:    "keda.sh",
		Version:  "v1alpha1",
		Resource: "scaledobjects",
	}

	scaledObject, err := k.dynamicClient.
		Resource(gvr).
		Namespace(k.namespace).
		Get(ctx, scaledObjectName, metav1.GetOptions{})
	if err != nil {
		return nil, fmt.Errorf("failed to get ScaledObject: %w", err)
	}

	spec, specFound, _ := unstructuredNestedMap(scaledObject.Object, "spec")
	if specFound {
		if v, ok := spec["minReplicaCount"].(int64); ok {
			metrics.KEDAConfig.MinReplicas = int(v)
		}

		if v, ok := spec["maxReplicaCount"].(int64); ok {
			metrics.KEDAConfig.MaxReplicas = int(v)
		}

		if v, ok := spec["pollingInterval"].(int64); ok {
			metrics.KEDAConfig.PollingInterval = int(v)
		} else {
			metrics.KEDAConfig.PollingInterval = 30
		}

		if v, ok := spec["cooldownPeriod"].(int64); ok {
			metrics.KEDAConfig.CooldownPeriod = int(v)
		} else {
			metrics.KEDAConfig.CooldownPeriod = 300
		}

		if triggers, ok := spec["triggers"].([]interface{}); ok && len(triggers) > 0 {
			if trigger, ok := triggers[0].(map[string]interface{}); ok {
				if t, ok := trigger["type"].(string); ok {
					metrics.KEDAConfig.TriggerType = t
				}

				if metadata, ok := trigger["metadata"].(map[string]interface{}); ok {
					if ql, ok := metadata["queueLength"].(string); ok {
						if v, err := strconv.Atoi(ql); err == nil {
							metrics.KEDAConfig.TriggerThreshold = v
						}
					}
					if val, ok := metadata["value"].(string); ok {
						if v, err := strconv.Atoi(val); err == nil {
							metrics.KEDAConfig.TriggerThreshold = v
						}
					}
				}
			}
		}
	}

	status, statusFound, _ := unstructuredNestedMap(scaledObject.Object, "status")
	if statusFound {
		if lastActive, ok := status["lastActiveTime"].(string); ok {
			if t, err := time.Parse(time.RFC3339, lastActive); err == nil {
				metrics.LastScalingEvent = t
			}
		}

		if conditions, ok := status["conditions"].([]interface{}); ok {
			for _, c := range conditions {
				cond, ok := c.(map[string]interface{})
				if !ok {
					continue
				}

				condType, _ := cond["type"].(string)
				condStatus, _ := cond["status"].(string)

				switch condType {
				case "Ready":
					metrics.KEDAConfig.IsReady = condStatus == "True"
				case "Active":
					metrics.KEDAConfig.IsActive = condStatus == "True"
				case "Paused":
					metrics.KEDAConfig.IsPaused = condStatus == "True"
				}
			}
		}
	}

	specRef, _, _ := unstructuredNestedMap(scaledObject.Object, "spec")
	var deploymentName string
	if scaleTargetRef, ok := specRef["scaleTargetRef"].(map[string]interface{}); ok {
		if name, ok := scaleTargetRef["name"].(string); ok {
			deploymentName = name
		}
	}

	if deploymentName != "" {
		deployment, err := k.clientset.
			AppsV1().
			Deployments(k.namespace).
			Get(ctx, deploymentName, metav1.GetOptions{})
		if err == nil {
			metrics.CurrentReplicas = int(deployment.Status.ReadyReplicas)
			if deployment.Spec.Replicas != nil {
				metrics.DesiredReplicas = int(*deployment.Spec.Replicas)
			}
		}
	}

	hpaName := fmt.Sprintf("keda-hpa-%s", scaledObjectName)
	hpa, err := k.clientset.
		AutoscalingV2().
		HorizontalPodAutoscalers(k.namespace).
		Get(ctx, hpaName, metav1.GetOptions{})
	if err == nil {
		metrics.DesiredReplicas = int(hpa.Status.DesiredReplicas)
		metrics.CurrentReplicas = int(hpa.Status.CurrentReplicas)
	}

	return metrics, nil
}

// Helper: extract nested map from unstructured object
func unstructuredNestedMap(
	obj map[string]interface{},
	fields ...string,
) (map[string]interface{}, bool, error) {

	var current interface{} = obj
	for _, field := range fields {
		if m, ok := current.(map[string]interface{}); ok {
			current = m[field]
		} else {
			return nil, false, nil
		}
	}

	if result, ok := current.(map[string]interface{}); ok {
		return result, true, nil
	}

	return nil, false, nil
}
