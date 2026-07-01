"""
weight_optimizer.py — Module 10: Weight Optimization Engine
Sensitivity analysis + grid search over scoring weights.
Uses synthetic relevance labels derived from domain rules.
No external API, no LightGBM training — pure analytical optimization.
"""
import itertools
import logging
from typing import Dict, List, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# SYNTHETIC LABEL GENERATION
# ─────────────────────────────────────────────────────────────

def generate_synthetic_labels(features_list: List[Dict]) -> List[float]:
    """
    Generate pseudo-relevance labels from domain rules (no ground truth needed).
    Returns list of relevance scores in [0, 1].
    
    Rule: A candidate is "relevant" if they have:
    - ML/AI title (title_score ≥ 0.8)
    - Core AI skills (core_skill_count ≥ 0.4)
    - Appropriate experience (yoe_score ≥ 0.5)
    - Not a honeypot (honeypot_probability < 0.3)
    """
    labels = []
    for feat in features_list:
        title = feat.get("title_score", 0)
        skills = feat.get("core_skill_count", 0)
        yoe = feat.get("yoe_score", 0)
        hp = feat.get("honeypot_probability", 0)
        product = feat.get("has_product_company", 0)

        label = (
            0.40 * title
            + 0.30 * skills
            + 0.15 * yoe
            + 0.10 * product
            + 0.05 * (1.0 - hp)
        )
        labels.append(round(min(1.0, label), 4))
    return labels


def _ndcg_at_k(scores: List[float], labels: List[float], k: int = 10) -> float:
    """Compute NDCG@k given ranking scores and relevance labels."""
    if not scores:
        return 0.0
    paired = sorted(zip(scores, labels), key=lambda x: -x[0])
    ideal = sorted(labels, reverse=True)[:k]
    actual = [lbl for _, lbl in paired[:k]]

    def dcg(rels):
        return sum(r / np.log2(i + 2) for i, r in enumerate(rels))

    idcg = dcg(ideal)
    if idcg == 0:
        return 0.0
    return dcg(actual) / idcg


# ─────────────────────────────────────────────────────────────
# SENSITIVITY ANALYSIS
# ─────────────────────────────────────────────────────────────

def sensitivity_analysis(
    features_list: List[Dict],
    base_weights: Dict[str, float],
    perturbation: float = 0.20,
    top_n: int = 100,
) -> Dict[str, Dict]:
    """
    For each weight, perturb ±perturbation% and measure NDCG@10 change.
    Returns sensitivity report: {feature: {base, plus, minus, sensitivity}}.
    """
    labels = generate_synthetic_labels(features_list)

    def score_all(weights: Dict) -> List[float]:
        scores = []
        for feat in features_list:
            s = (
                weights.get("title_score", 0)         * feat.get("combined_title_score", 0)
                + weights.get("core_skill_score", 0)  * feat.get("core_skill_score", 0)
                + weights.get("experience_score", 0)  * feat.get("yoe_score", 0)
                + weights.get("behavioral_score", 0)  * feat.get("availability_score", 0)
                + weights.get("education_score", 0)   * feat.get("education_score", 0)
                + weights.get("assessment_score", 0)  * feat.get("ai_assessment_score", 0)
                + weights.get("location_score", 0)    * feat.get("location_score", 0)
                + weights.get("github_score", 0)       * feat.get("github_score", 0.2)
            )
            scores.append(s)
        return scores

    base_scores = score_all(base_weights)
    base_ndcg = _ndcg_at_k(base_scores, labels, k=10)

    report = {}
    for feat_key in base_weights:
        # +perturbation
        w_plus = {**base_weights, feat_key: base_weights[feat_key] * (1 + perturbation)}
        scores_plus = score_all(w_plus)
        ndcg_plus = _ndcg_at_k(scores_plus, labels)

        # -perturbation
        w_minus = {**base_weights, feat_key: base_weights[feat_key] * (1 - perturbation)}
        scores_minus = score_all(w_minus)
        ndcg_minus = _ndcg_at_k(scores_minus, labels)

        sensitivity = max(abs(ndcg_plus - base_ndcg), abs(ndcg_minus - base_ndcg))
        report[feat_key] = {
            "base_weight": round(base_weights[feat_key], 4),
            "ndcg_base": round(base_ndcg, 4),
            "ndcg_plus20pct": round(ndcg_plus, 4),
            "ndcg_minus20pct": round(ndcg_minus, 4),
            "sensitivity": round(sensitivity, 4),
        }

    return report


def write_feature_importance_report(
    sensitivity: Dict,
    output_path: str = "./feature_importance_report.md",
) -> str:
    """Write sensitivity analysis as markdown report."""
    lines = [
        "# Feature Importance Report\n",
        "Sensitivity analysis: each weight perturbed ±20% and NDCG@10 measured.\n",
        "| Feature | Weight | NDCG Base | +20% | -20% | Sensitivity |",
        "|---------|--------|-----------|------|------|-------------|",
    ]
    # Sort by sensitivity descending
    sorted_items = sorted(sensitivity.items(), key=lambda x: -x[1]["sensitivity"])
    for feat, data in sorted_items:
        lines.append(
            f"| {feat} | {data['base_weight']} | {data['ndcg_base']} "
            f"| {data['ndcg_plus20pct']} | {data['ndcg_minus20pct']} "
            f"| **{data['sensitivity']:.4f}** |"
        )
    lines.append("")
    lines.append("---")
    lines.append("*Higher sensitivity = feature has more impact on ranking quality.*")
    report = "\n".join(lines)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)
    return report
