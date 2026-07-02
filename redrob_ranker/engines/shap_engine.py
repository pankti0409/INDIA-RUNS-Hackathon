"""
shap_engine.py — SHAP Explanations & Feature Importance Engine (Block 8)

Implements:
- Per-candidate SHAP value computation using TreeExplainer
- Recruiter-quality explanations ("Why this candidate ranked high/low")
- Global feature importance summary report
- Rule-based fallback when SHAP or trained model is unavailable

Plan.md references:
  Block 8 §3: SHAP Analysis — global importance, candidate-level importance
  Block 8 §17: Automated Reports — feature importance report, SHAP summary
  Block 4 §17: Explainability — every reranking decision should explain why
  Final §Explainability — every candidate must produce a recruiter-quality explanation
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

try:
    import shap
    HAS_SHAP = True
except ImportError:  # pragma: no cover
    HAS_SHAP = False

# ---------------------------------------------------------------------------
# Human-readable feature descriptions for recruiter explanations
# ---------------------------------------------------------------------------
FEATURE_DESCRIPTIONS: Dict[str, str] = {
    # Title
    "combined_title_score": "Current role alignment with the JD",
    "title_score": "Current job title relevance",
    "career_best_title_score": "Best title match in career history",
    "is_disqualifier_title": "❌ Role is outside technical scope",
    "title_exact_match": "Exact JD title match",
    "title_seniority_gap": "Seniority alignment with JD",
    # Skills
    "core_skill_score": "Core required skill coverage",
    "ontology_skill_score": "Ontology-enriched skill match",
    "jd_skill_soft_coverage": "Skill-graph expanded JD coverage",
    "jd_skill_exact_coverage": "Exact required skill match",
    "retrieval_skill_score": "Retrieval & vector search expertise",
    "embedding_skill_score": "Embedding & dense retrieval expertise",
    "preferred_skill_score": "Preferred skill match",
    "skill_diversity_score": "Breadth of technical skills",
    "skill_freshness_score": "Recency of skill experience",
    "skill_cluster_coverage": "Domain cluster coverage",
    "missing_critical_skills_ratio": "❌ Missing critical skills",
    # Experience
    "role_specific_depth_score": "Role-specific depth (vector search, ranking, etc.)",
    "semantic_similarity_score": "Semantic match with JD",
    "cross_encoder_score": "Deep semantic compatibility (cross-encoder)",
    "yoe_score": "Years of experience alignment",
    "ai_experience_score": "AI/ML domain experience",
    "product_company_score": "Product company background",
    "architecture_exp_score": "Architecture & system design experience",
    "deployment_exp_score": "Production deployment experience",
    "ownership_exp_score": "Engineering ownership evidence",
    "mentoring_exp_score": "Mentorship & leadership evidence",
    # Candidate intelligence
    "engineering_maturity_score": "Engineering maturity signal",
    "project_complexity_score": "Project complexity & technical depth",
    "leadership_evidence_score": "Leadership evidence strength",
    "scale_evidence_score": "Large-scale system experience",
    "business_impact_score": "Business impact evidence",
    "research_depth_score": "Research & publication depth",
    "transferable_skill_score": "Transferable skill alignment",
    # Company
    "company_quality_score": "Employer caliber signal",
    "industry_relevance_score": "Industry relevance",
    "has_big_tech_experience": "Big Tech / top-tier employer background",
    "has_search_ranking_experience": "Direct search/ranking company background",
    # Responsibility verbs
    "resp_designed_freq": "System design ownership",
    "resp_led_freq": "Engineering leadership",
    "resp_owned_freq": "End-to-end ownership",
    "resp_optimized_freq": "Performance optimization track record",
    "resp_scaled_freq": "Scaling system experience",
    "resp_architected_freq": "Architecture contributions",
    # Production
    "production_at_scale": "Proven production-at-scale experience",
    "has_production_at_scale": "Production ML at scale",
    "production_ml_mentions": "Production ML evidence in profile",
    # Career
    "career_coherence_score": "Career narrative coherence",
    "career_growth_score": "Career growth trajectory",
    "career_momentum_score": "Career momentum (recent acceleration)",
    "promotion_velocity_score": "Promotion speed",
    # Behavior / availability
    "hireability_probability": "Behavioral hireability signal",
    "availability_score": "Availability & urgency",
    "active_recently": "Recently active on platform",
    "open_to_work_flag": "Open to work",
    # Risk / trust
    "risk_probability": "❌ Risk / honeypot probability",
    "trust_score": "Profile authenticity score",
    "evidence_confidence_score": "Evidence confidence",
    "feature_confidence_score": "Overall feature confidence",
    # Graph
    "jd_domain_coverage": "JD domain coverage via skill graph",
    "skill_graph_coverage": "Skill graph alignment",
    # GitHub
    "github_score": "GitHub activity & open source",
    "strong_github": "Strong GitHub contributions",
    # Education
    "education_score": "Education quality & relevance",
    "advanced_degree": "PhD / M.Tech degree signal",
    # Interaction
    "title_x_skills": "Title × Skill compatibility",
    "projects_x_leadership": "Projects × Leadership evidence",
    "experience_x_company": "Experience × Company quality",
}

_NEGATIVE_FEATURES = {
    "is_disqualifier_title",
    "is_pure_consulting",
    "missing_critical_skills_ratio",
    "risk_probability",
}


def _feature_direction(fname: str, value: float) -> str:
    """Return '+' if this feature-value combination is a positive signal."""
    if fname in _NEGATIVE_FEATURES:
        return "-" if value > 0.3 else "+"
    return "+" if value > 0.3 else "-"


# ---------------------------------------------------------------------------
# Rule-based explanation (fallback)
# ---------------------------------------------------------------------------

def _rule_based_explanation(feature_dict: Dict[str, Any], top_k: int = 5) -> Dict[str, Any]:
    """
    Build a recruiter explanation without SHAP by ranking features by value.
    Used when no trained LTR model is available.
    """
    ranked_positive: List[Tuple[str, float]] = []
    ranked_negative: List[Tuple[str, float]] = []

    for fname, fdesc in FEATURE_DESCRIPTIONS.items():
        val = float(feature_dict.get(fname, 0.0))
        if fname in _NEGATIVE_FEATURES:
            if val > 0.3:
                ranked_negative.append((fname, val))
        else:
            if val >= 0.6:
                ranked_positive.append((fname, val))
            elif val < 0.25:
                ranked_negative.append((fname, val))

    ranked_positive.sort(key=lambda x: x[1], reverse=True)
    ranked_negative.sort(key=lambda x: x[1] if x[0] in _NEGATIVE_FEATURES else (1 - x[1]))

    strengths = [
        {"feature": fn, "value": round(fv, 3), "description": FEATURE_DESCRIPTIONS.get(fn, fn)}
        for fn, fv in ranked_positive[:top_k]
    ]
    concerns = [
        {"feature": fn, "value": round(fv, 3), "description": FEATURE_DESCRIPTIONS.get(fn, fn)}
        for fn, fv in ranked_negative[:top_k]
    ]

    return {"strengths": strengths, "concerns": concerns, "method": "rule_based"}


# ---------------------------------------------------------------------------
# SHAP-based explanation
# ---------------------------------------------------------------------------

def explain_candidate_from_shap(
    shap_values: np.ndarray,
    feature_names: List[str],
    feature_values: np.ndarray,
    top_k: int = 5,
) -> Dict[str, Any]:
    """
    Build a recruiter explanation from SHAP values for a single candidate.

    Parameters
    ----------
    shap_values   : 1D array of SHAP values for this candidate
    feature_names : list of feature name strings
    feature_values: 1D array of raw feature values for this candidate
    top_k         : number of strengths / concerns to surface

    Returns
    -------
    Dict with 'strengths', 'concerns', 'method'
    """
    impacts = list(zip(feature_names, shap_values.tolist(), feature_values.tolist()))

    # Positive SHAP = contributed to higher rank
    positive = sorted(
        [(fn, sv, fv) for fn, sv, fv in impacts if sv > 0],
        key=lambda x: x[1],
        reverse=True,
    )[:top_k]

    # Negative SHAP = dragged score down
    negative = sorted(
        [(fn, sv, fv) for fn, sv, fv in impacts if sv < 0],
        key=lambda x: x[1],
    )[:top_k]

    strengths = [
        {
            "feature": fn,
            "shap": round(sv, 4),
            "value": round(fv, 3),
            "description": FEATURE_DESCRIPTIONS.get(fn, fn),
        }
        for fn, sv, fv in positive
    ]
    concerns = [
        {
            "feature": fn,
            "shap": round(sv, 4),
            "value": round(fv, 3),
            "description": FEATURE_DESCRIPTIONS.get(fn, fn),
        }
        for fn, sv, fv in negative
    ]

    return {"strengths": strengths, "concerns": concerns, "method": "shap"}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def explain_candidate(
    candidate_id: str,
    feature_dict: Dict[str, Any],
    shap_values: Optional[np.ndarray] = None,
    feature_names: Optional[List[str]] = None,
    candidate_idx: Optional[int] = None,
    top_k: int = 5,
) -> Dict[str, Any]:
    """
    Generate a recruiter-quality explanation for a single candidate.

    Uses SHAP if model + values are available, otherwise falls back to
    rule-based evidence ranking.

    Returns
    -------
    Dict:
      candidate_id: str
      strengths: List[{feature, value, description, [shap]}]
      concerns: List[{feature, value, description, [shap]}]
      method: 'shap' | 'rule_based'
      summary: str — one-line recruiter summary
    """
    explanation: Dict[str, Any] = {"candidate_id": candidate_id}

    if (
        shap_values is not None
        and feature_names is not None
        and candidate_idx is not None
        and HAS_SHAP
    ):
        try:
            from redrob_ranker.engines.ltr_engine import build_feature_matrix
            X_single, _ = build_feature_matrix([feature_dict], schema=feature_names)
            sv_row = shap_values[candidate_idx] if shap_values.ndim == 2 else shap_values
            detail = explain_candidate_from_shap(
                sv_row, feature_names, X_single[0], top_k=top_k
            )
        except Exception as exc:
            logger.debug(f"SHAP explanation failed, falling back: {exc}")
            detail = _rule_based_explanation(feature_dict, top_k=top_k)
    else:
        detail = _rule_based_explanation(feature_dict, top_k=top_k)

    explanation.update(detail)

    # Build one-line summary
    top_strength = explanation.get("strengths", [{}])[0].get("description", "")
    top_concern = explanation.get("concerns", [{}])[0].get("description", "")
    explanation["summary"] = _build_summary(feature_dict, top_strength, top_concern)

    return explanation


def _build_summary(
    feature_dict: Dict[str, Any], top_strength: str, top_concern: str
) -> str:
    """Build a one-line recruiter-quality summary sentence."""
    score = float(feature_dict.get("role_specific_depth_score", 0))
    maturity = float(feature_dict.get("engineering_maturity_score", 0.4))
    risk = float(feature_dict.get("risk_probability", 0))

    parts = []
    if score >= 0.7:
        parts.append("Strong role-specific depth")
    elif score >= 0.4:
        parts.append("Moderate role-specific depth")
    else:
        parts.append("Limited direct role experience")

    if maturity >= 0.7:
        parts.append("high engineering maturity")
    if top_strength:
        parts.append(f"with notable strength in: {top_strength.lower()}")
    if top_concern and risk < 0.5:
        parts.append(f"⚠ concern: {top_concern.lower()}")
    if risk >= 0.6:
        parts.append("⚠ elevated risk profile")

    return ". ".join(parts).capitalize() + "."


def batch_explain_candidates(
    candidates_with_features: List[Dict[str, Any]],
    shap_values: Optional[np.ndarray] = None,
    feature_names: Optional[List[str]] = None,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """
    Generate explanations for all candidates in a ranked list.

    Parameters
    ----------
    candidates_with_features : list of feature dicts with 'candidate_id' key
    shap_values              : optional ndarray (n_candidates, n_features)
    feature_names            : optional list of feature names matching shap_values cols
    top_k                    : features per candidate
    """
    explanations = []
    for idx, fd in enumerate(candidates_with_features):
        cid = str(fd.get("candidate_id", f"cand_{idx}"))
        expl = explain_candidate(
            cid,
            fd,
            shap_values=shap_values,
            feature_names=feature_names,
            candidate_idx=idx if shap_values is not None else None,
            top_k=top_k,
        )
        explanations.append(expl)
    return explanations


def generate_global_importance_report(
    shap_values: Optional[np.ndarray] = None,
    feature_names: Optional[List[str]] = None,
    feature_importance_gain: Optional[Dict[str, float]] = None,
) -> str:
    """
    Generate a global SHAP / feature importance markdown report.

    Can use either SHAP values or model gain importance (or both).
    """
    lines = ["# Global Feature Importance Report\n"]

    if shap_values is not None and feature_names is not None:
        # Mean absolute SHAP
        mean_abs = np.abs(shap_values).mean(axis=0)
        total = max(float(mean_abs.sum()), 1e-9)
        ranked = sorted(
            zip(feature_names, mean_abs.tolist()),
            key=lambda x: x[1],
            reverse=True,
        )[:25]

        lines.append("## Top 25 Features by Mean |SHAP|\n")
        lines.append("| Rank | Feature | Mean |SHAP| | Contribution % |")
        lines.append("|------|---------|----------|----------------|")
        for rank, (fn, mv) in enumerate(ranked, 1):
            desc = FEATURE_DESCRIPTIONS.get(fn, fn)
            lines.append(
                f"| {rank} | `{fn}` | {mv:.4f} | {mv/total*100:.1f}% |  _{desc}_ |"
            )
        lines.append("")

    if feature_importance_gain:
        lines.append("## Model Gain Importance\n")
        lines.append("| Rank | Feature | Gain % |")
        lines.append("|------|---------|--------|")
        sorted_gain = sorted(
            feature_importance_gain.items(), key=lambda x: x[1], reverse=True
        )[:20]
        for rank, (fn, gv) in enumerate(sorted_gain, 1):
            lines.append(f"| {rank} | `{fn}` | {gv*100:.2f}% |")
        lines.append("")

    if not shap_values and not feature_importance_gain:
        lines.append("_No trained model available. Run training first._\n")

    return "\n".join(lines)
