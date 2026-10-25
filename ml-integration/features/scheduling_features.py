"""
Scheduling Feature Extractor

Extracts 11 features specifically designed to identify sub-causes of scheduling delays:
- taint_conflict: Pod tolerations don't match node taints
- resource_quota_exceeded: Namespace quota limits hit
- node_affinity_mismatch: No nodes match affinity rules
- pdb_violation: PodDisruptionBudget blocking scheduling
- insufficient_resources: No nodes with enough CPU/memory

NOTE: scheduling_failure_encoded was REMOVED to prevent label leakage.
      That feature directly encoded the target label, making the model
      memorize rather than learn patterns.
"""

import numpy as np
from typing import Dict, Any, List

# Sub-cause labels for scheduling delays
SCHEDULING_SUB_CAUSES = [
    "taint_conflict",
    "resource_quota_exceeded",
    "node_affinity_mismatch",
    "pdb_violation",
    "insufficient_resources",
]

# Feature names (11 features - removed scheduling_failure_encoded due to label leakage)
SCHEDULING_FEATURES = [
    "scheduling_duration_seconds",
    "scheduling_attempts",
    "has_node_selector",
    "has_node_affinity",
    "has_tolerations",
    "pod_priority",
    "cpu_request_millicores",
    "memory_request_mb",
    "node_count_in_cluster",
    "available_cpu_millicores",
    "resource_pressure_score",
]


class SchedulingFeatureExtractor:
    """Extracts features for scheduling delay sub-cause classification"""

    def __init__(self):
        self.feature_names = SCHEDULING_FEATURES
        self.n_features = len(SCHEDULING_FEATURES)

    def extract(self, metrics: Dict[str, Any]) -> np.ndarray:
        """
        Extract scheduling features from metrics dictionary.

        Args:
            metrics: Dictionary containing pod metrics and cluster state

        Returns:
            numpy array of 11 features
        """
        # Timing metrics
        scheduling_duration = float(metrics.get('scheduling_duration_seconds', 0))
        scheduling_attempts = float(metrics.get('scheduling_attempts', 1))

        # Pod configuration flags
        has_node_selector = float(metrics.get('has_node_selector', 0))
        has_node_affinity = float(metrics.get('has_node_affinity', 0))
        has_tolerations = float(metrics.get('has_tolerations', 0))
        pod_priority = float(metrics.get('pod_priority', 0))

        # Resource requests
        cpu_request = float(metrics.get('cpu_request_millicores', 100))  # Default 100m
        memory_request = float(metrics.get('memory_request_mb', 128))    # Default 128Mi

        # Cluster state
        node_count = float(metrics.get('node_count_in_cluster', 3))      # Default 3 nodes
        available_cpu = float(metrics.get('available_cpu_millicores', 4000))  # Default 4 cores

        # Resource pressure score
        # Higher score = more pressure (request relative to available)
        if available_cpu > 0:
            resource_pressure = cpu_request / available_cpu
        else:
            resource_pressure = 1.0  # Max pressure if no resources available

        # Build feature array (11 features)
        features = np.array([
            scheduling_duration,          # 0
            scheduling_attempts,          # 1
            has_node_selector,            # 2
            has_node_affinity,            # 3
            has_tolerations,              # 4
            pod_priority,                 # 5
            cpu_request,                  # 6
            memory_request,               # 7
            node_count,                   # 8
            available_cpu,                # 9
            resource_pressure,            # 10
        ], dtype=np.float64)

        # Sanitize: replace NaN/Inf with 0 to prevent model crashes
        features = np.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0)

        return features

    def get_feature_names(self) -> List[str]:
        """Return list of feature names"""
        return self.feature_names.copy()

    def get_sub_causes(self) -> List[str]:
        """Return list of possible sub-causes"""
        return SCHEDULING_SUB_CAUSES.copy()

    def infer_sub_cause_from_reason(self, failure_reason: str) -> str:
        """
        Infer sub-cause directly from scheduling failure reason.
        Useful as a fallback when ML confidence is low.

        Args:
            failure_reason: The scheduling failure reason string

        Returns:
            Inferred sub-cause string
        """
        reason_lower = failure_reason.lower() if failure_reason else ""

        if "insufficient" in reason_lower or "unschedulable" in reason_lower:
            return "insufficient_resources"
        elif "taint" in reason_lower or "toleration" in reason_lower:
            return "taint_conflict"
        elif "affinity" in reason_lower:
            return "node_affinity_mismatch"
        elif "pdb" in reason_lower or "disruption" in reason_lower:
            return "pdb_violation"
        elif "quota" in reason_lower:
            return "resource_quota_exceeded"
        else:
            return "insufficient_resources"  # Default

    def get_recommendations(self, sub_cause: str) -> List[str]:
        """
        Get actionable recommendations for a specific sub-cause.

        Args:
            sub_cause: The identified sub-cause

        Returns:
            List of recommendation strings
        """
        recommendations = {
            "taint_conflict": [
                "Add appropriate tolerations to the pod spec",
                "Review node taints with: kubectl describe nodes | grep Taints",
                "Consider removing unnecessary taints from nodes",
                "Use nodeSelector or affinity rules to target untainted nodes",
            ],
            "resource_quota_exceeded": [
                "Check namespace ResourceQuota: kubectl describe quota -n <namespace>",
                "Request quota increase from cluster admin",
                "Reduce resource requests in pod spec if over-provisioned",
                "Delete unused pods/deployments to free quota",
            ],
            "node_affinity_mismatch": [
                "Review node labels: kubectl get nodes --show-labels",
                "Adjust nodeAffinity rules to match available nodes",
                "Consider using preferredDuringSchedulingIgnoredDuringExecution",
                "Add required labels to target nodes",
            ],
            "pdb_violation": [
                "Review PodDisruptionBudget: kubectl get pdb -n <namespace>",
                "Temporarily adjust PDB minAvailable/maxUnavailable",
                "Wait for disruption budget to allow scheduling",
                "Check if other pods in the same PDB are healthy",
            ],
            "insufficient_resources": [
                "Scale up cluster by adding more nodes",
                "Review and right-size resource requests (may be over-provisioned)",
                "Check for resource hogging pods: kubectl top pods",
                "Consider using Cluster Autoscaler for dynamic scaling",
                "Delete completed Jobs or unused pods to free resources",
            ],
        }

        return recommendations.get(sub_cause, [
            "Review pod events: kubectl describe pod <pod-name>",
            "Check cluster resource availability",
        ])
