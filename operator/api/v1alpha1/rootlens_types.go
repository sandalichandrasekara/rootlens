/*
Copyright 2026.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

package v1alpha1

import (
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// RootLensSpec defines the desired state of RootLens.
type RootLensSpec struct {
	// Version of RootLens to deploy
	// +kubebuilder:default="latest"
	Version string `json:"version,omitempty"`

	// ImagePullPolicy for all containers
	// +kubebuilder:default="IfNotPresent"
	// +kubebuilder:validation:Enum=Always;IfNotPresent;Never
	ImagePullPolicy corev1.PullPolicy `json:"imagePullPolicy,omitempty"`

	// ImagePullSecrets for private registries
	ImagePullSecrets []corev1.LocalObjectReference `json:"imagePullSecrets,omitempty"`

	// Components configuration
	Components ComponentsSpec `json:"components,omitempty"`

	// RCA configuration for root cause analysis
	RCA RCASpec `json:"rca,omitempty"`

	// Scaling configuration for KEDA integration
	Scaling ScalingSpec `json:"scaling,omitempty"`

	// Networking configuration
	Networking NetworkingSpec `json:"networking,omitempty"`

	// RabbitMQ connection configuration (for external RabbitMQ)
	RabbitMQ RabbitMQSpec `json:"rabbitmq,omitempty"`

	// Monitoring configuration for Prometheus/Grafana integration
	Monitoring MonitoringSpec `json:"monitoring,omitempty"`
}

// MonitoringSpec defines Prometheus/Grafana monitoring configuration.
type MonitoringSpec struct {
	// Enable ServiceMonitor creation for Prometheus Operator
	// +kubebuilder:default=false
	Enabled bool `json:"enabled,omitempty"`

	// Prometheus scrape interval
	// +kubebuilder:default="30s"
	ScrapeInterval string `json:"scrapeInterval,omitempty"`

	// Additional labels for ServiceMonitor (for Prometheus selector)
	Labels map[string]string `json:"labels,omitempty"`
}

// ComponentsSpec defines configuration for each RootLens component.
type ComponentsSpec struct {
	// API server configuration
	API APIComponentSpec `json:"api,omitempty"`

	// ML service configuration
	MLService MLServiceSpec `json:"mlService,omitempty"`

	// Dashboard configuration
	Dashboard DashboardSpec `json:"dashboard,omitempty"`

	// Consumer configuration
	Consumer ConsumerSpec `json:"consumer,omitempty"`

	// Internal RabbitMQ configuration (set enabled=false to use external)
	InternalRabbitMQ InternalRabbitMQSpec `json:"internalRabbitMQ,omitempty"`
}

// APIComponentSpec defines the API server configuration.
type APIComponentSpec struct {
	// Number of replicas
	// +kubebuilder:default=1
	// +kubebuilder:validation:Minimum=1
	Replicas int32 `json:"replicas,omitempty"`

	// Container image
	// +kubebuilder:default="rootlens-api:latest"
	Image string `json:"image,omitempty"`

	// Resource requirements
	Resources corev1.ResourceRequirements `json:"resources,omitempty"`

	// Additional environment variables
	Env []corev1.EnvVar `json:"env,omitempty"`
}

// MLServiceSpec defines the ML service configuration.
type MLServiceSpec struct {
	// Enable ML service
	// +kubebuilder:default=true
	Enabled bool `json:"enabled,omitempty"`

	// Number of replicas
	// +kubebuilder:default=1
	// +kubebuilder:validation:Minimum=0
	Replicas int32 `json:"replicas,omitempty"`

	// Container image
	// +kubebuilder:default="rootlens-ml:latest"
	Image string `json:"image,omitempty"`

	// Resource requirements
	Resources corev1.ResourceRequirements `json:"resources,omitempty"`

	// ML inference timeout in seconds
	// +kubebuilder:default=2
	TimeoutSeconds int `json:"timeoutSeconds,omitempty"`
}

// DashboardSpec defines the Dashboard configuration.
type DashboardSpec struct {
	// Enable dashboard
	// +kubebuilder:default=true
	Enabled bool `json:"enabled,omitempty"`

	// Number of replicas
	// +kubebuilder:default=1
	// +kubebuilder:validation:Minimum=0
	Replicas int32 `json:"replicas,omitempty"`

	// Container image
	// +kubebuilder:default="rootlens-dashboard:latest"
	Image string `json:"image,omitempty"`

	// Resource requirements
	Resources corev1.ResourceRequirements `json:"resources,omitempty"`
}

// ConsumerSpec defines the Consumer configuration.
type ConsumerSpec struct {
	// Enable consumer
	// +kubebuilder:default=true
	Enabled bool `json:"enabled,omitempty"`

	// Container image
	// +kubebuilder:default="rabbitmq-consumer:latest"
	Image string `json:"image,omitempty"`

	// Resource requirements
	Resources corev1.ResourceRequirements `json:"resources,omitempty"`
}

// InternalRabbitMQSpec defines internal RabbitMQ configuration.
type InternalRabbitMQSpec struct {
	// Deploy internal RabbitMQ (set false to use external)
	// +kubebuilder:default=true
	Enabled bool `json:"enabled,omitempty"`

	// Number of replicas (StatefulSet)
	// +kubebuilder:default=1
	// +kubebuilder:validation:Minimum=1
	Replicas int32 `json:"replicas,omitempty"`

	// Storage size for PVC
	// +kubebuilder:default="1Gi"
	Storage string `json:"storage,omitempty"`

	// Storage class name
	StorageClassName string `json:"storageClassName,omitempty"`

	// Resource requirements
	Resources corev1.ResourceRequirements `json:"resources,omitempty"`
}

// RabbitMQSpec defines RabbitMQ connection configuration.
type RabbitMQSpec struct {
	// RabbitMQ host (auto-set if using internal RabbitMQ)
	Host string `json:"host,omitempty"`

	// RabbitMQ port
	// +kubebuilder:default=5672
	Port int `json:"port,omitempty"`

	// Queue name
	// +kubebuilder:default="rootlens-tasks"
	Queue string `json:"queue,omitempty"`

	// Username
	// +kubebuilder:default="admin"
	Username string `json:"username,omitempty"`

	// VHost is the RabbitMQ virtual host
	// +kubebuilder:default="/"
	VHost string `json:"vhost,omitempty"`

	// TLS enables TLS/AMQPS connections (required for CloudAMQP and other managed services)
	// +kubebuilder:default=false
	TLS bool `json:"tls,omitempty"`

	// Password secret reference (recommended for production)
	PasswordSecret corev1.SecretKeySelector `json:"passwordSecret,omitempty"`

	// Password (plain text - use passwordSecret in production instead)
	// WARNING: No default - must be explicitly set or use passwordSecret
	Password string `json:"password,omitempty"`
}

// RCASpec defines RCA engine configuration.
type RCASpec struct {
	// Cold start threshold in seconds
	// +kubebuilder:default=2
	ColdStartThreshold int `json:"coldStartThreshold,omitempty"`

	// Scheduling threshold in seconds
	// +kubebuilder:default=1
	SchedulingThreshold int `json:"schedulingThreshold,omitempty"`

	// Metric lag threshold in seconds
	// +kubebuilder:default=5
	MetricLagThreshold int `json:"metricLagThreshold,omitempty"`

	// Weight for rule-based confidence (0.0-1.0, should sum with MLWeight to ~1.0)
	// +kubebuilder:default="0.6"
	// +kubebuilder:validation:Pattern=`^(0(\.\d+)?|1(\.0+)?)$`
	RuleWeight string `json:"ruleWeight,omitempty"`

	// Weight for ML confidence (0.0-1.0, should sum with RuleWeight to ~1.0)
	// +kubebuilder:default="0.4"
	// +kubebuilder:validation:Pattern=`^(0(\.\d+)?|1(\.0+)?)$`
	MLWeight string `json:"mlWeight,omitempty"`
}

// ScalingSpec defines KEDA scaling configuration.
type ScalingSpec struct {
	// Enable KEDA auto-scaling for consumer
	// +kubebuilder:default=true
	Enabled bool `json:"enabled,omitempty"`

	// Minimum consumer replicas
	// +kubebuilder:default=0
	// +kubebuilder:validation:Minimum=0
	MinReplicas int32 `json:"minReplicas,omitempty"`

	// Maximum consumer replicas
	// +kubebuilder:default=10
	// +kubebuilder:validation:Minimum=1
	MaxReplicas int32 `json:"maxReplicas,omitempty"`

	// Messages per pod threshold
	// +kubebuilder:default=50
	MessagesPerPod int `json:"messagesPerPod,omitempty"`

	// KEDA polling interval in seconds
	// +kubebuilder:default=5
	PollingInterval int `json:"pollingInterval,omitempty"`

	// Cooldown period in seconds
	// +kubebuilder:default=30
	CooldownPeriod int `json:"cooldownPeriod,omitempty"`
}

// NetworkingSpec defines networking configuration.
type NetworkingSpec struct {
	// Dashboard service type
	// +kubebuilder:default="LoadBalancer"
	// +kubebuilder:validation:Enum=ClusterIP;NodePort;LoadBalancer
	DashboardServiceType corev1.ServiceType `json:"dashboardServiceType,omitempty"`

	// Dashboard NodePort (when using NodePort)
	DashboardNodePort int32 `json:"dashboardNodePort,omitempty"`

	// API service type
	// +kubebuilder:default="ClusterIP"
	// +kubebuilder:validation:Enum=ClusterIP;NodePort;LoadBalancer
	APIServiceType corev1.ServiceType `json:"apiServiceType,omitempty"`

	// API NodePort (when using NodePort)
	APINodePort int32 `json:"apiNodePort,omitempty"`

	// Enable ingress
	Ingress IngressSpec `json:"ingress,omitempty"`
}

// IngressSpec defines ingress configuration.
type IngressSpec struct {
	// Enable ingress
	Enabled bool `json:"enabled,omitempty"`

	// Ingress class name
	// +kubebuilder:default="nginx"
	ClassName string `json:"className,omitempty"`

	// Dashboard hostname
	DashboardHost string `json:"dashboardHost,omitempty"`

	// API hostname
	APIHost string `json:"apiHost,omitempty"`

	// TLS configuration
	TLS []IngressTLS `json:"tls,omitempty"`

	// Additional annotations
	Annotations map[string]string `json:"annotations,omitempty"`
}

// IngressTLS defines TLS configuration for ingress.
type IngressTLS struct {
	// Hosts covered by TLS
	Hosts []string `json:"hosts,omitempty"`

	// Secret name containing TLS cert
	SecretName string `json:"secretName,omitempty"`
}

// RootLensStatus defines the observed state of RootLens.
type RootLensStatus struct {
	// Current phase of the RootLens deployment
	// +kubebuilder:validation:Enum=Pending;Deploying;Running;Degraded;Failed
	Phase string `json:"phase,omitempty"`

	// Human-readable message about current state
	Message string `json:"message,omitempty"`

	// Conditions for each component
	Conditions []metav1.Condition `json:"conditions,omitempty"`

	// Component statuses
	ComponentStatuses ComponentStatuses `json:"componentStatuses,omitempty"`

	// Dashboard URL (when available)
	DashboardURL string `json:"dashboardURL,omitempty"`

	// API endpoint (internal)
	APIEndpoint string `json:"apiEndpoint,omitempty"`

	// Observed generation
	ObservedGeneration int64 `json:"observedGeneration,omitempty"`

	// Last reconciliation time
	LastReconcileTime *metav1.Time `json:"lastReconcileTime,omitempty"`
}

// ComponentStatuses tracks replica counts for each component.
type ComponentStatuses struct {
	API       ReplicaStatus `json:"api,omitempty"`
	MLService ReplicaStatus `json:"mlService,omitempty"`
	Dashboard ReplicaStatus `json:"dashboard,omitempty"`
	Consumer  ReplicaStatus `json:"consumer,omitempty"`
	RabbitMQ  ReplicaStatus `json:"rabbitmq,omitempty"`
}

// ReplicaStatus tracks ready vs desired replicas.
type ReplicaStatus struct {
	Ready   int32 `json:"ready"`
	Desired int32 `json:"desired"`
}

// Phase constants
const (
	PhasePending   = "Pending"
	PhaseDeploying = "Deploying"
	PhaseRunning   = "Running"
	PhaseDegraded  = "Degraded"
	PhaseFailed    = "Failed"
)

// Condition types
const (
	ConditionRabbitMQReady  = "RabbitMQReady"
	ConditionAPIReady       = "APIReady"
	ConditionMLServiceReady = "MLServiceReady"
	ConditionDashboardReady = "DashboardReady"
	ConditionConsumerReady  = "ConsumerReady"
	ConditionKEDAReady      = "KEDAReady"
)

// +kubebuilder:object:root=true
// +kubebuilder:subresource:status
// +kubebuilder:printcolumn:name="Phase",type="string",JSONPath=".status.phase",description="Current phase"
// +kubebuilder:printcolumn:name="Dashboard",type="string",JSONPath=".status.dashboardURL",description="Dashboard URL"
// +kubebuilder:printcolumn:name="Age",type="date",JSONPath=".metadata.creationTimestamp"

// RootLens is the Schema for the rootlens API.
type RootLens struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata,omitempty"`

	Spec   RootLensSpec   `json:"spec,omitempty"`
	Status RootLensStatus `json:"status,omitempty"`
}

// +kubebuilder:object:root=true

// RootLensList contains a list of RootLens.
type RootLensList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata,omitempty"`
	Items           []RootLens `json:"items"`
}

func init() {
	SchemeBuilder.Register(&RootLens{}, &RootLensList{})
}
