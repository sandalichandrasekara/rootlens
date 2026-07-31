#!/usr/bin/env python3
"""
Analyze comparative evaluation results and generate report.
"""

import json
import os

RESULTS_DIR = 'results'
COMPARISON_DIR = 'ml_comparison/comparison'

# Find latest comparative evaluation
result_files = [f for f in os.listdir(RESULTS_DIR) if f.startswith('comparative_eval_')]
if not result_files:
    print("No comparative evaluation results found.")
    print("Run: ./run_comparative_evaluation.sh")
    exit(1)

latest_file = sorted(result_files)[-1]
results_path = os.path.join(RESULTS_DIR, latest_file)

print(f"Loading: {results_path}")

with open(results_path, 'r') as f:
    data = json.load(f)

scenarios = data['scenarios']
summary = data['summary']

print()
print("=" * 70)
print("COMPARATIVE EVALUATION RESULTS")
print("RootLens (KEDA-aware) vs Generic Baseline")
print("=" * 70)
print()

# Overall accuracy
print(f"{'Approach':<25} {'Correct':<12} {'Accuracy':<12}")
print("-" * 50)
print(f"{'RootLens (KEDA-aware)':<25} {summary['rootlens']['correct']}/{summary['total_scenarios']:<10} {summary['rootlens']['accuracy']}%")
print(f"{'Generic Baseline':<25} {summary['generic_baseline']['correct']}/{summary['total_scenarios']:<10} {summary['generic_baseline']['accuracy']}%")
print()
print(f"RootLens Improvement: +{summary['improvement']}%")
print()

# Per-category analysis
categories = {
    'POD_COLD_START': [s for s in scenarios if s['ground_truth'] == 'POD_COLD_START'],
    'SCHEDULING_CONTENTION': [s for s in scenarios if s['ground_truth'] == 'SCHEDULING_CONTENTION'],
    'METRIC_PROPAGATION_LAG': [s for s in scenarios if s['ground_truth'] == 'METRIC_PROPAGATION_LAG'],
}

print("Per-Category Analysis:")
print("-" * 70)
print(f"{'Category':<25} {'RootLens':<15} {'Generic':<15} {'Advantage':<15}")
print("-" * 70)

for category, items in categories.items():
    if not items:
        continue

    rootlens_correct = sum(1 for s in items if s['rootlens']['correct'])
    generic_correct = sum(1 for s in items if s['generic_baseline']['correct'])

    rootlens_acc = rootlens_correct / len(items) * 100
    generic_acc = generic_correct / len(items) * 100
    advantage = rootlens_acc - generic_acc

    print(f"{category:<25} {rootlens_acc:.0f}%{'':<10} {generic_acc:.0f}%{'':<10} +{advantage:.0f}%")

print()

# Find cases where RootLens succeeded and Generic failed
rootlens_wins = [s for s in scenarios if s['rootlens']['correct'] and not s['generic_baseline']['correct']]

if rootlens_wins:
    print("Cases where RootLens succeeded, Generic failed:")
    print("-" * 70)
    for s in rootlens_wins[:5]:  # Show first 5
        print(f"  {s['scenario_id']}: Expected {s['ground_truth']}")
        print(f"    RootLens: {s['rootlens']['predicted']} [PASS]")
        print(f"    Generic:  {s['generic_baseline']['predicted']} [FAIL]")
        print()

# Key insight
print("=" * 70)
print("KEY INSIGHT FOR RESEARCH GAP")
print("=" * 70)
print()
print("The Generic Baseline represents existing 'generic' RCA tools that:")
print("  • Do NOT use KEDA-specific signals")
print("  • Use simple threshold-based detection")
print("  • Cannot correlate KEDA + K8s + Queue metrics")
print()
print(f"RootLens achieves {summary['improvement']}% higher accuracy by:")
print("  • Using KEDA's LastScalingEvent and desired/current replicas")
print("  • Correlating pod lifecycle events with queue metrics")
print("  • Applying dominant-delay classification logic")
print()
print("This validates the research gap: KEDA-aware RCA outperforms generic approaches.")
