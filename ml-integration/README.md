# ML Explainer Service

> Flask service providing ML-powered sub-cause identification for the RootLens RCA engine.

Three RandomForest models — one per root cause category — each trained on real Kubernetes experimental data to classify the specific sub-cause within a detected root cause.

## Quick Start

```bash
cd ml-integration
pip install -r requirements.txt

# Run with gunicorn (production)
gunicorn --bind :5000 --workers 1 --threads 2 predictor_service:app

# Run with Flask dev server (development)
python predictor_service.py
```

Docker:
```bash
docker build -f Dockerfile -t rootlens-ml .
docker run -p 5000:5000 rootlens-ml
```

## API Endpoints

### `GET /health`

```json
{ "status": "healthy", "explainers": { "cold_start": true, "scheduling": true, "metric_propagation": true } }
```

### `POST /explain/cold-start`

```json
{
  "metrics": {
    "cold_start_duration": 3.5,
    "image_pull_duration": 2.1,
    "image_size_estimate_mb": 850,
    "image_pull_errors": 0,
    "image_not_found": 0,
    "image_pull_backoff": 0,
    "readiness_probe_failures": 2,
    "init_container_duration": 0.5,
    "container_backoff": 0,
    "crash_loop_backoff": 0,
    "restart_count": 0,
    "scheduling_duration": 0.2,
    "queue_depth": 5000,
    "desired_replicas": 5,
    "current_replicas": 1
  }
}
```

### `POST /explain/scheduling`

```json
{
  "metrics": {
    "scheduling_duration": 2.5,
    "scheduling_failure_encoded": 2,
    "cpu_request_millicores": 500,
    "memory_request_mb": 256,
    "node_selector_present": 0,
    "preempted": 0,
    "node_affinity_mismatch": 0,
    "pvc_pending": 0,
    "queue_depth": 3000,
    "desired_replicas": 4,
    "current_replicas": 1
  }
}
```

### `POST /explain/metric-propagation`

```json
{
  "metrics": {
    "metric_lag_seconds": 8.0,
    "queue_depth_at_lag": 1000,
    "keda_polling_interval": 5,
    "message_rate": 200.0,
    "desired_replicas": 2,
    "current_replicas": 1,
    "consumer_count": 1,
    "time_since_last_scale": 8.0,
    "keda_cooldown_period": 30,
    "queue_message_rate_delta": 150.0
  }
}
```

### Response format (all explainers)

```json
{
  "sub_cause": "large_image",
  "confidence": 0.91,
  "probabilities": { "large_image": 0.91, "slow_registry": 0.06, "readiness_probe_failure": 0.03 },
  "explanation": { "image_size_estimate_mb": 0.42, "image_pull_duration": 0.31, ... },
  "recommendations": ["Use multi-stage builds to reduce image size", "Consider a local registry mirror"],
  "success": true
}
```

`explanation` contains global feature importances from the RandomForest model (not per-instance SHAP).

## Models

| Model | Algorithm | Features | Sub-causes | Training samples |
|-------|-----------|----------|------------|-----------------|
| Cold Start | RandomForest | 15 | 5 | 42 train / 8 test |
| Scheduling | RandomForest | 11 | 5 | 42 train / 8 test |
| Metric Propagation | RandomForest | 10 | 4 | 34 train / 6 test |

Training data: real Kubernetes experiments on minikube with ground-truth labels. Models stored in `results/explainers/`.

## Retraining

```bash
python train_cold_start_explainer.py
python train_scheduling_explainer.py
python train_metric_propagation_explainer.py
```

Models are saved to `results/explainers/` and picked up automatically on next service start.

## Graceful Degradation

- If a model file is missing → that explainer returns `success: false`, confidence 0
- If the ML service is unreachable from the API → API falls back to rule-based only (`method_agreement: "ml_unavailable"`)
- If confidence is 0 or sub-cause is empty → API uses rule-based confidence alone

## Configuration

| Env var | Default | Description |
|---------|---------|-------------|
| `PORT` | `5000` | Listening port |
| `FLASK_DEBUG` | `False` | Enable debug mode |
