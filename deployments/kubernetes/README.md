# Kubernetes Manifests

> Raw manifests for local Minikube development only. For production, use the [RootLens Operator](../../operator/README.md).

## Usage

```bash
# Point Docker to Minikube's daemon
eval $(minikube docker-env)

# Build images locally
docker build -t rootlens-api:latest .
docker build -t rootlens-dashboard:latest ./dashboard
docker build -t rootlens-ml-service:latest ./ml-integration

# Deploy
kubectl apply -f deployments/kubernetes/
```

## Limitations

- `imagePullPolicy: IfNotPresent` — requires locally built images
- No reconciliation — changes must be applied manually

## Files

| File | Resource |
|------|----------|
| `configmap.yaml` | API configuration |
| `api-deployment.yaml` | RootLens API |
| `ml-service-deployment.yaml` | ML explainer service |
| `dashboard-deployment.yaml` | React dashboard |
| `consumer-deployment.yaml` | RabbitMQ consumer |
| `keda-scaledobject.yaml` | KEDA autoscaler |
| `rabbitmq.yaml` | RabbitMQ (local) |
| `monitoring.yaml` | ServiceMonitor for Prometheus scraping |
