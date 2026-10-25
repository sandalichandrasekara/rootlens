"""
ML Explainer Service
Provides sub-cause explanations for RCA classifications

Endpoints:
- /explain/cold-start: Sub-cause explanation for cold start delays
- /explain/scheduling: Sub-cause explanation for scheduling delays
- /explain/metric-propagation: Sub-cause explanation for metric propagation delays
- /explainers/status: Check which explainer models are loaded
- /health: Health check
"""

import os
import logging
import pickle
import numpy as np
from flask import Flask, request, jsonify
from typing import Dict, Any
import traceback

from features.cold_start_features import ColdStartFeatureExtractor, COLD_START_FEATURES
from features.scheduling_features import SchedulingFeatureExtractor, SCHEDULING_FEATURES
from features.metric_propagation_features import MetricPropagationFeatureExtractor, METRIC_PROPAGATION_FEATURES

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Global variables for explainer models
cold_start_explainer = None
scheduling_explainer = None
metric_propagation_explainer = None

cold_start_extractor = ColdStartFeatureExtractor()
scheduling_extractor = SchedulingFeatureExtractor()
metric_propagation_extractor = MetricPropagationFeatureExtractor()


class ExplainerModel:
    """Wrapper for category-specific explainer models"""

    def __init__(self, model_path: str, scaler_path: str, encoder_path: str,
                 extractor, feature_names: list, name: str):
        """
        Load explainer model and supporting files.

        Args:
            model_path: Path to trained model pickle file
            scaler_path: Path to feature scaler pickle file
            encoder_path: Path to label encoder pickle file
            extractor: Feature extractor instance
            feature_names: List of feature names
            name: Human-readable name for logging
        """
        self.name = name
        self.extractor = extractor
        self.feature_names = feature_names

        try:
            with open(model_path, 'rb') as f:
                self.model = pickle.load(f)
            with open(scaler_path, 'rb') as f:
                self.scaler = pickle.load(f)
            with open(encoder_path, 'rb') as f:
                self.label_encoder = pickle.load(f)
            logger.info(f"  Loaded {name} explainer")
        except Exception as e:
            logger.error(f"Failed to load {name} explainer: {e}")
            raise

    def explain(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate sub-cause explanation for the given metrics.

        Args:
            metrics: Raw metrics dictionary

        Returns:
            Dictionary with sub_cause, confidence, probabilities, explanation, recommendations
        """
        try:
            # Extract features
            features = self.extractor.extract(metrics)

            # Scale features
            features_scaled = self.scaler.transform(features.reshape(1, -1))

            # Get prediction and probabilities
            prediction = self.model.predict(features_scaled)[0]
            probabilities = self.model.predict_proba(features_scaled)[0]

            # Convert to label
            sub_cause = self.label_encoder.inverse_transform([prediction])[0]
            confidence = float(probabilities[prediction])

            # Create probability dictionary
            prob_dict = {
                cause: float(probabilities[i])
                for i, cause in enumerate(self.label_encoder.classes_)
            }

            # Generate explanation (top contributing features)
            explanation = self._generate_explanation(features, features_scaled[0])

            # Get recommendations
            recommendations = self.extractor.get_recommendations(sub_cause)

            return {
                "success": True,
                "sub_cause": sub_cause,
                "confidence": confidence,
                "probabilities": prob_dict,
                "explanation": explanation,
                "recommendations": recommendations
            }

        except Exception as e:
            logger.error(f"{self.name} explanation failed: {e}")
            logger.error(traceback.format_exc())
            raise

    def _generate_explanation(self, features: np.ndarray, features_scaled: np.ndarray) -> Dict[str, Any]:
        """Generate explanation with top contributing features."""

        # Get feature importances from the model
        if hasattr(self.model, 'feature_importances_'):
            importances = self.model.feature_importances_
        else:
            # Fallback: use scaled feature magnitudes
            importances = np.abs(features_scaled)

        feature_contributions = []
        for name, value, importance in zip(
            self.feature_names, features, importances
        ):
            feature_contributions.append({
                "feature": name,
                "value": float(value),
                "importance": float(importance),
            })

        # Sort by importance and take top 5
        feature_contributions.sort(key=lambda x: x["importance"], reverse=True)
        top_features = feature_contributions[:5]

        # Generate summary
        top_feature = top_features[0] if top_features else None
        if top_feature:
            summary = f"Primary indicator: {top_feature['feature']} = {top_feature['value']:.2f}"
        else:
            summary = "Unable to determine primary indicator"

        return {
            "top_features": top_features,
            "summary": summary
        }


def load_explainers():
    """Load all explainer models on service startup."""
    global cold_start_explainer, scheduling_explainer, metric_propagation_explainer

    script_dir = os.path.dirname(os.path.abspath(__file__))
    explainers_dir = os.path.join(script_dir, 'results', 'explainers')

    logger.info("Loading explainer models...")

    # Cold Start Explainer
    try:
        cold_start_explainer = ExplainerModel(
            model_path=os.path.join(explainers_dir, 'cold_start_explainer.pkl'),
            scaler_path=os.path.join(explainers_dir, 'cold_start_scaler.pkl'),
            encoder_path=os.path.join(explainers_dir, 'cold_start_label_encoder.pkl'),
            extractor=cold_start_extractor,
            feature_names=COLD_START_FEATURES,
            name="Cold Start"
        )
    except Exception as e:
        logger.warning(f"Cold Start explainer not available: {e}")
        cold_start_explainer = None

    # Scheduling Explainer
    try:
        scheduling_explainer = ExplainerModel(
            model_path=os.path.join(explainers_dir, 'scheduling_explainer.pkl'),
            scaler_path=os.path.join(explainers_dir, 'scheduling_scaler.pkl'),
            encoder_path=os.path.join(explainers_dir, 'scheduling_label_encoder.pkl'),
            extractor=scheduling_extractor,
            feature_names=SCHEDULING_FEATURES,
            name="Scheduling"
        )
    except Exception as e:
        logger.warning(f"Scheduling explainer not available: {e}")
        scheduling_explainer = None

    # Metric Propagation Explainer
    try:
        metric_propagation_explainer = ExplainerModel(
            model_path=os.path.join(explainers_dir, 'metric_propagation_explainer.pkl'),
            scaler_path=os.path.join(explainers_dir, 'metric_propagation_scaler.pkl'),
            encoder_path=os.path.join(explainers_dir, 'metric_propagation_label_encoder.pkl'),
            extractor=metric_propagation_extractor,
            feature_names=METRIC_PROPAGATION_FEATURES,
            name="Metric Propagation"
        )
    except Exception as e:
        logger.warning(f"Metric Propagation explainer not available: {e}")
        metric_propagation_explainer = None

    loaded_count = sum([
        cold_start_explainer is not None,
        scheduling_explainer is not None,
        metric_propagation_explainer is not None
    ])
    logger.info(f"Loaded {loaded_count}/3 explainer models")

    return loaded_count > 0


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint - reports ready only when models are loaded."""
    loaded = sum([
        cold_start_explainer is not None,
        scheduling_explainer is not None,
        metric_propagation_explainer is not None
    ])
    ready = loaded > 0
    status_code = 200 if ready else 503
    return jsonify({
        "status": "ok" if ready else "loading",
        "service": "ml-explainer",
        "version": "2.0",
        "models_loaded": loaded,
        "models_total": 3
    }), status_code


@app.route('/explain/cold-start', methods=['POST'])
def explain_cold_start():
    """
    Explain cold start delay sub-cause.

    Sub-causes: image_pull_latency, init_container_delay, readiness_probe_failure,
                container_runtime_slow, registry_timeout
    """
    try:
        if not request.is_json:
            return jsonify({"success": False, "error": "Request must be JSON"}), 400

        data = request.get_json()
        if 'metrics' not in data:
            return jsonify({"success": False, "error": "Missing 'metrics' field"}), 400

        if cold_start_explainer is None:
            return jsonify({
                "success": False,
                "error": "Cold Start explainer not loaded"
            }), 503

        result = cold_start_explainer.explain(data['metrics'])
        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Cold Start explanation error: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": "Explanation failed",
            "details": str(e)
        }), 503


@app.route('/explain/scheduling', methods=['POST'])
def explain_scheduling():
    """
    Explain scheduling delay sub-cause.

    Sub-causes: taint_conflict, resource_quota_exceeded, node_affinity_mismatch,
                pdb_violation, insufficient_resources
    """
    try:
        if not request.is_json:
            return jsonify({"success": False, "error": "Request must be JSON"}), 400

        data = request.get_json()
        if 'metrics' not in data:
            return jsonify({"success": False, "error": "Missing 'metrics' field"}), 400

        if scheduling_explainer is None:
            return jsonify({
                "success": False,
                "error": "Scheduling explainer not loaded"
            }), 503

        result = scheduling_explainer.explain(data['metrics'])
        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Scheduling explanation error: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": "Explanation failed",
            "details": str(e)
        }), 503


@app.route('/explain/metric-propagation', methods=['POST'])
def explain_metric_propagation():
    """
    Explain metric propagation lag sub-cause.

    Sub-causes: metrics_server_lag, hpa_sync_delay, prometheus_scrape_gap, keda_polling_delay
    """
    try:
        if not request.is_json:
            return jsonify({"success": False, "error": "Request must be JSON"}), 400

        data = request.get_json()
        if 'metrics' not in data:
            return jsonify({"success": False, "error": "Missing 'metrics' field"}), 400

        if metric_propagation_explainer is None:
            return jsonify({
                "success": False,
                "error": "Metric Propagation explainer not loaded"
            }), 503

        result = metric_propagation_explainer.explain(data['metrics'])
        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Metric Propagation explanation error: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": "Explanation failed",
            "details": str(e)
        }), 503


@app.route('/explainers/status', methods=['GET'])
def explainers_status():
    """Check which explainer models are loaded."""
    return jsonify({
        "success": True,
        "explainers": {
            "cold_start": cold_start_explainer is not None,
            "scheduling": scheduling_explainer is not None,
            "metric_propagation": metric_propagation_explainer is not None
        }
    }), 200


@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "success": False,
        "error": "Endpoint not found"
    }), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "success": False,
        "error": "Internal server error"
    }), 500


load_explainers()


if __name__ == '__main__':
    if cold_start_explainer is None and scheduling_explainer is None:
        load_explainers()

    port = int(os.getenv('PORT', os.getenv('FLASK_PORT', 5000)))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'

    logger.info(f"Starting ML Explainer Service on port {port}")
    logger.info("Available endpoints:")
    logger.info("  POST /explain/cold-start - Cold start sub-cause")
    logger.info("  POST /explain/scheduling - Scheduling sub-cause")
    logger.info("  POST /explain/metric-propagation - Metric propagation sub-cause")
    logger.info("  GET  /explainers/status - Check loaded explainers")
    logger.info("  GET  /health - Health check")

    app.run(host='0.0.0.0', port=port, debug=debug, threaded=True)
