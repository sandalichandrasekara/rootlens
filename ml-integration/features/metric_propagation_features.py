"""
Metric Propagation Feature Extractor

Extracts 10 features specifically designed to identify sub-causes of metric propagation delays:
- metrics_server_lag: Kubernetes metrics-server returning stale data
- hpa_sync_delay: HPA sync period causing delays
- prometheus_scrape_gap: Prometheus scrape interval too long
- keda_polling_delay: KEDA polling interval causing lag
"""

import numpy as np
from typing import Dict, Any, List

# Sub-cause labels for metric propagation lag
METRIC_PROPAGATION_SUB_CAUSES = [
    "metrics_server_lag",
    "hpa_sync_delay",
    "prometheus_scrape_gap",
    "keda_polling_delay",
]

# Feature names (10 features)
METRIC_PROPAGATION_FEATURES = [
    "metric_lag_seconds",
    "keda_polling_interval_seconds",
    "keda_cooldown_period_seconds",
    "trigger_threshold",
    "time_since_last_scale_seconds",
    "queue_depth_at_lag",
    "desired_vs_current_gap",
    "hpa_sync_period_seconds",
    "lag_to_polling_ratio",
    "scale_responsiveness_score",
]


class MetricPropagationFeatureExtractor:
    """Extracts features for metric propagation sub-cause classification"""

    def __init__(self):
        self.feature_names = METRIC_PROPAGATION_FEATURES
        self.n_features = len(METRIC_PROPAGATION_FEATURES)

    def extract(self, metrics: Dict[str, Any]) -> np.ndarray:
        """
        Extract metric propagation features from metrics dictionary.

        Args:
            metrics: Dictionary containing KEDA metrics and timing data

        Returns:
            numpy array of 10 features
        """
        # Core lag metric
        metric_lag = float(metrics.get('metric_lag_seconds', 0))
        if metric_lag == 0:
            metric_lag = float(metrics.get('metric_propagation_lag_seconds', 0))

        # KEDA configuration
        polling_interval = float(metrics.get('keda_polling_interval_seconds', 30))
        if polling_interval == 0:
            polling_interval = float(metrics.get('polling_interval_seconds', 30))

        cooldown_period = float(metrics.get('keda_cooldown_period_seconds', 300))
        if cooldown_period == 0:
            cooldown_period = float(metrics.get('cooldown_period_seconds', 300))

        trigger_threshold = float(metrics.get('trigger_threshold', 100))

        # Scaling state
        time_since_last_scale = float(metrics.get('time_since_last_scale_seconds', 0))
        if time_since_last_scale == 0:
            time_since_last_scale = float(metrics.get('last_scaling_event_seconds_ago', 0))

        queue_depth = float(metrics.get('queue_depth_at_lag', 0))
        if queue_depth == 0:
            queue_depth = float(metrics.get('queue_depth', 0))

        current_replicas = float(metrics.get('current_replicas', 1))
        desired_replicas = float(metrics.get('desired_replicas', 1))
        replica_gap = desired_replicas - current_replicas

        # HPA configuration (default Kubernetes value is 15 seconds)
        hpa_sync_period = float(metrics.get('hpa_sync_period_seconds', 15))

        # Derived: lag to polling ratio
        # High ratio suggests lag is significantly longer than polling should allow
        if polling_interval > 0:
            lag_to_polling_ratio = metric_lag / polling_interval
        else:
            lag_to_polling_ratio = 0.0

        # Scale responsiveness score
        # Measures how quickly the system responds to demand
        # Lower is better; higher suggests propagation issues
        if queue_depth > trigger_threshold and replica_gap > 0:
            # System should be scaling but queue is building up
            scale_responsiveness = metric_lag / max(polling_interval, 1)
        elif queue_depth > trigger_threshold and replica_gap == 0:
            # Queue high but no scaling happening - likely metric lag issue
            scale_responsiveness = 2.0 * (metric_lag / max(polling_interval, 1))
        else:
            # Normal operation
            scale_responsiveness = 0.5

        # Build feature array
        features = np.array([
            metric_lag,                   # 0
            polling_interval,             # 1
            cooldown_period,              # 2
            trigger_threshold,            # 3
            time_since_last_scale,        # 4
            queue_depth,                  # 5
            replica_gap,                  # 6
            hpa_sync_period,              # 7
            lag_to_polling_ratio,         # 8
            scale_responsiveness,         # 9
        ], dtype=np.float64)

        # Sanitize: replace NaN/Inf with 0 to prevent model crashes
        features = np.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0)

        return features

    def get_feature_names(self) -> List[str]:
        """Return list of feature names"""
        return self.feature_names.copy()

    def get_sub_causes(self) -> List[str]:
        """Return list of possible sub-causes"""
        return METRIC_PROPAGATION_SUB_CAUSES.copy()

    def infer_sub_cause_from_config(self, metrics: Dict[str, Any]) -> str:
        """
        Infer sub-cause from configuration analysis.
        Useful as a fallback when ML confidence is low.

        Args:
            metrics: The metrics dictionary

        Returns:
            Inferred sub-cause string
        """
        metric_lag = float(metrics.get('metric_lag_seconds', 0))
        polling_interval = float(metrics.get('keda_polling_interval_seconds', 30))
        hpa_sync = float(metrics.get('hpa_sync_period_seconds', 15))

        # If lag is close to polling interval, likely KEDA polling issue
        if metric_lag > 0 and abs(metric_lag - polling_interval) < 5:
            return "keda_polling_delay"

        # If lag is close to HPA sync period multiples
        if metric_lag > 0 and metric_lag % hpa_sync < 3:
            return "hpa_sync_delay"

        # If lag is very high (>60s), likely metrics server issue
        if metric_lag > 60:
            return "metrics_server_lag"

        # Default to KEDA polling as most common
        return "keda_polling_delay"

    def get_recommendations(self, sub_cause: str) -> List[str]:
        """
        Get actionable recommendations for a specific sub-cause.

        Args:
            sub_cause: The identified sub-cause

        Returns:
            List of recommendation strings
        """
        recommendations = {
            "metrics_server_lag": [
                "Check metrics-server health: kubectl get pods -n kube-system | grep metrics",
                "Verify metrics-server resource allocation (may need more CPU/memory)",
                "Review metrics-server --metric-resolution flag (default 15s)",
                "Check network latency between metrics-server and API server",
            ],
            "hpa_sync_delay": [
                "Review HPA sync period in kube-controller-manager",
                "Default is 15s; consider reducing if faster response needed",
                "Check HPA status: kubectl describe hpa <name>",
                "Ensure custom metrics adapter is responding quickly",
            ],
            "prometheus_scrape_gap": [
                "Review Prometheus scrape_interval for target metrics",
                "Consider reducing scrape interval for critical metrics",
                "Check Prometheus scrape duration (may be timing out)",
                "Verify Prometheus has enough resources for scrape load",
            ],
            "keda_polling_delay": [
                "Reduce pollingInterval in ScaledObject (default 30s)",
                "Consider using pollingInterval: 10 for faster response",
                "Review cooldownPeriod if scaling is delayed after events",
                "Check KEDA operator logs for any errors",
            ],
        }

        return recommendations.get(sub_cause, [
            "Review KEDA ScaledObject configuration",
            "Check metrics pipeline for bottlenecks",
        ])
