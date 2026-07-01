"""
gap_analysis_engine.py — Module 16: Candidate Gap Analysis Engine
For every candidate generates:
  - Match Score (per JD dimension)
  - Strengths (what they excel at)
  - Missing Skills (gap vs. JD requirements)
  - Behavioral Risks (signals that could derail hiring)
  - Experience Gaps (domain/company type gaps)
  - Ranking Explanation (why this rank)
Uses Qwen 2.5 3B for narrative generation, rule-based for gap detection.
"""
import logging
import re
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Default JD context (Redrob ML Engineer)
DEFAULT_JD = {
    "required_skills": {
        "faiss", "elasticsearch", "sentence-transformers", "embeddings",
        "learning to rank", "pytorch", "python", "nlp", "rag",
        "vector search", "transformers", "information retrieval",
    },
    "nice_to_have": {
        "milvus", "pinecone", "weaviate", "lightgbm", "bm25",
        "huggingface", "fine-tuning", "lora",
    },
    "yoe_min": 5,
    "yoe_max": 9,
    "product_company_preferred": True,
    "location": "India",
}

# ─────────────────────────────────────────────────────────────
# GAP DETECTION — Rule-based (fast, no LLM)
# ─────────────────────────────────────────────────────────────

def _normalize_skill(name: str) -> str:
    return name.lower().strip()


def detect_skill_gaps(
    candidate_skills: List[Dict],
    required_skills: set,
    nice_to_have: set,
) -> Dict:
    """
    Returns: {
      "matched_required": [...],
      "missing_required": [...],
      "matched_preferred": [...],
      "missing_preferred": [...],
      "coverage_pct": 0-100
    }
    """
    candidate_norm = {_normalize_skill(s["name"]) for s in candidate_skills}

    matched_req = list(required_skills & candidate_norm)
    missing_req = list(required_skills - candidate_norm)
    matched_pref = list(nice_to_have & candidate_norm)
    missing_pref = list(nice_to_have - candidate_norm)

    coverage = len(matched_req) / max(1, len(required_skills)) * 100

    return {
        "matched_required": sorted(matched_req),
        "missing_required": sorted(missing_req),
        "matched_preferred": sorted(matched_pref),
        "missing_preferred": sorted(missing_pref),
        "coverage_pct": round(coverage, 1),
    }


def detect_experience_gaps(
    candidate: Dict,
    jd: Dict,
) -> List[str]:
    """Return list of experience gap descriptions."""
    gaps = []
    profile = candidate.get("profile", {})
    career = candidate.get("career_history", [])

    yoe = profile.get("years_of_experience", 0)
    yoe_min = jd.get("yoe_min", 5)
    yoe_max = jd.get("yoe_max", 9)

    if yoe < yoe_min:
        gaps.append(f"Experience ({yoe:.1f}yr) below minimum requirement ({yoe_min}yr)")
    elif yoe > yoe_max + 3:
        gaps.append(f"May be overqualified ({yoe:.1f}yr vs {yoe_max}yr max)")

    # Product company check
    from redrob_ranker.config import CONSULTING_COMPANIES
    is_consulting_only = all(
        any(cc in j.get("company", "").lower() for cc in CONSULTING_COMPANIES)
        for j in career
    )
    if is_consulting_only and jd.get("product_company_preferred"):
        gaps.append("Entire career at IT services/consulting companies — product company experience preferred")

    # AI role experience
    ai_keywords = ["ml", "machine learning", "ai", "nlp", "search", "ranking", "recommendation", "retrieval"]
    ai_months = sum(
        j.get("duration_months", 0)
        for j in career
        if any(kw in j.get("title", "").lower() for kw in ai_keywords)
    )
    if ai_months < 24:
        gaps.append(f"Limited direct AI/ML role experience ({ai_months} months)")

    # Location
    country = profile.get("country", "")
    if country and country != jd.get("location", "India") and country != "India":
        gaps.append(f"Location mismatch: {country} (role based in {jd.get('location', 'India')})")

    return gaps


def detect_behavioral_risks(candidate: Dict) -> List[str]:
    """Return list of behavioral risk descriptions."""
    risks = []
    signals = candidate.get("redrob_signals", {})

    # Response rate
    rr = signals.get("recruiter_response_rate", 0.5)
    if rr < 0.20:
        risks.append(f"Very low recruiter response rate ({rr:.0%}) — unlikely to respond")

    # Long notice
    notice = signals.get("notice_period_days", 90)
    if notice > 90:
        risks.append(f"Long notice period ({notice} days) — slow to join")

    # Stale profile
    last_active = signals.get("last_active_date", "")
    if last_active and last_active < "2026-01-01":
        risks.append("Profile inactive for 6+ months")

    # Not open to work
    if not signals.get("open_to_work_flag", False):
        risks.append("Not actively open to work")

    # Low interview completion
    icr = signals.get("interview_completion_rate", 1.0)
    if icr < 0.40:
        risks.append(f"Low interview completion rate ({icr:.0%}) — may ghost during process")

    # Offer rejection history
    oar = signals.get("offer_acceptance_rate", -1)
    if 0 <= oar < 0.30:
        risks.append(f"Low offer acceptance rate ({oar:.0%}) — may decline after selection")

    # High salary expectations
    salary = signals.get("expected_salary_range_inr_lpa", {})
    sal_min = salary.get("min", 0)
    if sal_min > 80:
        risks.append(f"Salary expectations ({sal_min}+ LPA) may be above typical range")

    return risks


def identify_strengths(
    candidate: Dict,
    features: Dict,
    skill_gaps: Dict,
) -> List[str]:
    """Return list of candidate strengths relative to JD."""
    strengths = []
    signals = candidate.get("redrob_signals", {})
    profile = candidate.get("profile", {})

    # Skill strengths
    matched = skill_gaps.get("matched_required", [])
    if matched:
        strengths.append(f"Matched {len(matched)} required skills: {', '.join(matched[:5])}")

    # Assessment
    assessments = signals.get("skill_assessment_scores", {})
    if assessments:
        avg = sum(assessments.values()) / len(assessments)
        if avg >= 70:
            strengths.append(f"Strong platform assessments: avg {avg:.0f}/100 ({len(assessments)} tests)")

    # Availability
    if signals.get("open_to_work_flag"):
        notice = signals.get("notice_period_days", 90)
        strengths.append(f"Actively looking — notice period: {notice} days")

    # Career growth
    cg = features.get("career_growth_score", 0)
    if cg >= 0.70:
        strengths.append(f"Strong career trajectory (growth score: {cg:.0%})")

    # GitHub
    gh = signals.get("github_activity_score", -1)
    if gh >= 60:
        strengths.append(f"Active open-source contributor (GitHub score: {gh}/100)")

    # Product company
    if features.get("has_product_company", 0) > 0:
        strengths.append("Product company experience — understands scale and production systems")

    # Education
    edu = candidate.get("education", [])
    if edu:
        top_edu = edu[0]
        if top_edu.get("tier") in ("tier_1", "iit", "iim", "top_global"):
            strengths.append(f"Top-tier education: {top_edu.get('institution', '')}")

    # Response rate
    rr = signals.get("recruiter_response_rate", 0)
    if rr >= 0.70:
        strengths.append(f"Highly responsive to recruiters ({rr:.0%} response rate)")

    return strengths[:6]  # Top 6 strengths


# ─────────────────────────────────────────────────────────────
# LLM NARRATIVE — Qwen 2.5 3B
# ─────────────────────────────────────────────────────────────

def generate_gap_narrative_llm(
    candidate: Dict,
    strengths: List[str],
    missing_skills: List[str],
    experience_gaps: List[str],
    behavioral_risks: List[str],
    rank: int,
    score: float,
) -> str:
    """Use Qwen to generate a fluent recruiter-facing gap analysis paragraph."""
    try:
        from redrob_ranker.engines.resume_ingestion_engine import _qwen_extract

        profile = candidate.get("profile", {})
        prompt = f"""Write a concise 3-4 sentence recruiter summary for this candidate ranked #{rank} (score {score:.1%}).

Candidate: {profile.get('current_title', '')} | {profile.get('years_of_experience', 0):.0f}yr exp | {profile.get('country', '')}

Strengths: {', '.join(strengths[:3]) if strengths else 'None'}
Missing Skills: {', '.join(missing_skills[:3]) if missing_skills else 'None'}
Experience Gaps: {', '.join(experience_gaps[:2]) if experience_gaps else 'None'}
Behavioral Risks: {', '.join(behavioral_risks[:2]) if behavioral_risks else 'None'}

Write a professional, factual 3-4 sentence analysis. No bullet points. Start with the candidate's strongest qualification."""

        result = _qwen_extract("", prompt, max_new_tokens=200)
        return result.strip() if result else ""
    except Exception as e:
        logger.warning(f"LLM narrative failed: {e}")
        return ""


# ─────────────────────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────────

def analyze_candidate_gap(
    candidate: Dict,
    features: Dict,
    rank: int,
    score: float,
    jd: Optional[Dict] = None,
    use_llm: bool = False,
) -> Dict:
    """
    Module 16: Full gap analysis for a single candidate.
    Returns comprehensive gap analysis dict.
    """
    if jd is None:
        try:
            from redrob_ranker.config import REQUIRED_SKILLS, PREFERRED_SKILLS, JD_EXPERIENCE_RANGE
            min_yoe, max_yoe = JD_EXPERIENCE_RANGE
            jd = {
                "required_skills": REQUIRED_SKILLS,
                "nice_to_have": PREFERRED_SKILLS,
                "yoe_min": min_yoe,
                "yoe_max": max_yoe,
                "product_company_preferred": True,
                "location": "India",
            }
        except Exception:
            jd = DEFAULT_JD
    skills = candidate.get("skills", [])

    # 1. Skill gaps
    skill_gaps = detect_skill_gaps(
        skills,
        set(jd.get("required_skills", DEFAULT_JD["required_skills"])),
        set(jd.get("nice_to_have", DEFAULT_JD["nice_to_have"])),
    )

    # 2. Experience gaps
    exp_gaps = detect_experience_gaps(candidate, jd)

    # 3. Behavioral risks
    behavioral_risks = detect_behavioral_risks(candidate)

    # 4. Strengths
    strengths = identify_strengths(candidate, features, skill_gaps)

    # 5. LLM narrative (optional)
    narrative = ""
    if use_llm:
        narrative = generate_gap_narrative_llm(
            candidate, strengths,
            skill_gaps["missing_required"],
            exp_gaps, behavioral_risks, rank, score,
        )

    # 6. Composite match scores per dimension
    skill_match = skill_gaps["coverage_pct"] / 100.0
    exp_match = features.get("yoe_score", 0)
    product_match = features.get("product_company_score", 0)
    behavioral_match = features.get("availability_score", 0)
    education_match = features.get("education_score", 0)

    return {
        "candidate_id": candidate.get("candidate_id", ""),
        "rank": rank,
        "final_score": round(score, 4),
        "dimension_scores": {
            "skill_match": round(skill_match, 3),
            "experience_match": round(exp_match, 3),
            "product_company_match": round(product_match, 3),
            "behavioral_match": round(behavioral_match, 3),
            "education_match": round(education_match, 3),
        },
        "strengths": strengths,
        "missing_required_skills": skill_gaps["missing_required"],
        "missing_preferred_skills": skill_gaps["missing_preferred"],
        "matched_skills": skill_gaps["matched_required"],
        "experience_gaps": exp_gaps,
        "behavioral_risks": behavioral_risks,
        "skill_coverage_pct": skill_gaps["coverage_pct"],
        "llm_narrative": narrative,
        "overall_assessment": (
            "Strong Fit" if score >= 0.85
            else "Good Fit" if score >= 0.70
            else "Partial Fit" if score >= 0.55
            else "Weak Fit"
        ),
    }


def analyze_all_candidates(
    ranked: list,
    jd: Optional[Dict] = None,
    use_llm: bool = False,
) -> List[Dict]:
    """Run gap analysis across all top-N ranked candidates."""
    results = []
    for idx, (candidate, features, score) in enumerate(ranked):
        try:
            gap = analyze_candidate_gap(
                candidate, features, idx + 1, score, jd=jd, use_llm=use_llm
            )
            results.append(gap)
        except Exception as e:
            logger.error(f"Gap analysis failed for {candidate.get('candidate_id', '?')}: {e}")
    return results
