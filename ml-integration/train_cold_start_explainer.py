"""
Train Cold Start Explainer Model

Trains a model to identify sub-causes of cold start delays:
- image_pull_latency
- init_container_delay
- readiness_probe_failure
- container_runtime_slow
- registry_timeout

Uses REAL experimental data from data-collection/raw_data/
"""

import os
import pickle
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import LeaveOneOut, cross_val_score
from sklearn.pipeline import Pipeline
import warnings
warnings.filterwarnings('ignore')

from features.cold_start_features import ColdStartFeatureExtractor

# Directories
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, 'results', 'explainers')
DATA_DIR = os.path.join(SCRIPT_DIR, 'data', 'cold_start')
os.makedirs(OUTPUT_DIR, exist_ok=True)


def load_real_data() -> tuple:
    """
    Load real experimental data from .npz files.

    Returns:
        Tuple of (X_train, y_train, X_test, y_test, feature_names, sub_causes)
    """
    train_path = os.path.join(DATA_DIR, 'cold_start_train.npz')
    val_path = os.path.join(DATA_DIR, 'cold_start_val.npz')
    test_path = os.path.join(DATA_DIR, 'cold_start_test.npz')

    if not all(os.path.exists(p) for p in [train_path, val_path, test_path]):
        raise FileNotFoundError(
            f"Real data files not found in {DATA_DIR}. "
            "Run data collection experiments first."
        )

    train_data = np.load(train_path, allow_pickle=True)
    val_data = np.load(val_path, allow_pickle=True)
    test_data = np.load(test_path, allow_pickle=True)

    # Combine train + val for training (since real data is limited)
    X_train = np.vstack([train_data['features'], val_data['features']])
    y_train = np.concatenate([train_data['labels'], val_data['labels']])

    X_test = test_data['features']
    y_test = test_data['labels']

    feature_names = train_data['feature_names']
    sub_causes = train_data['sub_causes']

    print(f"  Loaded real data: {len(X_train)} train, {len(X_test)} test samples")
    print(f"  Features: {list(feature_names)}")
    print(f"  Sub-causes: {list(sub_causes)}")

    return X_train, y_train, X_test, y_test, feature_names, sub_causes


def train_model(X_train, y_train, X_test, y_test, feature_names):
    """Train and evaluate the model using real experimental data."""

    label_encoder = LabelEncoder()
    y_train_encoded = label_encoder.fit_transform(y_train)
    y_test_encoded = label_encoder.transform(y_test)

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    print("Training Cold Start Explainer model on REAL data...")
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=8,
        min_samples_split=3,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train_scaled, y_train_encoded)

    print("\n" + "="*60)
    print("COLD START EXPLAINER - REAL DATA EVALUATION")
    print("="*60)

    y_pred = model.predict(X_test_scaled)

    print("\nClassification Report:")
    print(classification_report(
        y_test_encoded, y_pred,
        target_names=label_encoder.classes_
    ))

    # Per-class accuracy
    print("\nPer-Class Accuracy:")
    for i, class_name in enumerate(label_encoder.classes_):
        class_mask = y_test_encoded == i
        if class_mask.sum() > 0:
            class_acc = (y_pred[class_mask] == y_test_encoded[class_mask]).mean()
            print(f"  {class_name}: {class_acc:.1%}")

    overall_acc = (y_pred == y_test_encoded).mean()
    print(f"\nOverall Accuracy: {overall_acc:.1%}")

    # Feature importance
    print("\nTop 5 Most Important Features:")
    importances = model.feature_importances_
    indices = np.argsort(importances)[::-1][:5]
    for i, idx in enumerate(indices):
        print(f"  {i+1}. {feature_names[idx]}: {importances[idx]:.3f}")

    # Confusion matrix
    print("\nConfusion Matrix:")
    cm = confusion_matrix(y_test_encoded, y_pred)
    print(f"Classes: {list(label_encoder.classes_)}")
    print(cm)

    return model, scaler, label_encoder, overall_acc


def run_loocv(X_train, y_train, X_test, y_test):
    """
    Leave-One-Out Cross-Validation on the full dataset (train+test combined).

    Using a Pipeline ensures the scaler is re-fit on each LOO fold's training
    split, avoiding data leakage and giving an honest accuracy estimate.
    """
    label_encoder = LabelEncoder()
    X_all = np.vstack([X_train, X_test])
    y_all = label_encoder.fit_transform(np.concatenate([y_train, y_test]))

    pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('model', RandomForestClassifier(
            n_estimators=100,
            max_depth=8,
            min_samples_split=3,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1
        ))
    ])

    loo = LeaveOneOut()
    loo_scores = cross_val_score(pipeline, X_all, y_all, cv=loo, scoring='accuracy')

    print("\n" + "="*60)
    print("LEAVE-ONE-OUT CROSS-VALIDATION (LOOCV)")
    print("="*60)
    print(f"  Total samples: {len(X_all)}")
    print(f"  LOOCV Accuracy: {loo_scores.mean():.1%} ± {loo_scores.std():.1%}")
    print(f"  Folds: {len(loo_scores)}, Min: {loo_scores.min():.1%}, Max: {loo_scores.max():.1%}")
    print("  (Each fold trains on N-1 samples, tests on 1 — no data leakage)")

    return loo_scores.mean(), loo_scores.std()


def save_model(model, scaler, label_encoder):
    """Save model artifacts."""

    model_path = os.path.join(OUTPUT_DIR, 'cold_start_explainer.pkl')
    scaler_path = os.path.join(OUTPUT_DIR, 'cold_start_scaler.pkl')
    encoder_path = os.path.join(OUTPUT_DIR, 'cold_start_label_encoder.pkl')

    with open(model_path, 'wb') as f:
        pickle.dump(model, f)

    with open(scaler_path, 'wb') as f:
        pickle.dump(scaler, f)

    with open(encoder_path, 'wb') as f:
        pickle.dump(label_encoder, f)

    print(f"\nModel saved to: {model_path}")
    print(f"Scaler saved to: {scaler_path}")
    print(f"Label encoder saved to: {encoder_path}")


def test_inference():
    """Test loading and running inference with saved model."""

    print("\n" + "="*60)
    print("TESTING INFERENCE")
    print("="*60)

    model = pickle.load(open(os.path.join(OUTPUT_DIR, 'cold_start_explainer.pkl'), 'rb'))
    scaler = pickle.load(open(os.path.join(OUTPUT_DIR, 'cold_start_scaler.pkl'), 'rb'))
    label_encoder = pickle.load(open(os.path.join(OUTPUT_DIR, 'cold_start_label_encoder.pkl'), 'rb'))

    extractor = ColdStartFeatureExtractor()

    # Test cases based on real data patterns
    test_cases = [
        {
            'name': 'Image Pull Latency Case',
            'metrics': {
                'image_pull_duration_seconds': 45.0,
                'image_pull_errors': 0,
                'is_first_pull_on_node': 1,
                'image_size_estimate_mb': 500,
                'init_container_count': 0,
                'init_container_duration_seconds': 0,
                'readiness_probe_failures': 1,
                'readiness_probe_period_seconds': 10,
                'readiness_probe_timeout_seconds': 1,
                'container_create_duration_seconds': 1.5,
            },
            'expected': 'image_pull_latency'
        },
        {
            'name': 'Init Container Delay Case',
            'metrics': {
                'image_pull_duration_seconds': 5.0,
                'image_pull_errors': 0,
                'is_first_pull_on_node': 0,
                'image_size_estimate_mb': 150,
                'init_container_count': 2,
                'init_container_duration_seconds': 35.0,
                'readiness_probe_failures': 0,
                'readiness_probe_period_seconds': 10,
                'readiness_probe_timeout_seconds': 1,
                'container_create_duration_seconds': 1.0,
            },
            'expected': 'init_container_delay'
        },
        {
            'name': 'Readiness Probe Failure Case',
            'metrics': {
                'image_pull_duration_seconds': 4.0,
                'image_pull_errors': 0,
                'is_first_pull_on_node': 0,
                'image_size_estimate_mb': 100,
                'init_container_count': 0,
                'init_container_duration_seconds': 0,
                'readiness_probe_failures': 8,
                'readiness_probe_period_seconds': 5,
                'readiness_probe_timeout_seconds': 1,
                'container_create_duration_seconds': 1.0,
            },
            'expected': 'readiness_probe_failure'
        },
    ]

    print("\nRunning test cases:")
    passed = 0
    for tc in test_cases:
        features = extractor.extract(tc['metrics'])
        features_scaled = scaler.transform(features.reshape(1, -1))

        probs = model.predict_proba(features_scaled)[0]
        pred_idx = np.argmax(probs)
        predicted = label_encoder.inverse_transform([pred_idx])[0]
        confidence = probs[pred_idx]

        match = "" if predicted == tc['expected'] else "x"
        if predicted == tc['expected']:
            passed += 1

        print(f"\n  {tc['name']}:")
        print(f"    Expected: {tc['expected']}")
        print(f"    Predicted: {predicted} (confidence: {confidence:.1%}) {match}")

    print(f"\n  Test Results: {passed}/{len(test_cases)} passed")

    return passed == len(test_cases)


def main():
    print("="*60)
    print("COLD START EXPLAINER TRAINING")
    print("="*60)

    print("\nLoading REAL experimental data...")
    X_train, y_train, X_test, y_test, feature_names, _ = load_real_data()

    print(f"\n>>> USING REAL EXPERIMENTAL DATA <<<")
    print(f"Train samples: {len(X_train)}")
    print(f"Test samples: {len(X_test)}")

    # Show class distribution
    unique, counts = np.unique(y_train, return_counts=True)
    print("\nTrain class distribution:")
    for cls, cnt in zip(unique, counts):
        print(f"  {cls}: {cnt}")

    # LOOCV — honest accuracy estimate before training final model
    loocv_mean, loocv_std = run_loocv(X_train, y_train, X_test, y_test)

    model, scaler, label_encoder, accuracy = train_model(
        X_train, y_train, X_test, y_test, feature_names
    )

    print(f"\n>>> MODEL TRAINED ON REAL K8s EXPERIMENTAL DATA <<<")
    print(f"    Data source: data-collection/raw_data/cold_start_subcauses/")
    print(f"    LOOCV Accuracy: {loocv_mean:.1%} ± {loocv_std:.1%} (honest estimate)")

    # Check accuracy range
    if accuracy > 0.95:
        print("\n  Note: High accuracy expected with small controlled test set")
    elif accuracy < 0.70:
        print("\n  WARNING: Accuracy < 70% - model may need more data")
    else:
        print(f"\n  Accuracy {accuracy:.1%} is in expected range")

    save_model(model, scaler, label_encoder)

    # Test inference
    test_inference()

    print("\n" + "="*60)
    print("Cold Start Explainer training complete")
    print("="*60)


if __name__ == '__main__':
    main()
