"""
Cold Start Feature Extractor

Extracts 15 features specifically designed to identify sub-causes of cold start delays:
- image_pull_latency: Long image pull times
- init_container_delay: Slow init containers
- readiness_probe_failure: Probe retries delaying readiness
- container_runtime_slow: Container creation taking too long
- registry_timeout: Registry connectivity issues
"""

import numpy as np
from typing import Dict, Any, List

# Sub-cause labels for cold start
COLD_START_SUB_CAUSES = [
    "image_pull_latency",
    "init_container_delay",
    "readiness_probe_failure",
    "container_runtime_slow",
    "registry_timeout",
]

# Feature names (15 features)
COLD_START_FEATURES = [
    "image_pull_duration_seconds",
    "image_pull_errors",
    "is_first_pull_on_node",
    "image_size_estimate_mb",
    "init_container_count",
    "init_container_duration_seconds",
    "readiness_probe_failures",
    "readiness_probe_period_seconds",
    "readiness_probe_timeout_seconds",
    "container_create_duration_seconds",
    "total_cold_start_seconds",
    "image_pull_ratio",
    "init_container_ratio",
    "probe_failure_rate",
    "container_create_ratio",
]


class ColdStartFeatureExtractor:
    """Extracts features for cold start sub-cause classification"""

    def __init__(self):
        self.feature_names = COLD_START_FEATURES
        self.n_features = len(COLD_START_FEATURES)

    def extract(self, metrics: Dict[str, Any]) -> np.ndarray:
        """
        Extract cold start features from metrics dictionary.

        Args:
            metrics: Dictionary containing pod metrics and event data

        Returns:
            numpy array of 15 features
        """
        # Image pull metrics
        image_pull_duration = float(metrics.get('image_pull_duration_seconds', 0))
        image_pull_errors = float(metrics.get('image_pull_errors', 0))
        is_first_pull = float(metrics.get('is_first_pull_on_node', 0))
        image_size_mb = float(metrics.get('image_size_estimate_mb', 100))  

        # Init container metrics
        init_container_count = float(metrics.get('init_container_count', 0))
        init_container_duration = float(metrics.get('init_container_duration_seconds', 0))

        # Readiness probe metrics
        readiness_failures = float(metrics.get('readiness_probe_failures', 0))
        probe_period = float(metrics.get('readiness_probe_period_seconds', 10))  
        probe_timeout = float(metrics.get('readiness_probe_timeout_seconds', 1))  

        # Container runtime metrics
        container_create_duration = float(metrics.get('container_create_duration_seconds', 0))

        # Calculate total cold start (from available data)
        total_cold_start = float(metrics.get('total_cold_start_seconds', 0))
        if total_cold_start == 0:
            # Estimate from components
            total_cold_start = image_pull_duration + init_container_duration + container_create_duration
            # Add probe delay estimate
            total_cold_start += readiness_failures * probe_period

        # Avoid division by zero
        total_cold_start = max(total_cold_start, 0.001)

        # Derived ratios
        image_pull_ratio = image_pull_duration / total_cold_start
        init_container_ratio = init_container_duration / total_cold_start

        # Probe failure rate (failures / expected number of probes in cold start period)
        expected_probes = max(total_cold_start / probe_period, 1)
        probe_failure_rate = readiness_failures / expected_probes

        container_create_ratio = container_create_duration / total_cold_start

        # Build feature array
        features = np.array([
            image_pull_duration,          # 0
            image_pull_errors,            # 1
            is_first_pull,                # 2
            image_size_mb,                # 3
            init_container_count,         # 4
            init_container_duration,      # 5
            readiness_failures,           # 6
            probe_period,                 # 7
            probe_timeout,                # 8
            container_create_duration,    # 9
            total_cold_start,             # 10
            image_pull_ratio,             # 11
            init_container_ratio,         # 12
            probe_failure_rate,           # 13
            container_create_ratio,       # 14
        ], dtype=np.float64)

        # Sanitize: replace NaN/Inf with 0 to prevent model crashes
        features = np.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0)

        return features

    def get_feature_names(self) -> List[str]:
        """Return list of feature names"""
        return self.feature_names.copy()

    def get_sub_causes(self) -> List[str]:
        """Return list of possible sub-causes"""
        return COLD_START_SUB_CAUSES.copy()

    def get_recommendations(self, sub_cause: str) -> List[str]:
        """
        Get actionable recommendations for a specific sub-cause.

        Args:
            sub_cause: The identified sub-cause

        Returns:
            List of recommendation strings
        """
        recommendations = {
            "image_pull_latency": [
                "Use a container registry closer to your cluster (same region/zone)",
                "Enable image caching on nodes using tools like Spegel or registry mirrors",
                "Reduce image size by using multi-stage builds and slim base images",
                "Pre-pull images to nodes using DaemonSets before scaling events",
            ],
            "init_container_delay": [
                "Review init container logic for unnecessary delays",
                "Parallelize init container operations where possible",
                "Consider moving init logic to application startup if not security-critical",
                "Use readiness gates instead of init containers for dependency checks",
            ],
            "readiness_probe_failure": [
                "Increase initialDelaySeconds for readiness probe",
                "Review probe configuration (timeoutSeconds, periodSeconds)",
                "Ensure application startup is optimized and deterministic",
                "Check for resource constraints causing slow application startup",
            ],
            "container_runtime_slow": [
                "Check node resource utilization (CPU, memory, disk I/O)",
                "Review container runtime (containerd/docker) performance",
                "Consider using lighter container runtimes for faster startup",
                "Check for disk I/O bottlenecks on node storage",
            ],
            "registry_timeout": [
                "Verify network connectivity to container registry",
                "Check registry authentication and pull secrets",
                "Use image pull secrets with correct credentials",
                "Consider setting up a local registry mirror for reliability",
            ],
        }

        return recommendations.get(sub_cause, [
            "Review pod events and logs for specific failure details",
            "Check cluster resource availability",
        ])
