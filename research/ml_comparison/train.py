import json
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import confusion_matrix, classification_report
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
import os
from datetime import datetime

# Configuration
RESULTS_DIR = 'results'
MODELS_DIR = 'ml_comparison/models'
PLOTS_DIR = 'ml_comparison/plots'

# Create directories
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(PLOTS_DIR, exist_ok=True)

print("=" * 50)
print("RootLens ML Model Training")
print("=" * 50)
print()

# Find latest test results
result_files = [f for f in os.listdir(RESULTS_DIR) if f.startswith('synthetic_run_') and f.endswith('.json')]
if not result_files:
    print("No test results found in results/")
    print("   Run ./run_synthetic_tests.sh first")
    exit(1)

latest_file = sorted(result_files)[-1]
results_path = os.path.join(RESULTS_DIR, latest_file)

print(f"Loading: {results_path}")

# Load data
with open(results_path, 'r') as f:
    data = json.load(f)

print(f"Loaded {len(data)} test scenarios")
print()

# Extract features
print("Extracting features...")
features = []
labels = []

for item in data:
    metrics = item['rca_result']['metrics']
    
    # Features: 6 metrics
    features.append([
        metrics['cold_start_delay_seconds'],
        metrics['scheduling_delay_seconds'],
        metrics['metric_lag_seconds'],
        metrics['queue_depth'],
        metrics['current_replicas'],
        metrics['desired_replicas']
    ])
    
    labels.append(item['ground_truth'])

X = np.array(features)
y = np.array(labels)

print(f"   Features shape: {X.shape}")
print(f"   Labels: {len(set(y))} unique classes")
print()

# Feature scaling
print("Scaling features...")
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Train Random Forest
print("Training Random Forest...")
rf_model = RandomForestClassifier(
    n_estimators=100,
    max_depth=10,
    random_state=42
)
rf_model.fit(X_scaled, y)
rf_pred = rf_model.predict(X_scaled)
rf_accuracy = (rf_pred == y).mean()
print(f"   Accuracy: {rf_accuracy:.2%}")

# Train SVM
print("Training SVM...")
svm_model = SVC(
    kernel='rbf',
    C=1.0,
    gamma='scale',
    random_state=42
)
svm_model.fit(X_scaled, y)
svm_pred = svm_model.predict(X_scaled)
svm_accuracy = (svm_pred == y).mean()
print(f"   Accuracy: {svm_accuracy:.2%}")
print()

# Save models
print("Saving models...")
joblib.dump(rf_model, os.path.join(MODELS_DIR, 'random_forest.pkl'))
joblib.dump(svm_model, os.path.join(MODELS_DIR, 'svm.pkl'))
joblib.dump(scaler, os.path.join(MODELS_DIR, 'scaler.pkl'))
print(f"   Saved to {MODELS_DIR}/")
print()

# Generate confusion matrices
print("Generating confusion matrices...")

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Random Forest confusion matrix
cm_rf = confusion_matrix(y, rf_pred)
sns.heatmap(cm_rf, annot=True, fmt='d', cmap='Blues', 
            xticklabels=sorted(set(y)), yticklabels=sorted(set(y)),
            ax=axes[0])
axes[0].set_title('Random Forest Confusion Matrix')
axes[0].set_ylabel('True Label')
axes[0].set_xlabel('Predicted Label')

# SVM confusion matrix
cm_svm = confusion_matrix(y, svm_pred)
sns.heatmap(cm_svm, annot=True, fmt='d', cmap='Greens',
            xticklabels=sorted(set(y)), yticklabels=sorted(set(y)),
            ax=axes[1])
axes[1].set_title('SVM Confusion Matrix')
axes[1].set_ylabel('True Label')
axes[1].set_xlabel('Predicted Label')

plt.tight_layout()
plt.savefig(os.path.join(PLOTS_DIR, 'confusion_matrices.png'), dpi=300, bbox_inches='tight')
print(f"    Saved confusion_matrices.png")

# Feature importance
print("Generating feature importance plot...")
feature_names = ['Cold Start', 'Scheduling', 'Metric Lag', 'Queue Depth', 'Current Replicas', 'Desired Replicas']
importances = rf_model.feature_importances_

plt.figure(figsize=(10, 6))
plt.barh(feature_names, importances)
plt.xlabel('Importance')
plt.title('Random Forest Feature Importance')
plt.tight_layout()
plt.savefig(os.path.join(PLOTS_DIR, 'feature_importance.png'), dpi=300, bbox_inches='tight')
print(f"    Saved feature_importance.png")
print()

# Save training summary
summary = {
    'timestamp': datetime.now().isoformat(),
    'test_file': latest_file,
    'total_scenarios': len(data),
    'models': {
        'random_forest': {
            'accuracy': float(rf_accuracy),
            'n_estimators': 100
        },
        'svm': {
            'accuracy': float(svm_accuracy),
            'kernel': 'rbf'
        }
    }
}

with open(os.path.join(MODELS_DIR, 'training_summary.json'), 'w') as f:
    json.dump(summary, f, indent=2)

print("=" * 50)
print("Training Complete!")
print("=" * 50)
print()
print("Generated files:")
print(f"  • {MODELS_DIR}/random_forest.pkl")
print(f"  • {MODELS_DIR}/svm.pkl")
print(f"  • {MODELS_DIR}/scaler.pkl")
print(f"  • {PLOTS_DIR}/confusion_matrices.png")
print(f"  • {PLOTS_DIR}/feature_importance.png")
print()
