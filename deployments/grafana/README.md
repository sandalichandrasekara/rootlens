# Grafana Dashboard

> Pre-built dashboard for monitoring RootLens RCA activity and ML service health.

## Setup

### Minikube (automated)

```bash
./scripts/setup-monitoring.sh
```

Installs kube-prometheus-stack via Helm, applies the `ServiceMonitor`, and provisions this dashboard as a ConfigMap. Grafana opens on NodePort 32000.

### Manual import

1. Grafana → **Dashboards** → **Import**
2. Upload `rootlens-dashboard.json`
3. Select your Prometheus datasource → **Import**

## Metrics Reference

| Metric | Description |
|--------|-------------|
| `rootlens_rca_analysis_total` | Total analyses by root cause |
| `rootlens_rca_analysis_duration_seconds` | RCA latency histogram |
| `rootlens_rca_confidence` | Current confidence scores |
| `rootlens_ml_service_available` | ML service availability (1/0) |
| `rootlens_ml_requests_total` | ML requests by explainer and status |
| `rootlens_queue_depth` | Current RabbitMQ queue depth |
| `rootlens_keda_desired_replicas` | KEDA desired replica count |
| `rootlens_api_requests_total` | API requests by endpoint and status |

All metrics exposed at `GET /metrics` on the API pod.

## Dashboard Panels

1. **Overview** — ML service status (0/1), RCA analyses (1h), queue depth, API requests (1h)
2. **Root Cause Analysis** — root cause distribution (pie chart), confidence over time, analysis duration p95
3. **API Performance** — request rate by endpoint and HTTP status
