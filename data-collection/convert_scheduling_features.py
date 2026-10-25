#!/usr/bin/env python3
"""
Convert Scheduling Sub-Cause Raw Data to Training Features

Reads JSON files from raw_data/scheduling_subcauses/ and converts them
to the 11-feature format expected by the scheduling explainer model.

Output:
- features/scheduling_train.npz
- features/scheduling_val.npz
- features/scheduling_test.npz
- features/scheduling_metadata.json

Usage:
    python3 convert_scheduling_features.py
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
RAW_DATA_DIR = Path(__file__).parent / "raw_data" / "scheduling_subcauses"
OUTPUT_DIR = Path(__file__).parent / "features" / "scheduling"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FEATURE_NAMES = [
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

# Sub-cause labels
SUB_CAUSES = [
    "taint_conflict",
    "resource_quota_exceeded",
    "node_affinity_mismatch",
    "pdb_violation",
    "insufficient_resources",
]


def extract_features(sample: Dict) -> np.ndarray:
    """
    Extract 11 features from a raw sample.

    Args:
        sample: Dictionary with raw metrics from experiment

    Returns:
        numpy array of 11 features
    """
    scheduling_duration = float(sample.get("scheduling_duration_seconds", 0))
    scheduling_attempts = float(sample.get("scheduling_attempts", 1))
    has_node_selector = float(sample.get("has_node_selector", 0))
    has_node_affinity = float(sample.get("has_node_affinity", 0))
    has_tolerations = float(sample.get("has_tolerations", 0))
    pod_priority = float(sample.get("pod_priority", 0))
    cpu_request = float(sample.get("cpu_request_millicores", 100))
    memory_request = float(sample.get("memory_request_mb", 128))
    node_count = float(sample.get("node_count_in_cluster", 1))
    available_cpu = float(sample.get("available_cpu_millicores", 2000))

    resource_pressure = float(sample.get("resource_pressure_score", 0))
    if resource_pressure == 0 and available_cpu > 0:
        resource_pressure = cpu_request / available_cpu

    # Build feature array (11 features)
    features = np.array([
        scheduling_duration,
        scheduling_attempts,
        has_node_selector,
        has_node_affinity,
        has_tolerations,
        pod_priority,
        cpu_request,
        memory_request,
        node_count,
        available_cpu,
        resource_pressure,

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
        logger.info("Run 'python3 run_scheduling_subcause_experiments.py' first")
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
    # First split: train vs (val + test)
    try:
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
    except ValueError:
        # Fall back to non-stratified split if not enough samples
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
    logger.info("Converting Scheduling Sub-Cause Data to Features")
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
        output_path = OUTPUT_DIR / f"scheduling_{split_name}.npz"
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

    metadata_path = OUTPUT_DIR / "scheduling_metadata.json"
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

    logger.info("\nNext steps:")
    logger.info("1. Copy features to ml-integration:")
    logger.info(f"   cp {OUTPUT_DIR}/* ../ml-integration/data/scheduling/")
    logger.info("2. Retrain scheduling explainer:")
    logger.info("   cd ../ml-integration && python3 train_scheduling_explainer.py --use-real-data")


if __name__ == "__main__":
    main()
