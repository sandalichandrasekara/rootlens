"""
Tests for model loading and basic inference.
Verifies trained models load correctly and produce valid predictions.
"""

import sys
import os
import pickle
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

sklearn = pytest.importorskip("sklearn", reason="scikit-learn not installed — skipping model tests")

from features.cold_start_features import ColdStartFeatureExtractor
from features.scheduling_features import SchedulingFeatureExtractor
from features.metric_propagation_features import MetricPropagationFeatureExtractor

EXPLAINER_DIR = os.path.join(os.path.dirname(__file__), "..", "results", "explainers")


def load_pkl(filename):
    path = os.path.join(EXPLAINER_DIR, filename)
    if not os.path.exists(path):
        pytest.skip(f"Model file not found: {path}")
    with open(path, "rb") as f:
        return pickle.load(f)


class TestColdStartModel:
    def setup_method(self):
        self.model = load_pkl("cold_start_explainer.pkl")
        self.scaler = load_pkl("cold_start_scaler.pkl")
        self.encoder = load_pkl("cold_start_label_encoder.pkl")
        self.extractor = ColdStartFeatureExtractor()

    def test_model_feature_count_matches_extractor(self):
        assert self.model.n_features_in_ == self.extractor.n_features, (
            f"Model expects {self.model.n_features_in_} features, "
            f"extractor produces {self.extractor.n_features}"
        )

    def test_scaler_feature_count_matches_extractor(self):
        assert self.scaler.n_features_in_ == self.extractor.n_features

    def test_predict_returns_valid_class(self):
        features = self.extractor.extract({"image_pull_duration_seconds": 8.0, "total_cold_start_seconds": 10.0})
        scaled = self.scaler.transform(features.reshape(1, -1))
        pred = self.model.predict(scaled)
        decoded = self.encoder.inverse_transform(pred)
        assert decoded[0] in self.extractor.get_sub_causes()

    def test_predict_proba_sums_to_one(self):
        features = self.extractor.extract({"image_pull_duration_seconds": 8.0})
        scaled = self.scaler.transform(features.reshape(1, -1))
        proba = self.model.predict_proba(scaled)
        assert abs(proba.sum() - 1.0) < 1e-6

    def test_predict_proba_shape(self):
        features = self.extractor.extract({})
        scaled = self.scaler.transform(features.reshape(1, -1))
        proba = self.model.predict_proba(scaled)
        assert proba.shape[1] == len(self.extractor.get_sub_causes())

    def test_no_prediction_error_on_nan_sanitized_input(self):
        # NaN should be sanitized by extractor before reaching model
        features = self.extractor.extract({"image_pull_duration_seconds": float("nan")})
        assert not np.any(np.isnan(features))
        scaled = self.scaler.transform(features.reshape(1, -1))
        self.model.predict(scaled)  # Should not raise


class TestSchedulingModel:
    def setup_method(self):
        self.model = load_pkl("scheduling_explainer.pkl")
        self.scaler = load_pkl("scheduling_scaler.pkl")
        self.encoder = load_pkl("scheduling_label_encoder.pkl")
        self.extractor = SchedulingFeatureExtractor()

    def test_model_feature_count_matches_extractor(self):
        assert self.model.n_features_in_ == self.extractor.n_features

    def test_scaler_feature_count_matches_extractor(self):
        assert self.scaler.n_features_in_ == self.extractor.n_features

    def test_predict_returns_valid_class(self):
        features = self.extractor.extract({"scheduling_duration_seconds": 45.0})
        scaled = self.scaler.transform(features.reshape(1, -1))
        pred = self.model.predict(scaled)
        decoded = self.encoder.inverse_transform(pred)
        assert decoded[0] in self.extractor.get_sub_causes()

    def test_predict_proba_sums_to_one(self):
        features = self.extractor.extract({})
        scaled = self.scaler.transform(features.reshape(1, -1))
        proba = self.model.predict_proba(scaled)
        assert abs(proba.sum() - 1.0) < 1e-6


class TestMetricPropagationModel:
    def setup_method(self):
        self.model = load_pkl("metric_propagation_explainer.pkl")
        self.scaler = load_pkl("metric_propagation_scaler.pkl")
        self.encoder = load_pkl("metric_propagation_label_encoder.pkl")
        self.extractor = MetricPropagationFeatureExtractor()

    def test_model_feature_count_matches_extractor(self):
        assert self.model.n_features_in_ == self.extractor.n_features

    def test_scaler_feature_count_matches_extractor(self):
        assert self.scaler.n_features_in_ == self.extractor.n_features

    def test_predict_returns_valid_class(self):
        features = self.extractor.extract({"metric_lag_seconds": 45.0})
        scaled = self.scaler.transform(features.reshape(1, -1))
        pred = self.model.predict(scaled)
        decoded = self.encoder.inverse_transform(pred)
        assert decoded[0] in self.extractor.get_sub_causes()

    def test_predict_proba_sums_to_one(self):
        features = self.extractor.extract({})
        scaled = self.scaler.transform(features.reshape(1, -1))
        proba = self.model.predict_proba(scaled)
        assert abs(proba.sum() - 1.0) < 1e-6

    def test_feature_importances_available(self):
        assert hasattr(self.model, "feature_importances_")
        importances = self.model.feature_importances_
        assert len(importances) == self.extractor.n_features
        assert abs(importances.sum() - 1.0) < 1e-6
