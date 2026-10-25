#!/usr/bin/env python3
"""
Convert Metric Propagation Sub-Cause Raw Data to Training Features

Reads JSON files from raw_data/metric_propagation_subcauses/ and converts them
to the 10-feature format expected by the metric propagation explainer model.

Output:
- features/metric_propagation_train.npz
- features/metric_propagation_val.npz
- features/metric_propagation_test.npz
- features/metric_propagation_metadata.json

Usage:
    python3 convert_metric_propagation_features.py
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
from sklearn.model_selection import train_test_split
import logging

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Paths
RAW_DATA_DIR = Path(__file__).parent / "raw_data" / "metric_propagation_subcauses"
OUTPUT_DIR = Path(__file__).parent / "features" / "metric_propagation"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Features
FEATURE_NAMES = [
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

# Sub-cause labels
SUB_CAUSES = [
    "metrics_server_lag",
    "hpa_sync_delay",
    "prometheus_scrape_gap",
    "keda_polling_delay",
]


def extract_features(sample: Dict) -> np.ndarray:
    """
    Extract 10 features from a raw sample.

    Args:
        sample: Dictionary with raw metrics from experiment

    Returns:
        numpy array of 10 features
    """
    metric_lag = float(sample.get("metric_lag_seconds", 0))
    polling_interval = float(sample.get("keda_polling_interval_seconds", 30))
    cooldown_period = float(sample.get("keda_cooldown_period_seconds", 300))
    trigger_threshold = float(sample.get("trigger_threshold", 100))
    time_since_last_scale = float(sample.get("time_since_last_scale_seconds", 0))
    queue_depth = float(sample.get("queue_depth_at_lag", 0))

    current_replicas = float(sample.get("current_replicas", 0))
    desired_replicas = float(sample.get("desired_replicas", 1))
    replica_gap = desired_replicas - current_replicas

    hpa_sync_period = float(sample.get("hpa_sync_period_seconds", 15))

    if polling_interval > 0:
        lag_to_polling_ratio = metric_lag / polling_interval
    else:
        lag_to_polling_ratio = 0.0

    if queue_depth > trigger_threshold and replica_gap > 0:
        scale_responsiveness = metric_lag / max(polling_interval, 1)
    elif queue_depth > trigger_threshold and replica_gap == 0:
        scale_responsiveness = 2.0 * (metric_lag / max(polling_interval, 1))
    else:
        scale_responsiveness = 0.5

    features = np.array([
        metric_lag,
        polling_interval,
        cooldown_period,
        trigger_threshold,
        time_since_last_scale,
        queue_depth,
        replica_gap,
        hpa_sync_period,
        lag_to_polling_ratio,
        scale_responsiveness,
    ], dtype=np.float32)

    return features


def load_raw_data() -> Tuple[List[np.ndarray], List[str]]:
    """
    Load all raw JSON files and extract features.

    Returns:
        Tuple of (features_list, labels_list)
    """
    features_list = []
    labels_list = []

    if not RAW_DATA_DIR.exists():
        logger.error(f"Raw data directory not found: {RAW_DATA_DIR}")
        logger.info("Run 'python3 run_metric_propagation_subcause_experiments.py' first")
        return [], []

    json_files = list(RAW_DATA_DIR.glob("*.json"))

    if not json_files:
        logger.error(f"No JSON files found in {RAW_DATA_DIR}")
        return [], []

    logger.info(f"Found {len(json_files)} JSON files")

    for json_file in sorted(json_files):
        logger.info(f"Processing: {json_file.name}")

        try:
            with open(json_file) as f:
                samples = json.load(f)

            if not isinstance(samples, list):
                samples = [samples]

            for sample in samples:
                sub_cause = sample.get("sub_cause")

                if sub_cause not in SUB_CAUSES:
                    logger.warning(f"  Unknown sub_cause: {sub_cause}, skipping")
                    continue

                try:
                    features = extract_features(sample)

                    if np.any(np.isnan(features)) or np.any(np.isinf(features)):
                        logger.warning(f"  Invalid features (NaN/Inf), skipping")
                        continue

                    features_list.append(features)
                    labels_list.append(sub_cause)

                except Exception as e:
                    logger.warning(f"  Failed to extract features: {e}")
                    continue

            logger.info(f"  Extracted {len(samples)} samples")

        except Exception as e:
            logger.error(f"  Failed to load {json_file.name}: {e}")
            continue

    return features_list, labels_list


def create_train_val_test_split(
    features: np.ndarray,
    labels: np.ndarray,
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    random_state: int = 42
) -> Dict[str, Tuple[np.ndarray, np.ndarray]]:
    """Split data into train/val/test sets."""
    try:
        X_train, X_temp, y_train, y_temp = train_test_split(
            features, labels,
            test_size=(val_ratio + test_ratio),
            random_state=random_state,
            stratify=labels
        )

        relative_test_ratio = test_ratio / (val_ratio + test_ratio)
        X_val, X_test, y_val, y_test = train_test_split(
            X_temp, y_temp,
            test_size=relative_test_ratio,
            random_state=random_state,
            stratify=y_temp
        )
    except ValueError:
        logger.warning("Using non-stratified split due to small class sizes")
        n = len(features)
        indices = np.random.permutation(n)
        train_end = int(train_ratio * n)
        val_end = int((train_ratio + val_ratio) * n)

        X_train = features[indices[:train_end]]
        y_train = labels[indices[:train_end]]
        X_val = features[indices[train_end:val_end]]
        y_val = labels[indices[train_end:val_end]]
        X_test = features[indices[val_end:]]
        y_test = labels[indices[val_end:]]

    return {
        'train': (X_train, y_train),
        'val': (X_val, y_val),
        'test': (X_test, y_test),
    }


def main():
    """Main entry point"""
    logger.info("=" * 60)
    logger.info("Converting Metric Propagation Sub-Cause Data to Features")
    logger.info("=" * 60)

    # Load raw data
    features_list, labels_list = load_raw_data()

    if not features_list:
        logger.error("No data to convert. Exiting.")
        return

    # Convert to numpy arrays
    X = np.array(features_list, dtype=np.float32)
    y = np.array(labels_list)

    logger.info(f"\nTotal samples: {len(X)}")
    logger.info(f"Feature shape: {X.shape}")

    # Print label distribution
    logger.info("\nLabel distribution:")
    unique, counts = np.unique(y, return_counts=True)
    for label, count in zip(unique, counts):
        logger.info(f"  {label}: {count} ({100*count/len(y):.1f}%)")

    # Split data
    logger.info("\nSplitting data (70% train, 15% val, 15% test)...")
    splits = create_train_val_test_split(X, y)

    # Save splits
    logger.info("\nSaving to disk...")

    for split_name, (X_split, y_split) in splits.items():
        output_path = OUTPUT_DIR / f"metric_propagation_{split_name}.npz"
        np.savez(
            output_path,
            features=X_split,
            labels=y_split,
            feature_names=FEATURE_NAMES,
            sub_causes=SUB_CAUSES
        )
        logger.info(f"  {split_name}: {len(X_split)} samples -> {output_path.name}")

    # Save metadata
    metadata = {
        "feature_names": FEATURE_NAMES,
        "sub_causes": SUB_CAUSES,
        "n_features": len(FEATURE_NAMES),
        "n_classes": len(SUB_CAUSES),
        "total_samples": len(X),
        "splits": {
            name: {
                "n_samples": len(splits[name][0]),
                "label_distribution": {
                    label: int(count)
                    for label, count in zip(*np.unique(splits[name][1], return_counts=True))
                }
            }
            for name in splits
        },
        "source_dir": str(RAW_DATA_DIR),
        "created_at": str(np.datetime64('now')),
    }

    metadata_path = OUTPUT_DIR / "metric_propagation_metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"  metadata -> {metadata_path.name}")

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("CONVERSION COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Output directory: {OUTPUT_DIR}")
    logger.info(f"Total samples: {len(X)}")
    logger.info(f"Train: {len(splits['train'][0])}, Val: {len(splits['val'][0])}, Test: {len(splits['test'][0])}")


if __name__ == "__main__":
    main()
