"""
dynamic_weight_engine.py — Block 12: Dynamic Weight Generation Engine

Generates job-specific feature importance weights from JD Intelligence.

Per plan.md Block 12:
  - NEVER use globally fixed feature weights
  - Feature importance must be generated dynamically for every JD
  - The JD determines the ranking strategy, not the model designer
  - All weights must be explainable
  - All weights must normalize to 1.0
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# BASE WEIGHT PROFILES — role-specific starting points
# ─────────────────────────────────────────────────────────────────────────────

BASE_PROFILES: Dict[str, Dict[str, float]] = {
    "retrieval_ranking": {
        "combined_title_score":       0.18,
        "core_skill_score":           0.22,
        "ontology_skill_score":       0.08,
        "role_specific_depth_score":  0.15,
        "retrieval_skill_score":      0.10,
        "embedding_skill_score":      0.06,
        "yoe_score":                  0.08,
        "ai_experience_score":        0.05,
        "career_growth_score":        0.03,
        "leadership_signal":          0.02,
        "education_score":            0.02,
        "behavioral_score":           0.01,  # filled later
    },
    "research_scientist": {
        "combined_title_score":       0.10,
        "core_skill_score":           0.15,
        "ontology_skill_score":       0.10,
        "role_specific_depth_score":  0.12,
        "research_depth_score":       0.18,
        "education_score":            0.12,
        "yoe_score":                  0.06,
        "ai_experience_score":        0.07,
        "career_growth_score":        0.03,
        "leadership_signal":          0.02,
        "behavioral_score":           0.01,
    },
    "ml_engineer": {
        "combined_title_score":       0.16,
        "core_skill_score":           0.20,
        "ontology_skill_score":       0.07,
        "role_specific_depth_score":  0.14,
        "production_ml_mentions":     0.10,
        "yoe_score":                  0.10,
        "ai_experience_score":        0.07,
        "career_growth_score":        0.05,
        "leadership_signal":          0.03,
        "education_score":            0.05,
        "behavioral_score":           0.01,
    },
    "nlp_engineer": {
        "combined_title_score":       0.14,
        "core_skill_score":           0.20,
        "ontology_skill_score":       0.08,
        "role_specific_depth_score":  0.14,
        "embedding_skill_score":      0.10,
        "yoe_score":                  0.08,
        "ai_experience_score":        0.07,
        "career_growth_score":        0.05,
        "leadership_signal":          0.03,
        "education_score":            0.07,
        "behavioral_score":           0.01,
    },
    "engineering_manager": {
        "combined_title_score":       0.12,
        "core_skill_score":           0.10,
        "role_specific_depth_score":  0.08,
        "career_growth_score":        0.15,
        "leadership_signal":          0.25,
        "yoe_score":                  0.10,
        "ai_experience_score":        0.05,
        "education_score":            0.05,
        "behavioral_score":           0.08,
        "ontology_skill_score":       0.02,
    },
    "backend_engineer": {
        "combined_title_score":       0.15,
        "core_skill_score":           0.18,
        "role_specific_depth_score":  0.12,
        "production_ml_mentions":     0.12,
        "yoe_score":                  0.12,
        "ai_experience_score":        0.08,
        "career_growth_score":        0.07,
        "leadership_signal":          0.05,
        "education_score":            0.05,
        "ontology_skill_score":       0.04,
        "behavioral_score":           0.01,
    },
    "default": {
        "combined_title_score":       0.18,
        "core_skill_score":           0.20,
        "ontology_skill_score":       0.07,
        "role_specific_depth_score":  0.12,
        "yoe_score":                  0.10,
        "ai_experience_score":        0.07,
        "career_growth_score":        0.06,
        "leadership_signal":          0.05,
        "education_score":            0.06,
        "behavioral_score":           0.05,
        "production_ml_mentions":     0.04,
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# SENIORITY MODIFIERS — adjust weights based on seniority level
# ─────────────────────────────────────────────────────────────────────────────

SENIORITY_MODIFIERS: Dict[str, Dict[str, float]] = {
    "intern":    {"yoe_score": -0.05, "education_score": +0.05, "leadership_signal": -0.03},
    "junior":    {"yoe_score": -0.03, "education_score": +0.02, "leadership_signal": -0.02},
    "mid":       {},  # No change
    "senior":    {"role_specific_depth_score": +0.03, "leadership_signal": +0.02, "education_score": -0.02},
    "staff":     {"leadership_signal": +0.05, "role_specific_depth_score": +0.03, "education_score": -0.02},
    "principal": {"leadership_signal": +0.07, "role_specific_depth_score": +0.05, "education_score": -0.03},
    "architect":  {"leadership_signal": +0.08, "role_specific_depth_score": +0.06},
    "manager":   {"leadership_signal": +0.12, "career_growth_score": +0.05, "core_skill_score": -0.05},
}


def _normalize_weights(weights: Dict[str, float]) -> Dict[str, float]:
    """Normalize weights to sum to 1.0."""
    total = sum(weights.values())
    if total <= 0:
        return weights
    return {k: round(v / total, 6) for k, v in weights.items()}


def _apply_seniority_modifiers(weights: Dict[str, float], seniority: str) -> Dict[str, float]:
    """Apply seniority-specific adjustments to base weights."""
    modifiers = SENIORITY_MODIFIERS.get(seniority, {})
    result = dict(weights)
    for key, delta in modifiers.items():
        if key in result:
            result[key] = max(0.0, result[key] + delta)
        # Skip if feature doesn't exist in this profile
    return result


def _apply_skill_presence_boosts(
    weights: Dict[str, float],
    mandatory_skills: List[str],
    preferred_skills: List[str],
) -> Dict[str, float]:
    """
    Boost weights based on which skills are mandatory.
    If retrieval skills are mandatory → boost retrieval_skill_score.
    If embeddings are mandatory → boost embedding_skill_score.
    """
    result = dict(weights)

    mandatory_set = set(mandatory_skills)
    retrieval_mandatory = any(
        s in mandatory_set
        for s in ["faiss", "elasticsearch", "opensearch", "milvus", "vector-database", "bm25"]
    )
    embedding_mandatory = any(
        s in mandatory_set
        for s in ["sentence-transformers", "bge", "e5", "embeddings", "bi-encoder"]
    )
    ranking_mandatory = any(
        s in mandatory_set
        for s in ["learning-to-rank", "ndcg", "mrr", "lambdamart"]
    )
    llm_mandatory = any(
        s in mandatory_set
        for s in ["llm", "rag", "bert", "fine-tuning", "transformers"]
    )

    if retrieval_mandatory and "retrieval_skill_score" in result:
        result["retrieval_skill_score"] = result.get("retrieval_skill_score", 0.05) + 0.04
    if embedding_mandatory and "embedding_skill_score" in result:
        result["embedding_skill_score"] = result.get("embedding_skill_score", 0.05) + 0.03
    if ranking_mandatory and "role_specific_depth_score" in result:
        result["role_specific_depth_score"] += 0.03
    if llm_mandatory and "core_skill_score" in result:
        result["core_skill_score"] += 0.02

    return result


def generate_dynamic_weights(jd_intelligence: Dict) -> Dict:
    """
    Generate dynamic feature importance weights from JD intelligence.

    Args:
        jd_intelligence: Output from jd_intelligence_engine.parse_jd()

    Returns:
        DynamicWeightProfile dict with:
          - feature_weights: Dict[str, float] summing to 1.0
          - explanations: Dict[str, str] explaining each weight decision
          - scoring_profile: high-level description
    """
    primary_role = jd_intelligence.get("primary_role_type", "default")
    seniority = jd_intelligence.get("seniority", "senior")
    mandatory_skills = jd_intelligence.get("mandatory_skills", [])
    preferred_skills = jd_intelligence.get("preferred_skills", [])
    leadership_required = jd_intelligence.get("leadership_required", False)
    research_required = jd_intelligence.get("research_required", False)

    logger.info(f"Generating dynamic weights for role={primary_role}, seniority={seniority}")

    # 1. Select base profile
    base = dict(BASE_PROFILES.get(primary_role, BASE_PROFILES["default"]))

    # 2. Apply seniority modifiers
    weights = _apply_seniority_modifiers(base, seniority)

    # 3. Apply skill presence boosts
    weights = _apply_skill_presence_boosts(weights, mandatory_skills, preferred_skills)

    # 4. Leadership boost
    if leadership_required and "leadership_signal" in weights:
        weights["leadership_signal"] = weights.get("leadership_signal", 0.05) + 0.06

    # 5. Research boost
    if research_required:
        weights["research_depth_score"] = weights.get("research_depth_score", 0.02) + 0.08
        if "education_score" in weights:
            weights["education_score"] += 0.04

    # 6. Clamp all to [0, 1]
    weights = {k: max(0.0, min(1.0, v)) for k, v in weights.items()}

    # 7. Normalize
    normalized = _normalize_weights(weights)

    # 8. Generate explanations
    explanations = _generate_weight_explanations(
        normalized, primary_role, seniority, mandatory_skills,
        leadership_required, research_required
    )

    return {
        "primary_role": primary_role,
        "seniority": seniority,
        "feature_weights": normalized,
        "explanations": explanations,
        "scoring_profile": _describe_scoring_profile(primary_role, seniority),
    }


def _generate_weight_explanations(
    weights: Dict[str, float],
    primary_role: str,
    seniority: str,
    mandatory_skills: List[str],
    leadership_required: bool,
    research_required: bool,
) -> Dict[str, str]:
    """Generate human-readable explanations for weight decisions."""
    explanations = {}

    if weights.get("combined_title_score", 0) > 0.15:
        explanations["combined_title_score"] = (
            f"High weight: role alignment is critical for {primary_role}"
        )
    if weights.get("core_skill_score", 0) > 0.18:
        explanations["core_skill_score"] = (
            f"High weight: {len(mandatory_skills)} mandatory technical skills identified"
        )
    if weights.get("leadership_signal", 0) > 0.10:
        explanations["leadership_signal"] = (
            "High weight: JD explicitly requires mentoring/leading engineers"
        )
    if weights.get("research_depth_score", 0) > 0.08:
        explanations["research_depth_score"] = (
            "High weight: JD requires research depth (publications/novel algorithms)"
        )
    if weights.get("role_specific_depth_score", 0) > 0.12:
        explanations["role_specific_depth_score"] = (
            f"High weight: {seniority}-level role requires deep domain expertise"
        )

    return explanations


def _describe_scoring_profile(primary_role: str, seniority: str) -> str:
    profiles = {
        "retrieval_ranking": "Retrieval & Ranking Engineer profile: heavy emphasis on search systems, embeddings, and production ranking experience",
        "research_scientist": "Research Scientist profile: emphasis on research depth, academic credentials, and novel algorithm development",
        "ml_engineer": "ML Engineer profile: balanced emphasis on production ML systems, deployment, and technical depth",
        "nlp_engineer": "NLP Engineer profile: emphasis on language models, embeddings, and NLP-specific depth",
        "engineering_manager": "Engineering Manager profile: leadership, mentoring, and career growth weighted above technical depth",
        "backend_engineer": "Backend Engineer profile: systems engineering, production experience, and technical depth",
    }
    base = profiles.get(primary_role, "Standard ML Engineer profile")
    return f"{base} at {seniority} level."


# ─────────────────────────────────────────────────────────────────────────────
# SINGLETON — cached weight profile for the competition JD
# ─────────────────────────────────────────────────────────────────────────────

_cached_weight_profile: Optional[Dict] = None


def get_weight_profile(jd_intelligence: Optional[Dict] = None) -> Dict:
    """
    Returns the cached DynamicWeightProfile.
    If jd_intelligence is provided, regenerates fresh weights.
    """
    global _cached_weight_profile
    if jd_intelligence is not None:
        return generate_dynamic_weights(jd_intelligence)
    if _cached_weight_profile is None:
        from redrob_ranker.engines.jd_intelligence_engine import get_jd_intelligence
        _cached_weight_profile = generate_dynamic_weights(get_jd_intelligence())
    return _cached_weight_profile
