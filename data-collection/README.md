# Data Collection

> Scripts for collecting real Kubernetes training data for the ML sub-cause explainer models.

## Overview

Three experiment scripts trigger specific sub-causes in a live cluster, collect metrics, then convert raw data to feature vectors for model training.

| Category | Features | Sub-causes | Samples collected |
|----------|----------|------------|-------------------|
| Cold Start | 15 | 5 | 50 |
| Scheduling | 11 | 5 | 50 |
| Metric Propagation | 10 | 4 | 40 |

## Prerequisites

```bash
# Verify cluster readiness
kubectl get pods -n rabbitmq
kubectl get pods -n keda
kubectl get scaledobjects -n default

# Install Python dependencies
pip install pika kubernetes pyyaml requests

# Port-forward RabbitMQ management API
kubectl port-forward -n rabbitmq svc/rabbitmq 15672:15672 &
```

## Run Experiments

```bash
python3 run_cold_start_subcause_experiments.py
python3 run_scheduling_subcause_experiments.py
python3 run_metric_propagation_subcause_experiments.py
```

Raw JSON output goes to `raw_data/{category}_subcauses/`.

## Convert to Features

```bash
python3 convert_cold_start_features.py
python3 convert_scheduling_features.py
python3 convert_metric_propagation_features.py
```

Output: `features/{category}/*.npz` (train/val/test splits) + `*_metadata.json`.

## Copy to ML Integration

```bash
cp features/cold_start/* ../ml-integration/data/cold_start/
cp features/scheduling/* ../ml-integration/data/scheduling/
cp features/metric_propagation/* ../ml-integration/data/metric_propagation/
```

Then retrain — see [ml-integration/README.md](../ml-integration/README.md).

## Sub-cause Reference

**Cold Start:** `image_pull_latency`, `init_container_delay`, `readiness_probe_failure`, `container_runtime_slow`, `registry_timeout`

**Scheduling:** `taint_conflict`, `resource_quota_exceeded`, `node_affinity_mismatch`, `pdb_violation`, `insufficient_resources`

**Metric Propagation:** `metrics_server_lag`, `hpa_sync_delay`, `prometheus_scrape_gap`, `keda_polling_delay`
