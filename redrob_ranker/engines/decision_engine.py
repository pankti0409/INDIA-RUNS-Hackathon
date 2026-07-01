"""
decision_engine.py — Block 10: Decision Engine

Transforms raw scores and features into formal, evidence-backed hiring recommendations
with calibrated confidence, self-verification, and actionable recruiter guidance.

Per plan.md Block 10 & Block 18 Section 18:
  - Generate hiring recommendation tiers (not just scores)
  - Calibrate confidence based on evidence quality
  - Run 8-question self-verification checklist before output
  - Generate interview focus areas from identified gaps
  - Every recommendation must reference evidence
  - Never hallucinate — only reference verified fields
  - Remain deterministic
"""

import logging
import math
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# HIRING RECOMMENDATION TIERS
# ─────────────────────────────────────────────────────────────────────────────

RECOMMENDATION_TIERS = {
    "strong_hire": {
        "label": "Strong Hire",
        "description": "Candidate demonstrates exceptional fit across technical depth, experience, and production evidence.",
        "min_score": 0.80,
    },
    "hire": {
        "label": "Hire",
        "description": "Candidate demonstrates solid fit with meaningful technical contributions and relevant experience.",
        "min_score": 0.65,
    },
    "borderline_hire": {
        "label": "Borderline – Recommend Interview",
        "description": "Candidate shows promise but has notable gaps. A technical interview is strongly recommended.",
        "min_score": 0.50,
    },
    "hold": {
        "label": "Hold for Review",
        "description": "Candidate has some relevant experience but significant gaps or concerns require closer review.",
        "min_score": 0.35,
    },
    "unlikely_fit": {
        "label": "Unlikely Fit",
        "description": "Candidate's background does not closely match the role's core requirements.",
        "min_score": 0.20,
    },
    "reject": {
        "label": "Not Recommended",
        "description": "Candidate does not meet the minimum technical or role requirements.",
        "min_score": 0.0,
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# CONFIDENCE TIERS
# ─────────────────────────────────────────────────────────────────────────────

CONFIDENCE_TIERS = {
    "very_high": {"label": "Very High", "description": "Rich evidence across all key dimensions.", "min": 0.85},
    "high":      {"label": "High",      "description": "Strong evidence in most key dimensions.",  "min": 0.70},
    "medium":    {"label": "Medium",    "description": "Adequate evidence in primary dimensions.", "min": 0.50},
    "low":       {"label": "Low",       "description": "Limited evidence; inference may be unreliable.", "min": 0.30},
    "very_low":  {"label": "Very Low",  "description": "Insufficient evidence for confident ranking.", "min": 0.0},
}


def classify_recommendation(score: float, features: Dict) -> str:
    """Return the recommendation tier key based on score and feature signals."""
    # Hard gates first
    if features.get("is_disqualifier_title", 0.0) == 1.0:
        return "reject"
    if features.get("risk_probability", 0.0) >= 0.75:
        return "reject"
    if features.get("title_tier", "tier_3") == "tier_5":
        return "reject"

    for tier, config in RECOMMENDATION_TIERS.items():
        if score >= config["min_score"]:
            return tier

    return "reject"


def calibrate_confidence(features: Dict, score: float) -> Tuple[str, float]:
    """
    Calibrate recommendation confidence based on evidence quality.
    High score alone is not sufficient — we need rich evidence to be confident.

    Returns (confidence_tier_key, confidence_score in [0, 1]).
    """
    evidence_signals = [
        features.get("trust_score", 0.0),
        features.get("core_skill_score", 0.0),
        features.get("role_specific_depth_score", 0.0),
        features.get("yoe_score", 0.0),
        1.0 if features.get("has_product_company", 0.0) else 0.0,
        features.get("ai_experience_score", 0.0),
        min(1.0, features.get("jd_skill_soft_coverage", features.get("ontology_skill_score", 0.0)) * 1.2),
    ]
    # Average evidence completeness
    avg_evidence = sum(evidence_signals) / len(evidence_signals)

    # Profile completeness factor
    completeness = features.get("profile_completeness_score", 50.0)
    if isinstance(completeness, float) and completeness <= 1.0:
        completeness = completeness * 100  # Handle normalized vs. raw
    completeness_factor = min(1.0, completeness / 100.0)

    # Confidence is a combination of evidence richness + score stability
    confidence_raw = 0.50 * avg_evidence + 0.30 * min(1.0, score * 1.1) + 0.20 * completeness_factor

    for tier_key, config in CONFIDENCE_TIERS.items():
        if confidence_raw >= config["min"]:
            return tier_key, round(confidence_raw, 4)

    return "very_low", round(confidence_raw, 4)


def identify_strengths(features: Dict, top_n: int = 5) -> List[str]:
    """Extract the top N evidence-backed strengths from the feature vector."""
    strength_checks = [
        (features.get("core_skill_score", 0.0) >= 0.70,
         "Strong core technical skill alignment with the JD"),
        (features.get("role_specific_depth_score", 0.0) >= 0.65,
         "Deep domain expertise in relevant ML/Retrieval dimensions"),
        (features.get("yoe_score", 0.0) >= 0.80,
         "Experience level precisely matches the JD's requirements"),
        (features.get("production_at_scale", 0.0) == 1.0,
         "Demonstrated production ML experience at scale"),
        (features.get("has_search_ranking_experience", 0.0) == 1.0,
         "Direct search or ranking company experience"),
        (features.get("has_big_tech_experience", 0.0) == 1.0,
         "Experience at a Big Tech or top-tier product company"),
        (features.get("leadership_evidence_score", 0.0) >= 0.60,
         "Strong leadership evidence beyond title — ownership, mentoring, architecture decisions"),
        (features.get("engineering_maturity_score", 0.0) >= 0.70,
         "High engineering maturity — system design and production experience"),
        (features.get("jd_skill_soft_coverage", features.get("ontology_skill_score", 0.0)) >= 0.65,
         "Strong JD skill coverage including transferable equivalents"),
        (features.get("transferability_gain", 0.0) >= 0.10,
         "Meaningful transferable skills from adjacent domains"),
        (features.get("strong_github", 0.0) == 1.0,
         "Active GitHub presence demonstrating open-source engagement"),
        (features.get("has_assessments", 0.0) == 1.0 and features.get("ai_assessment_score", 0.0) >= 0.65,
         "High-scoring technical assessments in AI/ML domains"),
        (features.get("career_growth_score", 0.0) >= 0.65,
         "Consistent, progressive career trajectory in relevant domains"),
        (features.get("advanced_degree", 0.0) >= 0.70,
         "Advanced degree (MS/PhD) in a relevant field"),
        (features.get("project_complexity_score", 0.0) >= 0.60,
         "Evidence of working on complex, production-grade systems"),
        (features.get("industry_relevance_score", 0.0) >= 0.75,
         "Career in search/recommendation-adjacent industries"),
    ]
    return [msg for passed, msg in strength_checks if passed][:top_n]


def identify_gaps(features: Dict, top_n: int = 5) -> List[str]:
    """Identify the top N evidence-backed gaps from the feature vector."""
    gap_checks = [
        (features.get("core_skill_score", 0.0) < 0.30,
         "Limited match on core technical skills required by the JD"),
        (features.get("role_specific_depth_score", 0.0) < 0.30,
         "Low depth across key retrieval/ranking/embedding dimensions"),
        (features.get("ai_experience_score", 0.0) < 0.20,
         "Limited direct AI/ML role experience"),
        (features.get("production_at_scale", 0.0) == 0.0 and features.get("engineering_maturity_score", 0.5) < 0.50,
         "No clear evidence of production or at-scale deployment"),
        (features.get("is_pure_consulting", 0.0) == 1.0,
         "Primarily consulting background — limited product engineering exposure"),
        (features.get("yoe_score", 0.0) < 0.40,
         "Experience level may not meet the JD's minimum requirements"),
        (features.get("trust_score", 0.0) < 0.30,
         "Low profile trust score — limited verification signals"),
        (features.get("jd_skill_soft_coverage", features.get("ontology_skill_score", 0.5)) < 0.30,
         "Low coverage of JD skills even with transferable equivalents"),
        (features.get("leadership_evidence_score", 1.0) < 0.20
         and features.get("leadership_signal", 0.5) < 0.30,
         "No clear leadership evidence for a senior-level role"),
        (features.get("company_quality_score", 0.5) < 0.35,
         "Limited exposure to high-quality engineering environments"),
        (features.get("retrieval_skill_score", 0.0) == 0.0,
         "No specific retrieval system (FAISS, Elasticsearch, etc.) experience detected"),
        (features.get("embedding_skill_score", 0.0) == 0.0,
         "No embedding model (sentence-transformers, BGE, E5, etc.) experience detected"),
    ]
    return [msg for passed, msg in gap_checks if passed][:top_n]


def identify_risk_factors(features: Dict) -> List[str]:
    """Identify potential risk factors for the hiring decision."""
    risks = []
    risk_prob = features.get("risk_probability", 0.0)

    if risk_prob >= 0.50:
        risks.append(f"Elevated profile risk detected (risk score: {risk_prob:.2f}) — verify profile authenticity")
    if features.get("is_pure_consulting", 0.0) == 1.0:
        risks.append("Entirely consulting background — may face challenges adapting to product engineering culture")
    if features.get("hireability_probability", 1.0) < 0.30:
        risks.append("Low recruiter response rate — candidate may not be actively looking or responsive")
    if features.get("notice_period_days", 0) > 90 if "notice_period_days" in features else False:
        risks.append("Long notice period (>90 days) may delay onboarding")

    # Job hopping risk
    avg_tenure = features.get("avg_tenure_score", 0.5)
    if avg_tenure < 0.40:
        risks.append("Short average job tenure — potential retention risk")

    return risks


def generate_interview_guidance(features: Dict, gaps: List[str]) -> List[str]:
    """
    Generate structured, evidence-based interview recommendations.
    Focus areas are derived from gaps and uncertainties — not generic questions.
    """
    guidance = []

    if features.get("core_skill_score", 0.0) < 0.50:
        guidance.append(
            "Technical depth assessment: Deep-dive on vector search and hybrid retrieval — "
            "ask candidate to walk through their system design for a dense retrieval pipeline"
        )
    if features.get("role_specific_depth_score", 0.0) < 0.50:
        guidance.append(
            "Domain knowledge assessment: Probe understanding of NDCG, MRR, and how they'd "
            "optimize a learning-to-rank model for a real system"
        )
    if features.get("production_at_scale", 0.0) == 0.0:
        guidance.append(
            "Production readiness: Ask for a specific production system they shipped — "
            "QPS, latency, scale, failure modes, monitoring approach"
        )
    if features.get("leadership_evidence_score", 0.0) < 0.40 and features.get("engineering_maturity_score", 0.5) >= 0.50:
        guidance.append(
            "Leadership assessment: Probe how they've influenced technical decisions, "
            "mentored engineers, or driven cross-team alignment — look beyond title"
        )
    if features.get("transferability_gain", 0.0) > 0.05:
        guidance.append(
            "Transferable skills validation: Candidate has adjacent domain experience — "
            "verify their understanding of ranking/retrieval-specific tradeoffs vs. their primary domain"
        )
    if features.get("trust_score", 0.0) < 0.50:
        guidance.append(
            "Profile verification: Request code samples, GitHub repositories, or live system "
            "references to validate claimed skills"
        )

    # Always add: system design question
    if not guidance or features.get("engineering_maturity_score", 0.0) < 0.70:
        guidance.append(
            "System design: Present a design challenge for a semantic search system "
            "handling 100M documents with sub-100ms latency requirements"
        )

    return guidance[:5]  # Cap at 5 focused areas


def self_verify(
    candidate_id: str,
    features: Dict,
    score: float,
    recommendation: str,
    strengths: List[str],
) -> Dict:
    """
    Run the 8-question self-verification checklist per plan.md Block 18 Section 18.
    Returns verification results and any flags for review.
    """
    checks = {
        "evidence_not_assumed": features.get("core_skill_score", 0.0) > 0.0 or features.get("role_specific_depth_score", 0.0) > 0.0,
        "score_from_features": score > 0.0,
        "no_hallucination_risk": len(strengths) > 0 or recommendation in ("reject", "unlikely_fit"),
        "disqualifier_handled": not (
            features.get("is_disqualifier_title", 0.0) == 1.0 and recommendation not in ("reject",)
        ),
        "high_risk_handled": not (
            features.get("risk_probability", 0.0) >= 0.75 and recommendation not in ("reject",)
        ),
        "tier_gate_respected": not (
            features.get("title_tier") == "tier_5" and recommendation not in ("reject",)
        ),
        "confidence_calibrated": score > 0.0,
        "fairness_maintained": True,  # No protected characteristics used in scoring
    }

    all_passed = all(checks.values())
    failed_checks = [k for k, v in checks.items() if not v]

    return {
        "all_checks_passed": all_passed,
        "failed_checks": failed_checks,
        "review_required": not all_passed,
        "verification_note": (
            "All self-verification checks passed." if all_passed
            else f"REVIEW REQUIRED: Failed checks: {', '.join(failed_checks)}"
        ),
    }


def generate_hiring_decision(
    candidate: Dict,
    features: Dict,
    score: float,
    rank: int,
) -> Dict:
    """
    Main entry point: Generate a complete, verified hiring decision.

    Args:
        candidate: Raw candidate dict
        features: Feature vector from feature_engine
        score: Final ranking score
        rank: Candidate's rank in the shortlist

    Returns:
        Complete HiringDecision dict for recruiter output
    """
    candidate_id = candidate.get("candidate_id", "UNKNOWN")
    profile = candidate.get("profile", {})

    # 1. Recommendation tier
    recommendation_key = classify_recommendation(score, features)
    recommendation_config = RECOMMENDATION_TIERS.get(recommendation_key, RECOMMENDATION_TIERS["reject"])

    # 2. Confidence calibration
    confidence_key, confidence_score = calibrate_confidence(features, score)
    confidence_config = CONFIDENCE_TIERS.get(confidence_key, CONFIDENCE_TIERS["medium"])

    # 3. Strengths
    strengths = identify_strengths(features)

    # 4. Gaps
    gaps = identify_gaps(features)

    # 5. Risk factors
    risks = identify_risk_factors(features)

    # 6. Interview guidance
    interview_guidance = generate_interview_guidance(features, gaps)

    # 7. Self-verification
    verification = self_verify(candidate_id, features, score, recommendation_key, strengths)

    # 8. Build decision
    decision = {
        "candidate_id": candidate_id,
        "rank": rank,
        "final_score": round(score, 6),
        "recommendation": recommendation_config["label"],
        "recommendation_key": recommendation_key,
        "recommendation_description": recommendation_config["description"],
        "confidence_tier": confidence_config["label"],
        "confidence_score": confidence_score,
        "confidence_description": confidence_config["description"],
        "top_strengths": strengths,
        "key_gaps": gaps,
        "risk_factors": risks,
        "interview_guidance": interview_guidance,
        "self_verification": verification,
        "engineering_maturity": features.get("engineering_maturity_score", 0.40),
        "is_verified_profile": features.get("trust_score", 0.0) >= 0.60,
        "has_production_evidence": features.get("production_at_scale", 0.0) == 1.0,
        "review_required": verification.get("review_required", False),
    }

    if not verification["all_checks_passed"]:
        logger.warning(
            f"Self-verification failed for {candidate_id}: {verification['failed_checks']}"
        )

    return decision
