#!/usr/bin/env python3
"""
Convert Cold Start Sub-Cause Raw Data to Training Features

Reads JSON files from raw_data/cold_start_subcauses/ and converts them
to the 15-feature format expected by the cold start explainer model.

Output:
- features/cold_start_train.npz
- features/cold_start_val.npz
- features/cold_start_test.npz
- features/cold_start_metadata.json

Usage:
    python3 convert_cold_start_features.py
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
RAW_DATA_DIR = Path(__file__).parent / "raw_data" / "cold_start_subcauses"
OUTPUT_DIR = Path(__file__).parent / "features" / "cold_start"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Features
FEATURE_NAMES = [
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

# Sub-cause labels
SUB_CAUSES = [
    "image_pull_latency",
    "init_container_delay",
    "readiness_probe_failure",
    "container_runtime_slow",
    "registry_timeout",
]


def extract_features(sample: Dict) -> np.ndarray:
    """
    Extract 15 features from a raw sample.

    Args:
        sample: Dictionary with raw metrics from experiment

    Returns:
        numpy array of 15 features
    """
    image_pull_duration = float(sample.get("image_pull_duration_seconds", 0))
    image_pull_errors = float(sample.get("image_pull_errors", 0))
    is_first_pull = float(sample.get("is_first_pull_on_node", 0))
    image_size_mb = float(sample.get("image_size_estimate_mb", 100))

    init_container_count = float(sample.get("init_container_count", 0))
    init_container_duration = float(sample.get("init_container_duration_seconds", 0))

    readiness_failures = float(sample.get("readiness_probe_failures", 0))
    probe_period = float(sample.get("readiness_probe_period_seconds", 10))
    probe_timeout = float(sample.get("readiness_probe_timeout_seconds", 1))

    container_create_duration = float(sample.get("container_create_duration_seconds", 0))
    total_cold_start = float(sample.get("total_cold_start_seconds", 0))

    # If total_cold_start is 0, estimate from components
    if total_cold_start <= 0:
        total_cold_start = (
            image_pull_duration +
            init_container_duration +
            container_create_duration +
            readiness_failures * probe_period
        )

    # Ensure minimum value to avoid division by zero
    total_cold_start = max(total_cold_start, 0.001)

    # Calculate derived ratios
    image_pull_ratio = image_pull_duration / total_cold_start
    init_container_ratio = init_container_duration / total_cold_start
    container_create_ratio = container_create_duration / total_cold_start

    # Probe failure rate
    expected_probes = max(total_cold_start / probe_period, 1)
    probe_failure_rate = readiness_failures / expected_probes

    # Build feature array
    features = np.array([
        image_pull_duration,
        image_pull_errors,
        is_first_pull,
        image_size_mb,
        init_container_count,
        init_container_duration,
        readiness_failures,
        probe_period,
        probe_timeout,
        container_create_duration,
        total_cold_start,
        image_pull_ratio,
        init_container_ratio,
        probe_failure_rate,
        container_create_ratio,
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
        logger.info("Run 'python3 run_cold_start_subcause_experiments.py' first")
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
    """
    Split data into train/val/test sets.

    Args:
        features: Feature matrix (N x 15)
        labels: Label array (N,)
        train_ratio: Proportion for training
        val_ratio: Proportion for validation
        test_ratio: Proportion for testing
        random_state: Random seed for reproducibility

    Returns:
        Dictionary with 'train', 'val', 'test' keys containing (X, y) tuples
    """
    # First split: train vs (val + test)
    X_train, X_temp, y_train, y_temp = train_test_split(
        features, labels,
        test_size=(val_ratio + test_ratio),
        random_state=random_state,
        stratify=labels
    )

    # Second split: val vs test
    relative_test_ratio = test_ratio / (val_ratio + test_ratio)
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp,
        test_size=relative_test_ratio,
        random_state=random_state,
        stratify=y_temp
    )

    return {
        'train': (X_train, y_train),
        'val': (X_val, y_val),
        'test': (X_test, y_test),
    }


def main():
    """Main entry point"""
    logger.info("=" * 60)
    logger.info("Converting Cold Start Sub-Cause Data to Features")
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

    # Check minimum samples
    min_samples = min(counts)
    if min_samples < 5:
        logger.warning(f"\nWarning: Some classes have very few samples ({min_samples})")
        logger.warning("Consider collecting more data for balanced training")

    # Split data
    logger.info("\nSplitting data (70% train, 15% val, 15% test)...")

    try:
        splits = create_train_val_test_split(X, y)
    except ValueError as e:
        logger.warning(f"Stratified split failed: {e}")
        logger.info("Using non-stratified split instead...")

        # Simple split without stratification
        n = len(X)
        indices = np.random.permutation(n)
        train_end = int(0.7 * n)
        val_end = int(0.85 * n)

        splits = {
            'train': (X[indices[:train_end]], y[indices[:train_end]]),
            'val': (X[indices[train_end:val_end]], y[indices[train_end:val_end]]),
            'test': (X[indices[val_end:]], y[indices[val_end:]]),
        }

    # Save splits
    logger.info("\nSaving to disk...")

    for split_name, (X_split, y_split) in splits.items():
        output_path = OUTPUT_DIR / f"cold_start_{split_name}.npz"
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

    metadata_path = OUTPUT_DIR / "cold_start_metadata.json"
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
