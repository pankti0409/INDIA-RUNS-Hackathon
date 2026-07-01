"""
resume_quality_engine.py — Module 17: Resume Quality Engine
Generates:
  - Resume Quality Score (0-100)
  - Profile Completeness analysis
  - Missing Sections detection
  - Weak Areas identification
  - Improvement Suggestions
Uses Qwen 2.5 3B for intelligent suggestions, rule-based for detection.
"""
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# COMPLETENESS CHECKS
# ─────────────────────────────────────────────────────────────

REQUIRED_SECTIONS = {
    "current_title": ("Profile — Current Title", 8),
    "summary": ("Profile — Professional Summary", 10),
    "skills": ("Skills Section", 15),
    "career_history": ("Work Experience", 20),
    "education": ("Education", 10),
    "location": ("Location", 5),
}

OPTIONAL_SECTIONS = {
    "certifications": ("Certifications", 5),
    "github_url": ("GitHub Profile", 8),
    "linkedin_url": ("LinkedIn Profile", 5),
    "languages": ("Languages", 4),
    "phone": ("Phone Number", 5),
    "email": ("Email Address", 5),
}


def check_completeness(candidate: Dict) -> Tuple[float, List[str], List[str]]:
    """
    Returns (completeness_score 0-100, present_sections, missing_sections).
    """
    profile = candidate.get("profile", {})
    signals = candidate.get("redrob_signals", {})
    present = []
    missing = []
    score = 0

    # Required sections
    for field, (label, weight) in REQUIRED_SECTIONS.items():
        val = None
        if field == "skills":
            val = candidate.get("skills", [])
        elif field == "career_history":
            val = candidate.get("career_history", [])
        elif field == "education":
            val = candidate.get("education", [])
        elif field == "summary":
            val = profile.get("summary", "")
        elif field == "current_title":
            val = profile.get("current_title", "")
        elif field == "location":
            val = profile.get("location", "") or profile.get("country", "")

        if val and (not isinstance(val, (list, str)) or len(val) > 0):
            present.append(label)
            score += weight
        else:
            missing.append(f"❌ {label} (required)")

    # Optional sections
    for field, (label, weight) in OPTIONAL_SECTIONS.items():
        val = None
        if field in ("certifications", "languages"):
            val = candidate.get(field, [])
        elif field in ("github_url", "linkedin_url", "email", "phone"):
            val = profile.get(field, "")
        
        if val and (not isinstance(val, (list, str)) or len(val) > 0):
            present.append(label)
            score += weight
        else:
            missing.append(f"○ {label} (optional)")

    return round(min(100, score), 1), present, missing


# ─────────────────────────────────────────────────────────────
# WEAK AREA DETECTION
# ─────────────────────────────────────────────────────────────

def detect_weak_areas(candidate: Dict) -> List[str]:
    """Identify specific weaknesses in the profile."""
    weak = []
    profile = candidate.get("profile", {})
    skills = candidate.get("skills", [])
    career = candidate.get("career_history", [])
    signals = candidate.get("redrob_signals", {})

    # Summary quality
    summary = profile.get("summary", "")
    if len(summary) < 50:
        weak.append("Summary is too short or missing — add 2-3 sentences of professional narrative")
    elif len(summary) < 150:
        weak.append("Summary could be stronger — mention specific technologies and impact")

    # Skill proficiency declarations
    beginner_skills = [s for s in skills if s.get("proficiency", "").lower() == "beginner"]
    if len(beginner_skills) > len(skills) * 0.5:
        weak.append(f"{len(beginner_skills)}/{len(skills)} skills listed at 'Beginner' level — update proficiency levels")

    # Skills with no duration
    no_duration = sum(1 for s in skills if s.get("duration_months", 0) == 0)
    if no_duration > len(skills) * 0.4:
        weak.append(f"{no_duration} skills missing duration — add years of practice to strengthen credibility")

    # Endorsements
    total_endorsed = sum(1 for s in skills if s.get("endorsements", 0) > 0)
    if total_endorsed == 0 and len(skills) > 0:
        weak.append("No skill endorsements — request endorsements from colleagues to build social proof")

    # Job descriptions
    empty_desc = sum(1 for j in career if not j.get("description", "").strip())
    if empty_desc > 0:
        weak.append(f"{empty_desc} work experiences have no description — add bullet points with achievements and impact")

    # Short tenures (job hopping)
    short_jobs = [j for j in career if 0 < j.get("duration_months", 0) < 12]
    if len(short_jobs) >= 2:
        weak.append(f"{len(short_jobs)} jobs under 12 months — consider adding context for short stints")

    # Profile completeness
    completeness = signals.get("profile_completeness_score", 0)
    if completeness < 70:
        weak.append(f"Platform completeness score is {completeness}/100 — fill in missing profile sections")

    # No assessments
    if not signals.get("skill_assessment_scores"):
        weak.append("No platform assessment scores — take Redrob skill assessments to validate expertise")

    # No GitHub
    if signals.get("github_activity_score", -1) < 0:
        weak.append("GitHub profile not linked — connect GitHub to showcase open-source contributions")

    return weak[:8]


# ─────────────────────────────────────────────────────────────
# IMPROVEMENT SUGGESTIONS
# ─────────────────────────────────────────────────────────────

def generate_improvement_suggestions(
    candidate: Dict,
    missing_sections: List[str],
    weak_areas: List[str],
    jd_required_skills: set = None,
) -> List[str]:
    """Generate prioritized, actionable improvement suggestions."""
    suggestions = []
    profile = candidate.get("profile", {})
    skills = candidate.get("skills", [])
    signals = candidate.get("redrob_signals", {})

    # Priority 1: Missing required sections
    for ms in missing_sections[:3]:
        if "❌" in ms:
            suggestions.append(f"🔴 HIGH: Add {ms.replace('❌ ', '').replace(' (required)', '')}")

    # Priority 2: Missing JD skills
    if jd_required_skills:
        candidate_skills_norm = {s["name"].lower().strip() for s in skills}
        missing_critical = jd_required_skills - candidate_skills_norm
        if missing_critical:
            top_missing = sorted(missing_critical)[:3]
            suggestions.append(f"🟠 HIGH: Learn/add skills critical for target role: {', '.join(top_missing)}")

    # Priority 3: Platform actions
    if not signals.get("skill_assessment_scores"):
        suggestions.append("🟡 MEDIUM: Take Redrob skill assessments — validated skills significantly improve ranking")

    if signals.get("github_activity_score", -1) < 0:
        suggestions.append("🟡 MEDIUM: Link GitHub profile — open-source work is a strong signal for ML roles")

    if not signals.get("open_to_work_flag"):
        suggestions.append("🟡 MEDIUM: Set 'Open to Work' status — candidates actively looking get 40% more visibility")

    # Priority 4: Profile polish
    summary = profile.get("summary", "")
    if len(summary) < 100:
        suggestions.append("🟢 LOW: Expand professional summary — mention specific systems you've built and scale achieved")

    if not signals.get("linkedin_connected"):
        suggestions.append("🟢 LOW: Connect LinkedIn profile for additional trust verification")

    # Priority 5: Behavioral signals
    rr = signals.get("recruiter_response_rate", 0.5)
    if rr < 0.40:
        suggestions.append(f"🟢 LOW: Respond faster to recruiter messages — current response rate ({rr:.0%}) is below average")

    return suggestions[:8]


# ─────────────────────────────────────────────────────────────
# LLM ENHANCEMENT — Qwen 2.5 3B
# ─────────────────────────────────────────────────────────────

def generate_quality_narrative_llm(
    candidate: Dict,
    quality_score: float,
    weak_areas: List[str],
    suggestions: List[str],
) -> str:
    """Use Qwen to generate a fluent quality assessment narrative."""
    try:
        from redrob_ranker.engines.resume_ingestion_engine import _qwen_extract
        profile = candidate.get("profile", {})

        prompt = f"""Write a 3-sentence resume quality assessment for a {profile.get('current_title', 'professional')}.

Quality Score: {quality_score:.0f}/100
Top Weak Areas: {'; '.join(weak_areas[:3]) if weak_areas else 'None identified'}
Top Suggestions: {'; '.join(s.split(': ', 1)[-1] for s in suggestions[:3]) if suggestions else 'Profile is strong'}

Write a professional, encouraging 3-sentence assessment. Be specific about what to improve. Start with what's working well."""

        result = _qwen_extract("", prompt, max_new_tokens=150)
        return result.strip() if result else ""
    except Exception as e:
        logger.warning(f"LLM quality narrative failed: {e}")
        return ""


# ─────────────────────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────────

def analyze_resume_quality(
    candidate: Dict,
    jd_required_skills: Optional[set] = None,
    use_llm: bool = False,
) -> Dict:
    """
    Module 17: Full resume quality analysis for a single candidate.
    Returns comprehensive quality assessment dict.
    """
    # 1. Completeness check
    completeness_score, present_sections, missing_sections = check_completeness(candidate)

    # 2. Weak area detection
    weak_areas = detect_weak_areas(candidate)

    # 3. Improvement suggestions
    suggestions = generate_improvement_suggestions(
        candidate, missing_sections, weak_areas, jd_required_skills
    )

    # 4. Overall quality score (weighted)
    signals = candidate.get("redrob_signals", {})
    platform_completeness = signals.get("profile_completeness_score", 0)

    # Blend: schema completeness (40%) + platform completeness (30%) + weak area penalty (30%)
    weak_penalty = len(weak_areas) * 5  # Each weak area costs 5 points
    quality_score = (
        0.40 * completeness_score
        + 0.30 * platform_completeness
        + 0.30 * max(0, 100 - weak_penalty)
    )
    quality_score = round(min(100, max(0, quality_score)), 1)

    # 5. LLM narrative
    narrative = ""
    if use_llm:
        narrative = generate_quality_narrative_llm(
            candidate, quality_score, weak_areas, suggestions
        )

    return {
        "candidate_id": candidate.get("candidate_id", ""),
        "quality_score": quality_score,
        "completeness_score": completeness_score,
        "platform_completeness": platform_completeness,
        "quality_grade": (
            "Excellent" if quality_score >= 85
            else "Good" if quality_score >= 70
            else "Fair" if quality_score >= 55
            else "Needs Work"
        ),
        "present_sections": present_sections,
        "missing_sections": missing_sections,
        "weak_areas": weak_areas,
        "improvement_suggestions": suggestions,
        "llm_narrative": narrative,
        "section_count": len(present_sections),
        "has_github": signals.get("github_activity_score", -1) >= 0,
        "has_assessments": bool(signals.get("skill_assessment_scores")),
        "is_open_to_work": signals.get("open_to_work_flag", False),
    }
