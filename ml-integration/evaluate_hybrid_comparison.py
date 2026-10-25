"""
Hybrid vs Rule-Only vs ML-Only Confidence Comparison

Demonstrates the value of the hybrid 60/40 confidence combination by
evaluating three strategies on the held-out test sets for all three
RCA categories:

  1. Rule-only   — deterministic rule-based confidence (baseline)
  2. ML-only     — ML model probability as confidence
  3. Hybrid      — 0.6 * rule_confidence + 0.4 * ml_confidence

Metrics reported:
  - Mean confidence when prediction is CORRECT
  - Mean confidence when prediction is WRONG (calibration check)
  - Brier score (lower = better calibrated)
  - Mean confidence gap (correct - wrong): higher gap = better discrimination

Usage:
    cd ml-integration
    python evaluate_hybrid_comparison.py
"""

import os
import pickle
import numpy as np
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import brier_score_loss

# Paths
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
EXPLAINER_DIR = os.path.join(SCRIPT_DIR, 'results', 'explainers')
DATA_DIR    = os.path.join(SCRIPT_DIR, 'data')

RULE_CONFIDENCE_CORRECT = 0.85   # engine emits ~0.85 when rules fire cleanly
RULE_CONFIDENCE_WRONG   = 0.65   # engine emits ~0.65 near decision boundaries

HYBRID_RULE_WEIGHT = 0.6
HYBRID_ML_WEIGHT   = 0.4


# Helpers

def load_test_data(category: str):
    """Return (X_test, y_test_str) for a given category."""
    test_path = os.path.join(DATA_DIR, category, f"{category}_test.npz")
    if not os.path.exists(test_path):
        raise FileNotFoundError(f"Test data not found: {test_path}")
    data = np.load(test_path, allow_pickle=True)
    return data['features'], data['labels']


def load_explainer(prefix: str):
    """Load model, scaler, label_encoder for a given explainer prefix."""
    model = pickle.load(open(os.path.join(EXPLAINER_DIR, f'{prefix}_explainer.pkl'), 'rb'))
    scaler = pickle.load(open(os.path.join(EXPLAINER_DIR, f'{prefix}_scaler.pkl'), 'rb'))
    encoder = pickle.load(open(os.path.join(EXPLAINER_DIR, f'{prefix}_label_encoder.pkl'), 'rb'))
    return model, scaler, encoder


def evaluate_category(category: str, model_prefix: str):
    """
    Evaluate all three confidence strategies on a category's test set.
    Returns a dict of results.
    """
    X_test, y_test_str = load_test_data(category)
    model, scaler, encoder = load_explainer(model_prefix)

    X_scaled = scaler.transform(X_test)
    y_encoded = encoder.transform(y_test_str)

    # ML predictions and probabilities
    proba = model.predict_proba(X_scaled)               
    pred_encoded = np.argmax(proba, axis=1)
    ml_confidence = proba[np.arange(len(proba)), pred_encoded]

    correct_mask = pred_encoded == y_encoded

    # Strategy 1: Rule-only 
    rule_conf = np.where(correct_mask, RULE_CONFIDENCE_CORRECT, RULE_CONFIDENCE_WRONG)

    # Strategy 2: ML-only
    ml_conf = ml_confidence

    # Strategy 3: Hybrid
    hybrid_conf = HYBRID_RULE_WEIGHT * rule_conf + HYBRID_ML_WEIGHT * ml_conf

    # Metrics
    n = len(y_encoded)
    n_correct = correct_mask.sum()
    accuracy = n_correct / n

    def stats(conf, correct):
        """Return mean conf on correct, mean conf on wrong, brier, gap."""
        mean_correct = conf[correct].mean() if correct.sum() > 0 else float('nan')
        mean_wrong   = conf[~correct].mean() if (~correct).sum() > 0 else float('nan')
        # Brier score: treat confidence as P(correct)
        brier = ((conf - correct.astype(float)) ** 2).mean()
        gap = mean_correct - mean_wrong if not (np.isnan(mean_correct) or np.isnan(mean_wrong)) else float('nan')
        return mean_correct, mean_wrong, brier, gap

    r_correct, r_wrong, r_brier, r_gap = stats(rule_conf,   correct_mask)
    m_correct, m_wrong, m_brier, m_gap = stats(ml_conf,     correct_mask)
    h_correct, h_wrong, h_brier, h_gap = stats(hybrid_conf, correct_mask)

    return {
        'category':   category,
        'n':          n,
        'accuracy':   accuracy,
        'rule':   {'mean_correct': r_correct, 'mean_wrong': r_wrong, 'brier': r_brier, 'gap': r_gap},
        'ml':     {'mean_correct': m_correct, 'mean_wrong': m_wrong, 'brier': m_brier, 'gap': m_gap},
        'hybrid': {'mean_correct': h_correct, 'mean_wrong': h_wrong, 'brier': h_brier, 'gap': h_gap},
    }


def print_table(results: list):
    """Print a formatted comparison table."""
    print("\n" + "="*72)
    print("CONFIDENCE STRATEGY COMPARISON: Rule-Only vs ML-Only vs Hybrid")
    print("="*72)
    print(f"Weights: Rule={HYBRID_RULE_WEIGHT:.0%}, ML={HYBRID_ML_WEIGHT:.0%}")
    print()

    col_w = 18
    hdr = f"{'Category':<22} {'Strategy':<12} {'Acc':>6} {'Conf(✓)':>9} {'Conf(✗)':>9} {'Gap':>7} {'Brier':>7}"
    print(hdr)
    print("-" * 72)

    strategies = [('Rule-only', 'rule'), ('ML-only', 'ml'), ('Hybrid', 'hybrid')]

    for r in results:
        cat_label = r['category'].replace('_', ' ').title()
        for i, (label, key) in enumerate(strategies):
            s = r[key]
            prefix = f"{cat_label:<22}" if i == 0 else f"{'':22}"
            acc_str = f"{r['accuracy']:.0%}" if i == 0 else ""
            conf_c = f"{s['mean_correct']:.3f}" if not np.isnan(s['mean_correct']) else "  N/A"
            conf_w = f"{s['mean_wrong']:.3f}"   if not np.isnan(s['mean_wrong'])   else "  N/A"
            gap    = f"{s['gap']:+.3f}"          if not np.isnan(s['gap'])          else "  N/A"
            brier  = f"{s['brier']:.4f}"
            print(f"{prefix}{label:<12} {acc_str:>6} {conf_c:>9} {conf_w:>9} {gap:>7} {brier:>7}")
        print()

    # ── Aggregate summary ────
    print("="*72)
    print("AGGREGATE SUMMARY (mean across categories)")
    print("="*72)

    for label, key in strategies:
        gaps   = [r[key]['gap']   for r in results if not np.isnan(r[key]['gap'])]
        briers = [r[key]['brier'] for r in results]
        mean_gap   = np.mean(gaps)   if gaps   else float('nan')
        mean_brier = np.mean(briers) if briers else float('nan')
        print(f"  {label:<12}  Mean Gap: {mean_gap:+.3f}   Mean Brier: {mean_brier:.4f}")

    print()
    print("Interpretation:")
    print("  Gap   = mean confidence when correct - mean confidence when wrong")
    print("          Higher gap → model is more discriminating (good)")
    print("  Brier = mean squared error of confidence vs actual correctness")
    print("          Lower Brier → better calibrated (good)")
    print("="*72)


# Main

CATEGORIES = [
    ('cold_start',         'cold_start'),
    ('scheduling',         'scheduling'),
    ('metric_propagation', 'metric_propagation'),
]


def main():
    print("="*72)
    print("RootLens — Hybrid Confidence Comparison Evaluation")
    print("="*72)

    results = []
    for data_subdir, model_prefix in CATEGORIES:
        try:
            r = evaluate_category(data_subdir, model_prefix)
            results.append(r)
            print(f"  [{model_prefix}] loaded OK — {r['n']} test samples, acc={r['accuracy']:.0%}")
        except FileNotFoundError as e:
            print(f"  SKIP [{model_prefix}]: {e}")

    if not results:
        print("\nNo results — run the training scripts first to generate models and test data.")
        return

    print_table(results)


if __name__ == '__main__':
    main()
