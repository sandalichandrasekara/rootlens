"""
Tests for ML feature extractors.
Validates feature shape, NaN/Inf sanitization, default handling, and edge cases.
"""

import sys
import os
import numpy as np
import pytest

# Add parent directory to path so features module is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from features.cold_start_features import ColdStartFeatureExtractor, COLD_START_FEATURES
from features.scheduling_features import SchedulingFeatureExtractor, SCHEDULING_FEATURES
from features.metric_propagation_features import MetricPropagationFeatureExtractor, METRIC_PROPAGATION_FEATURES


# Cold Start Extractor

class TestColdStartFeatureExtractor:
    def setup_method(self):
        self.extractor = ColdStartFeatureExtractor()

    def test_output_shape(self):
        features = self.extractor.extract({})
        assert features.shape == (15,), f"Expected 15 features, got {features.shape}"

    def test_feature_count_matches_names(self):
        assert len(COLD_START_FEATURES) == 15
        assert self.extractor.n_features == 15

    def test_no_nan_with_empty_input(self):
        features = self.extractor.extract({})
        assert not np.any(np.isnan(features)), "NaN found with empty input"
        assert not np.any(np.isinf(features)), "Inf found with empty input"

    def test_no_nan_with_zero_total_cold_start(self):
        metrics = {"total_cold_start_seconds": 0, "image_pull_duration_seconds": 0}
        features = self.extractor.extract(metrics)
        assert not np.any(np.isnan(features))
        assert not np.any(np.isinf(features))

    def test_realistic_input(self):
        metrics = {
            "image_pull_duration_seconds": 5.2,
            "image_pull_errors": 1,
            "is_first_pull_on_node": 1,
            "image_size_estimate_mb": 250,
            "init_container_count": 1,
            "init_container_duration_seconds": 2.0,
            "readiness_probe_failures": 3,
            "readiness_probe_period_seconds": 10,
            "readiness_probe_timeout_seconds": 1,
            "container_create_duration_seconds": 0.5,
            "total_cold_start_seconds": 12.0,
        }
        features = self.extractor.extract(metrics)
        assert features.shape == (15,)
        assert not np.any(np.isnan(features))
        assert not np.any(np.isinf(features))
        # image_pull_ratio = 5.2 / 12.0 ≈ 0.43
        assert 0.4 < features[11] < 0.5

    def test_nan_input_sanitized(self):
        metrics = {"image_pull_duration_seconds": float("nan"), "total_cold_start_seconds": float("nan")}
        features = self.extractor.extract(metrics)
        assert not np.any(np.isnan(features))

    def test_inf_input_sanitized(self):
        metrics = {"image_pull_duration_seconds": float("inf"), "total_cold_start_seconds": float("inf")}
        features = self.extractor.extract(metrics)
        assert not np.any(np.isinf(features))

    def test_dtype_is_float64(self):
        features = self.extractor.extract({})
        assert features.dtype == np.float64

    def test_get_sub_causes_returns_list(self):
        causes = self.extractor.get_sub_causes()
        assert len(causes) == 5
        assert "image_pull_latency" in causes

    def test_recommendations_returned_for_all_sub_causes(self):
        for cause in self.extractor.get_sub_causes():
            recs = self.extractor.get_recommendations(cause)
            assert isinstance(recs, list)
            assert len(recs) > 0


# Scheduling Extractor

class TestSchedulingFeatureExtractor:
    def setup_method(self):
        self.extractor = SchedulingFeatureExtractor()

    def test_output_shape(self):
        features = self.extractor.extract({})
        assert features.shape == (11,), f"Expected 11 features, got {features.shape}"

    def test_feature_count_matches_names(self):
        assert len(SCHEDULING_FEATURES) == 11
        assert self.extractor.n_features == 11

    def test_no_nan_with_empty_input(self):
        features = self.extractor.extract({})
        assert not np.any(np.isnan(features))
        assert not np.any(np.isinf(features))

    def test_resource_pressure_zero_cpu(self):
        # available_cpu=0 should not produce inf/nan
        metrics = {"available_cpu_millicores": 0, "cpu_request_millicores": 500}
        features = self.extractor.extract(metrics)
        assert not np.any(np.isnan(features))
        assert not np.any(np.isinf(features))
        # resource_pressure should be 1.0 (max pressure when no resources)
        assert features[10] == 1.0

    def test_realistic_scheduling_delay(self):
        metrics = {
            "scheduling_duration_seconds": 45.0,
            "scheduling_attempts": 3,
            "has_node_selector": 1,
            "has_node_affinity": 0,
            "has_tolerations": 0,
            "pod_priority": 100,
            "cpu_request_millicores": 2000,
            "memory_request_mb": 512,
            "node_count_in_cluster": 3,
            "available_cpu_millicores": 1000,
        }
        features = self.extractor.extract(metrics)
        assert features.shape == (11,)
        assert not np.any(np.isnan(features))
        assert features[10] == pytest.approx(2.0)

    def test_infer_sub_cause_from_reason(self):
        assert self.extractor.infer_sub_cause_from_reason("Insufficient CPU") == "insufficient_resources"
        assert self.extractor.infer_sub_cause_from_reason("node(s) had taint") == "taint_conflict"
        assert self.extractor.infer_sub_cause_from_reason("node affinity") == "node_affinity_mismatch"
        assert self.extractor.infer_sub_cause_from_reason("pdb maxUnavailable") == "pdb_violation"
        assert self.extractor.infer_sub_cause_from_reason("exceeded quota") == "resource_quota_exceeded"

    def test_get_sub_causes_returns_list(self):
        causes = self.extractor.get_sub_causes()
        assert len(causes) == 5


# Metric Propagation Extractor

class TestMetricPropagationFeatureExtractor:
    def setup_method(self):
        self.extractor = MetricPropagationFeatureExtractor()

    def test_output_shape(self):
        features = self.extractor.extract({})
        assert features.shape == (10,), f"Expected 10 features, got {features.shape}"

    def test_feature_count_matches_names(self):
        assert len(METRIC_PROPAGATION_FEATURES) == 10
        assert self.extractor.n_features == 10

    def test_no_nan_with_empty_input(self):
        features = self.extractor.extract({})
        assert not np.any(np.isnan(features))
        assert not np.any(np.isinf(features))

    def test_zero_polling_interval_no_divide_by_zero(self):
        metrics = {"keda_polling_interval_seconds": 0, "metric_lag_seconds": 30}
        features = self.extractor.extract(metrics)
        assert not np.any(np.isnan(features))
        assert not np.any(np.isinf(features))

    def test_alternative_field_names(self):
        # metric_propagation_lag_seconds should map to metric_lag_seconds
        metrics_alt = {"metric_propagation_lag_seconds": 45.0, "keda_polling_interval_seconds": 30}
        features_alt = self.extractor.extract(metrics_alt)
        metrics_direct = {"metric_lag_seconds": 45.0, "keda_polling_interval_seconds": 30}
        features_direct = self.extractor.extract(metrics_direct)
        assert features_alt[0] == features_direct[0]

    def test_queue_depth_fallback(self):
        # queue_depth should be used when queue_depth_at_lag not present
        metrics = {"queue_depth": 500}
        features = self.extractor.extract(metrics)
        assert features[5] == 500.0

    def test_realistic_keda_lag(self):
        metrics = {
            "metric_lag_seconds": 35.0,
            "keda_polling_interval_seconds": 30.0,
            "keda_cooldown_period_seconds": 300.0,
            "trigger_threshold": 100.0,
            "current_replicas": 1,
            "desired_replicas": 5,
            "queue_depth": 800,
            "time_since_last_scale_seconds": 60.0,
        }
        features = self.extractor.extract(metrics)
        assert features.shape == (10,)
        assert not np.any(np.isnan(features))
        # lag_to_polling_ratio = 35 / 30 ≈ 1.17
        assert features[8] == pytest.approx(35.0 / 30.0)

    def test_infer_sub_cause_keda_polling(self):
        metrics = {"metric_lag_seconds": 30.0, "keda_polling_interval_seconds": 30.0}
        sub_cause = self.extractor.infer_sub_cause_from_config(metrics)
        assert sub_cause == "keda_polling_delay"

    def test_infer_sub_cause_metrics_server(self):
        # lag=73 > 60 and 73 % 15 = 13 (>= 3), so neither keda nor hpa check triggers → metrics_server_lag
        metrics = {"metric_lag_seconds": 73.0, "keda_polling_interval_seconds": 30.0, "hpa_sync_period_seconds": 15.0}
        sub_cause = self.extractor.infer_sub_cause_from_config(metrics)
        assert sub_cause == "metrics_server_lag"
