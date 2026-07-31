# RootLens Operator

> Kubernetes operator that deploys and manages the complete RootLens stack.

The operator reconciles a `RootLens` custom resource into Deployments, Services, KEDA ScaledObject, ConfigMap, Secret, Ingress, ServiceMonitor, and PodDisruptionBudget.

## Quick Start

```bash
# Install via Helm (OCI registry)
helm install rootlens-operator \
  oci://ghcr.io/sandalichandrasekara/charts/rootlens-operator \
  --namespace rootlens-system --create-namespace

# Apply a RootLens instance
kubectl apply -f config/samples/rca_v1alpha1_rootlens.yaml

# Watch reconciliation
kubectl get rootlens -n rootlens-system -w
```

## CRD Reference

```yaml
apiVersion: rca.rootlens.io/v1alpha1
kind: RootLens
metadata:
  name: rootlens
  namespace: rootlens-system
spec:
  # Component images
  components:
    api:
      replicas: 1
      image: ghcr.io/sandalichandrasekara/rootlens-api:latest
      resources: {}         
    mlService:
      enabled: true
      image: ghcr.io/sandalichandrasekara/rootlens-ml:latest
      timeoutSeconds: 2
    dashboard:
      enabled: true
      image: ghcr.io/sandalichandrasekara/rootlens-dashboard:latest
    consumer:
      enabled: true
      image: ghcr.io/sandalichandrasekara/rabbitmq-consumer:latest
    internalRabbitMQ:
      enabled: false         

  # RabbitMQ connection (external)
  rabbitmq:
    host: puffin.rmq2.cloudamqp.com
    port: 5671
    username: myuser
    vhost: myvhost
    tls: true
    queue: rootlens-tasks
    passwordSecret:         ]
      name: rabbitmq-secret
      key: password

  # RCA engine thresholds
  rca:
    coldStartThreshold: 2    # seconds
    schedulingThreshold: 1   # seconds
    metricLagThreshold: 5    # seconds
    ruleWeight: "0.6"
    mlWeight: "0.4"

  # KEDA autoscaling
  scaling:
    enabled: true
    minReplicas: 0
    maxReplicas: 10
    messagesPerPod: 50
    pollingInterval: 5
    cooldownPeriod: 30

  # Networking
  networking:
    dashboardServiceType: LoadBalancer  # ClusterIP | NodePort | LoadBalancer
    apiServiceType: ClusterIP
    ingress:
      enabled: false
      className: nginx
      dashboardHost: rootlens.example.com
      apiHost: rootlens-api.example.com

  # Prometheus monitoring
  monitoring:
    enabled: true
    scrapeInterval: 30s
```

## What Gets Created

| Resource | Name pattern |
|----------|-------------|
| Deployment | `{name}-api`, `{name}-ml-service`, `{name}-dashboard`, `{name}-consumer` |
| StatefulSet | `{name}-rabbitmq` (if internalRabbitMQ.enabled) |
| Service | Same as deployments |
| ConfigMap | `{name}-config` |
| Secret | `{name}-secret` |
| KEDA ScaledObject | `{name}-consumer-scaledobject` |
| KEDA TriggerAuthentication | `{name}-rabbitmq-auth` |
| Ingress | `{name}-ingress` (if enabled) |
| ServiceMonitor | `{name}-api` (if monitoring.enabled) |
| PodDisruptionBudget | `{name}-api` |

All resources are owned by the `RootLens` resource — deleting the CR deletes everything.

## Development

```bash
cd operator

# Install dependencies and generate code
make generate manifests

# Run tests
make test

# Run operator locally against a cluster
make install   # install CRDs
make run       # run controller locally

# Build and push Docker image
make docker-build docker-push IMG=ghcr.io/sandalichandrasekara/rootlens-operator:latest
```

## Helm Chart

```bash
# Lint
helm lint helm/rootlens-operator

# Install from local chart
helm install rootlens-operator helm/rootlens-operator \
  --namespace rootlens-system --create-namespace

# Key values
helm show values helm/rootlens-operator
```

## CI/CD

`.github/workflows/operator.yml` runs on pushes to `devops/test` and PRs to `main`:

1. `test` — `golangci-lint` + `make test`
2. `build` — builds and pushes Docker image to GHCR
3. `helm` — packages and pushes Helm chart to GHCR OCI registry
4. `e2e` — Kind cluster test (on release only)
