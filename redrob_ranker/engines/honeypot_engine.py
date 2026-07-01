"""
honeypot_engine.py — Module 8 & Priority 6: Risk Engine
Calculates continuous risk_probability using a noisy-OR blend of timeline,
skill, assessment, and behavioral anomalies. Avoids step functions and hard thresholds.
"""
import logging
import math
from datetime import datetime
from typing import Dict, Tuple

from redrob_ranker.config import (
    DISQUALIFIER_TITLES,
    PROFICIENCY_SCORES,
    REQUIRED_SKILLS,
)

logger = logging.getLogger(__name__)

REFERENCE_DATE = datetime(2026, 6, 22)


def detect_honeypot(candidate: dict) -> Tuple[float, str]:
    """
    Computes a continuous risk_probability [0, 1] for a candidate profile.
    Integrates multiple risk dimensions using smooth probability curves.
    """
    profile = candidate.get("profile", {})
    skills = candidate.get("skills", [])
    career_history = candidate.get("career_history", [])
    redrob = candidate.get("redrob_signals", {})
    education = candidate.get("education", [])

    title = profile.get("current_title", "").lower().strip()
    reasons = []
    
    # ── 1. Title-Skills Mismatch Risk ──────────────────────────────────────
    # Disqualifier title + stuffer skill profile
    is_disqualifier = any(dt in title for dt in DISQUALIFIER_TITLES)
    if is_disqualifier:
        skill_names_lower = {s["name"].lower() for s in skills}
        ai_matches = len(skill_names_lower & REQUIRED_SKILLS)
        # Smoothly scales with match count; reaches 0.86 at 5 matches
        r_title_skill = 1.0 - math.exp(-0.4 * ai_matches)
        if r_title_skill > 0.1:
            reasons.append(f"disqualifier-title with {ai_matches} AI skills (p={r_title_skill:.2f})")
    else:
        r_title_skill = 0.0

    # ── 2. Expert Skills with Zero Duration Risk ────────────────────────────
    expert_zero_months = sum(
        1 for s in skills 
        if s.get("proficiency", "").lower() in ("expert", "advanced") and s.get("duration_months", -1) == 0
    )
    # Smooth decay/growth based on count
    r_expert_zero = 1.0 - math.exp(-0.25 * expert_zero_months)
    if r_expert_zero > 0.1:
        reasons.append(f"{expert_zero_months} advanced skills with 0mo duration (p={r_expert_zero:.2f})")

    # ── 3. Assessment vs Claim Contradiction Risk ───────────────────────────
    assessment_scores = redrob.get("skill_assessment_scores", {})
    skill_proficiency_map = {s["name"].lower(): s.get("proficiency", "beginner") for s in skills}
    contradictions = 0
    for skill_name, score in assessment_scores.items():
        claimed = skill_proficiency_map.get(skill_name.lower(), "beginner")
        claimed_val = PROFICIENCY_SCORES.get(claimed, 0.2) * 100.0
        # If claimed expert/advanced (>= 80) but scored poorly (< 40)
        if claimed_val >= 80.0 and score < 40.0:
            contradictions += 1
            
    r_assessment = 1.0 - math.exp(-0.4 * contradictions)
    if r_assessment > 0.1:
        reasons.append(f"{contradictions} assessment contradictions (p={r_assessment:.2f})")

    # ── 4. Impossible Career Timeline Risk ─────────────────────────────────
    total_timeline_gap = 0.0
    for job in career_history:
        start_str = job.get("start_date", "")
        end_str = job.get("end_date")
        stated_duration = job.get("duration_months", 0)

        if start_str:
            try:
                start_dt = datetime.strptime(start_str, "%Y-%m-%d")
                end_dt = datetime.strptime(end_str, "%Y-%m-%d") if end_str else REFERENCE_DATE
                actual_months = (end_dt.year - start_dt.year) * 12 + (end_dt.month - start_dt.month)
                
                is_current = job.get("is_current", False) or not end_str
                if is_current and stated_duration <= actual_months:
                    gap = 0.0
                else:
                    gap = abs(actual_months - stated_duration)
                total_timeline_gap += gap
            except (ValueError, TypeError):
                pass
                
    # If gap is small (under 6 months total across jobs), no risk. Otherwise exponential increase.
    r_timeline = 1.0 - math.exp(-0.04 * max(0.0, total_timeline_gap - 6.0))
    if r_timeline > 0.1:
        reasons.append(f"career timeline gap of {total_timeline_gap:.0f}mo (p={r_timeline:.2f})")

    # ── 5. Unrealistic Skill Density Risk ──────────────────────────────────
    skill_count = len(skills)
    total_endorsements = sum(s.get("endorsements", 0) for s in skills)
    avg_endorsements = total_endorsements / max(skill_count, 1)

    # Risk grows with skill count and decays with average endorsements
    r_density = (1.0 - math.exp(-0.1 * skill_count)) * math.exp(-0.5 * avg_endorsements)
    if r_density > 0.2:
        reasons.append(f"high skill density {skill_count} with low endorsements {avg_endorsements:.1f} (p={r_density:.2f})")

    # ── 6. Profile Completeness vs Activity Paradox Risk ───────────────────
    completeness = redrob.get("profile_completeness_score", 0) / 100.0
    views_30d = redrob.get("profile_views_received_30d", 0)
    open_to_work = redrob.get("open_to_work_flag", False)

    # High completeness, open to work, but zero views received
    if open_to_work:
        r_paradox = completeness * math.exp(-0.1 * views_30d) * 0.45
    else:
        r_paradox = 0.0
    if r_paradox > 0.1:
        reasons.append(f"completeness vs activity paradox (p={r_paradox:.2f})")

    # ── 7. Impossible YoE vs Education Timeline Overlap Risk ───────────────
    yoe = profile.get("years_of_experience", 0)
    overlap_years = 0.0
    if education:
        latest_edu_end = max((e.get("end_year", 2000) for e in education), default=2000)
        earliest_work_start = None
        for job in career_history:
            start_str = job.get("start_date", "")
            if start_str:
                try:
                    year = int(start_str[:4])
                    if earliest_work_start is None or year < earliest_work_start:
                        earliest_work_start = year
                except ValueError:
                    pass

        if earliest_work_start and earliest_work_start < latest_edu_end:
            overlap_years = max(0.0, float(latest_edu_end - earliest_work_start))

    # Overlap up to 2 years (part-time student jobs) is ignored. Risk grows exponentially after.
    r_overlap = 1.0 - math.exp(-0.35 * max(0.0, overlap_years - 2.0))
    if r_overlap > 0.1:
        reasons.append(f"work-education overlap of {overlap_years:.1f} yrs (p={r_overlap:.2f})")

    # ── 8. Suspicious Progression Risk ─────────────────────────────────────
    # Junior/Intern roles occurring after Senior/Lead roles
    has_senior = False
    suspicious_transition = False
    # Sort chronologically by job start
    try:
        sorted_jobs = sorted(career_history, key=lambda j: j.get("start_date", ""))
        for j in sorted_jobs:
            job_title = j.get("title", "").lower()
            if any(kw in job_title for kw in ["senior", "lead", "principal", "manager", "director"]):
                has_senior = True
            if has_senior and any(kw in job_title for kw in ["intern", "trainee", "fresher"]):
                suspicious_transition = True
                break
    except Exception:
        pass
        
    r_progression = 0.65 if suspicious_transition else 0.0
    if r_progression > 0.1:
        reasons.append(f"suspicious seniority regression (p={r_progression:.2f})")

    # ── Vectorized Noisy-OR Combination ────────────────────────────────────
    risk_prob = 1.0 - (
        (1.0 - r_title_skill)
        * (1.0 - r_expert_zero)
        * (1.0 - r_assessment)
        * (1.0 - r_timeline)
        * (1.0 - r_density)
        * (1.0 - r_paradox)
        * (1.0 - r_overlap)
        * (1.0 - r_progression)
    )

    reason_str = "; ".join(reasons)
    return round(risk_prob, 4), reason_str
