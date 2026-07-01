"""
explanation_engine.py — Auto-generate recruiter-friendly reasoning strings
Produces 1-2 sentence justifications for each ranked candidate.
"""
import logging
from typing import Dict, List

from redrob_ranker.config import (
    DISQUALIFIER_TITLES,
    PREFERRED_CITIES,
    REQUIRED_SKILLS,
    SKILL_NORMALIZE,
)

logger = logging.getLogger(__name__)


def _normalize_skill_name(name: str) -> str:
    n = name.lower().strip()
    return SKILL_NORMALIZE.get(n, n)


def _get_top_ai_skills(skills: list, max_n: int = 3) -> List[str]:
    """Get the most relevant AI skills for the JD."""
    matched = []
    for skill in skills:
        norm = _normalize_skill_name(skill["name"])
        if norm in REQUIRED_SKILLS:
            proficiency = skill.get("proficiency", "beginner")
            endorsements = skill.get("endorsements", 0)
            matched.append((skill["name"], proficiency, endorsements))

    # Sort by proficiency then endorsements
    prof_order = {"expert": 4, "advanced": 3, "intermediate": 2, "beginner": 1}
    matched.sort(key=lambda x: (prof_order.get(x[1], 0), x[2]), reverse=True)
    return [m[0] for m in matched[:max_n]]


def _get_company_type(career_history: list) -> str:
    """Describe the candidate's company background."""
    from redrob_ranker.config import CONSULTING_COMPANIES
    
    companies = []
    has_product = False
    has_consulting = False
    
    for job in career_history[:3]:
        company = job.get("company", "")
        company_lower = company.lower()
        if any(cc in company_lower for cc in CONSULTING_COMPANIES):
            has_consulting = True
        else:
            has_product = True
            companies.append(company)
    
    if has_product and not has_consulting:
        return "product company"
    elif has_product and has_consulting:
        return "mixed product/services background"
    else:
        return "services background"


def generate_reasoning(
    candidate: dict,
    features: Dict[str, float],
    final_score: float,
    rank: int,
) -> str:
    """
    Generate a 1-2 sentence recruiter-facing reasoning string.
    Must:
    - Prepend decision engine recommendation and confidence level
    - Reference specific facts from the profile
    - Connect to JD requirements
    - Acknowledge concerns where relevant
    - Not hallucinate information
    """
    from redrob_ranker.engines.decision_engine import generate_hiring_decision

    profile = candidate.get("profile", {})
    skills = candidate.get("skills", [])
    career_history = candidate.get("career_history", [])
    signals = candidate.get("redrob_signals", {})
    education = candidate.get("education", [])

    title = profile.get("current_title", "Unknown Role")
    yoe = profile.get("years_of_experience", 0)
    country = profile.get("country", "")
    location = profile.get("location", "")
    
    # Open-to-work status
    open_to_work = signals.get("open_to_work_flag", False)
    notice_days = signals.get("notice_period_days", 90)
    response_rate = signals.get("recruiter_response_rate", 0)
    last_active = signals.get("last_active_date", "")
    github = signals.get("github_activity_score", -1)
    
    parts = []
    concerns = []

    # Get decision tier and confidence
    try:
        decision = generate_hiring_decision(candidate, features, final_score, rank)
        rec = decision.get("recommendation", "Review")
        conf = decision.get("confidence_tier", "Medium")
        prefix = f"[{rec} / {conf} Confidence] "
    except Exception:
        prefix = ""

    # ── Core sentence: title + experience ────────────────────────────────
    title_str = f"{title}"
    yoe_str = f"{yoe:.1f} yrs"
    
    # Location detail
    loc_str = ""
    loc_lower = location.lower()
    for city in PREFERRED_CITIES:
        if city in loc_lower:
            loc_str = f", {location.strip()}-based"
            break
    if not loc_str and country:
        loc_str = f", {country}"

    # ── AI/retrieval skills ───────────────────────────────────────────────
    top_skills = _get_top_ai_skills(skills, max_n=3)
    skill_str = ""
    if top_skills:
        skill_str = f"; core skills: {', '.join(top_skills)}"
    elif features.get("core_skill_count", 0) == 0:
        skill_str = "; no direct AI/retrieval skills in profile"

    # ── Assessment scores ─────────────────────────────────────────────────
    assessments = signals.get("skill_assessment_scores", {})
    assessment_str = ""
    if assessments:
        avg_score = sum(assessments.values()) / len(assessments)
        assessment_str = f"; platform assessments avg {avg_score:.0f}/100"

    # ── Company type ──────────────────────────────────────────────────────
    company_type = _get_company_type(career_history)
    company_str = f"; {company_type}"

    # ── GitHub ────────────────────────────────────────────────────────────
    github_str = ""
    if github >= 60:
        github_str = f"; GitHub score {github:.0f}/100"
    elif github < 0:
        github_str = "; no GitHub linked"

    # Build primary sentence
    primary = f"{prefix}{title_str} with {yoe_str} exp{loc_str}{company_str}{skill_str}{assessment_str}{github_str}."

    parts.append(primary)

    # ── Second sentence: behavioral/availability signals ─────────────────
    behavior_parts = []

    if open_to_work:
        behavior_parts.append("actively open to work")

    if response_rate >= 0.60:
        behavior_parts.append(f"high recruiter response rate ({response_rate:.0%})")
    elif response_rate < 0.15 and rank <= 50:
        concerns.append(f"low response rate ({response_rate:.0%})")

    if notice_days <= 30:
        behavior_parts.append(f"notice ≤{notice_days}d")
    elif notice_days > 90 and rank <= 50:
        concerns.append(f"long notice period ({notice_days}d)")

    # Concerns
    is_disqualifier = features.get("is_disqualifier_title", 0) > 0.5
    if is_disqualifier:
        concerns.append(f"title '{title}' does not match ML/AI role requirements")

    honeypot = features.get("honeypot_probability", 0)
    if honeypot >= 0.5:
        concerns.append(f"profile consistency concern (score {honeypot:.2f})")

    pure_consulting = features.get("is_pure_consulting", 0) > 0.5
    if pure_consulting and rank <= 30:
        concerns.append("entire career at IT services companies")

    # Build second sentence
    second_parts = []
    if behavior_parts:
        second_parts.append(", ".join(behavior_parts))
    if concerns:
        concern_str = "concern: " + "; ".join(concerns)
        second_parts.append(concern_str)

    if second_parts:
        parts.append(" | ".join(second_parts) + ".")

    # Clamp to reasonable length
    result = " ".join(parts)
    if len(result) > 400:
        result = result[:397] + "..."

    return result


# ─────────────────────────────────────────────────────────────
# MODULE 12 — Counterfactual Explanation Engine
# ─────────────────────────────────────────────────────────────

# Features to compare for counterfactual analysis
COUNTERFACTUAL_FEATURES = [
    ("core_skill_score",       "retrieval/AI skill depth",    True),
    ("ai_experience_score",    "AI role experience",          True),
    ("yoe_score",              "years of experience fit",     True),
    ("ai_assessment_score",    "platform assessment scores",  True),
    ("availability_score",     "availability",                True),
    ("recruiter_response_rate","recruiter response rate",     True),
    ("notice_score",           "notice period",               True),
    ("github_score",           "GitHub activity",             True),
    ("hireability_score",      "hireability",                 True),
    ("career_growth_score",    "career growth",               True),
    ("product_company_score",  "product company experience",  True),
    ("education_score",        "education tier",              True),
]


def generate_counterfactual_explanation(
    rank: int,
    features: Dict[str, float],
    top_features: Dict[str, float],
    signals: dict = None,
) -> str:
    """
    Module 12: Generate delta-based counterfactual reasoning.
    Explains why this candidate is ranked at `rank` instead of #1.
    
    Example output:
    "Ranked #4 vs #1: retrieval skill depth lower by 23%; 
     AI role experience lower by 18%; response rate lower by 35%."
    """
    if rank == 1:
        return "Top-ranked candidate."

    gaps = []
    signals = signals or {}

    for feat_key, feat_label, higher_is_better in COUNTERFACTUAL_FEATURES:
        # Check signals dict for raw values
        raw_key_map = {
            "recruiter_response_rate": "recruiter_response_rate",
        }
        if feat_key in raw_key_map and signals:
            this_val = signals.get(raw_key_map[feat_key], features.get(feat_key, 0))
            top_val = top_features.get(feat_key, this_val)
        else:
            this_val = features.get(feat_key, 0)
            top_val = top_features.get(feat_key, this_val)

        delta = top_val - this_val
        if higher_is_better and delta > 0.08:  # Meaningful gap
            pct = int(delta * 100)
            gaps.append(f"{feat_label} lower by {pct}%")
        elif not higher_is_better and delta < -0.08:
            pct = int(abs(delta) * 100)
            gaps.append(f"{feat_label} higher by {pct}% (unfavorable)")

    if not gaps:
        return f"Ranked #{rank}: competitive profile, marginally below top candidate on combined score."

    top_gaps = gaps[:3]  # Show at most 3 deltas
    gap_str = "; ".join(top_gaps)
    return f"Ranked #{rank} vs #1: {gap_str}."
