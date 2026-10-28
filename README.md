<div align="center">

# RootLens

**Automated root cause analysis for KEDA autoscaling delays in Kubernetes**

[![Go](https://img.shields.io/badge/Go-1.25.5-00ADD8?style=flat&logo=go)](https://go.dev)
[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat&logo=python)](https://www.python.org)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=flat&logo=react)](https://react.dev)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-1.34+-326CE5?style=flat&logo=kubernetes)](https://kubernetes.io)
[![KEDA](https://img.shields.io/badge/KEDA-2.0+-00A3E0?style=flat)](https://keda.sh)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

When your pods scale too slowly, RootLens tells you exactly why and how confident it is.


</div>

---

## What It Does

KEDA watches a RabbitMQ queue and scales consumer pods up when messages pile up. But scaling is never instant. Pods can be slow for several reasons. RootLens monitors the full event chain and diagnoses the bottleneck automatically.

```
RabbitMQ message spike
  └─ KEDA detects queue depth, triggers scale-up
       └─ Kubernetes schedules new pods
            └─ Pods initialize and become ready
                 └─ RootLens observes the delay
                      ├─ Rule engine classifies primary cause    [60% weight]
                      ├─ ML explainer identifies sub-cause       [40% weight]
                      └─ Combined confidence + recommendation returned
```

Instead of correlating pod events, KEDA logs, and queue metrics by hand, you get a single diagnosis: **what caused the delay, why the engine is confident, and what to fix**.

---

## Root Cause Categories

| Category | Trigger Condition | Example Sub-causes |
|----------|-------------------|--------------------|
| **Pod Cold Start** | `ReadyTime − ContainerStart > threshold` | Large image pull, slow registry, init container overhead, readiness probe failures |
| **Scheduling Delay** | `ContainerStart − ScheduledTime > threshold` | CPU/memory contention, taint mismatch, node affinity rules, resource quota limits |
| **Metric Propagation Lag** | `Now − KEDA.LastEvent > threshold` | KEDA polling interval, queue depth spike, scaler misconfiguration |

The rule engine identifies which category applies. The ML explainer (a category-specific RandomForest model trained on real K8s fault-injection data) then classifies the specific sub-cause within that category.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         RootLens                            │
│                                                             │
│  ┌──────────┐   ┌───────────────────────────────────────┐  │
│  │Dashboard │   │              Go API Server             │  │
│  │ React 19 │◄──│  /api/rca/run  /api/metrics  /health   │  │
│  └──────────┘   └────────────────┬──────────────────────┘  │
│                                  │                          │
│                    ┌─────────────▼─────────────┐           │
│                    │     RCA Engine (Go)         │           │
│                    │  Rule-based + ML Router     │           │
│                    └──────┬──────────┬──────────┘           │
│                           │          │                       │
│              ┌────────────▼──┐  ┌───▼────────────────────┐ │
│              │  K8s / KEDA   │  │   ML Explainer Service  │ │
│              │  Collectors   │  │   Python / Flask        │ │
│              └───────────────┘  │   3 RandomForest models │ │
│                                 └────────────────────────┘ │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Kubernetes Operator  (controller-runtime)    │  │
│  │         Installs the full stack from a single CRD    │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## License

This project is licensed under the terms of the **MIT License**. 

See the [LICENSE](LICENSE) file for details.



