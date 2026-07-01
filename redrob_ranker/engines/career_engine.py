"""
career_engine.py — Module 6: Career Trajectory Engine
Computes promotion velocity, growth rate, leadership signals.
"""
import logging
from datetime import datetime
from typing import Dict, List

logger = logging.getLogger(__name__)

REFERENCE_DATE = datetime(2026, 6, 22)

# Seniority tiers (higher = more senior)
TITLE_SENIORITY: Dict[str, int] = {
    "intern": 0, "trainee": 0, "apprentice": 0,
    "junior": 1, "associate": 1, "entry": 1,
    "engineer": 2, "developer": 2, "analyst": 2, "scientist": 2,
    "senior": 3, "sr": 3,
    "lead": 4, "principal": 5, "staff": 5,
    "manager": 4, "head": 5,
    "director": 6, "vp": 7, "chief": 8,
}

LEADERSHIP_KEYWORDS = {"lead", "head", "principal", "staff", "director", "vp", "chief", "manager", "architect"}
AI_ROLE_KEYWORDS = {"ml", "machine learning", "ai", "data scien", "nlp", "search", "ranking", "recommendation", "retrieval", "deep learning"}


def _title_seniority(title: str) -> int:
    """Map a job title to a seniority score 0-8."""
    title_lower = title.lower()
    best = 0
    for kw, score in TITLE_SENIORITY.items():
        if kw in title_lower:
            best = max(best, score)
    return best


def _parse_year(date_str: str) -> float:
    """Return decimal year from YYYY-MM-DD string."""
    if not date_str:
        return 0.0
    try:
        dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
        return dt.year + dt.month / 12.0
    except ValueError:
        return 0.0


def compute_promotion_velocity(career_history: List[dict]) -> float:
    """
    Measures how fast the candidate has been promoted relative to peers.
    Formula: seniority_gain / years_of_career
    Scale: 0 (no growth) → 1.0 (fast-tracked to principal/staff in 5yr)
    """
    if not career_history:
        return 0.0

    # Sort chronologically
    jobs = sorted(career_history, key=lambda j: _parse_year(j.get("start_date", "")))
    if len(jobs) < 2:
        return 0.30  # Only one job — neutral

    first_seniority = _title_seniority(jobs[0].get("title", ""))
    last_seniority = _title_seniority(jobs[-1].get("title", ""))
    seniority_gain = last_seniority - first_seniority

    first_year = _parse_year(jobs[0].get("start_date", ""))
    last_year = _parse_year(jobs[-1].get("end_date") or "2026-06-22")
    career_years = max(0.5, last_year - first_year)

    # velocity: seniority gained per year (max meaningful = 0.8/yr for fast track)
    velocity = seniority_gain / career_years
    # Normalize: 0.8/yr → 1.0, 0 → 0.0
    normalized = min(1.0, max(0.0, velocity / 0.8))
    return round(normalized, 4)


def compute_career_growth_score(career_history: List[dict]) -> float:
    """
    Overall career growth assessment combining:
    - Promotion velocity (35%)
    - Seniority of latest role (30%)
    - AI role progression (20%)
    - Job tenure stability (15%)
    """
    if not career_history:
        return 0.0

    # 1. Promotion velocity
    promo_vel = compute_promotion_velocity(career_history)

    # 2. Current seniority level (normalized to 0-1 from 0-8 scale)
    latest = max(career_history, key=lambda j: _parse_year(j.get("start_date", "")), default={})
    current_seniority = _title_seniority(latest.get("title", "")) / 8.0

    # 3. AI role progression — fraction of career in AI roles
    total_months = sum(j.get("duration_months", 0) for j in career_history)
    ai_months = sum(
        j.get("duration_months", 0)
        for j in career_history
        if any(kw in j.get("title", "").lower() for kw in AI_ROLE_KEYWORDS)
    )
    ai_fraction = ai_months / max(1, total_months)

    # 4. Stability — penalize too many short stints (<12mo), reward long tenures
    short_stints = sum(1 for j in career_history if 0 < j.get("duration_months", 0) < 12)
    stability = max(0.0, 1.0 - (short_stints / max(1, len(career_history))))

    score = (
        0.35 * promo_vel
        + 0.30 * current_seniority
        + 0.20 * ai_fraction
        + 0.15 * stability
    )
    return round(min(1.0, score), 4)


def compute_leadership_signal(career_history: List[dict]) -> float:
    """
    1.0 if candidate has held a leadership/principal/staff role.
    0.5 if senior engineer but never lead.
    0.0 if no seniority progression.
    """
    for job in career_history:
        title_lower = job.get("title", "").lower()
        if any(lkw in title_lower for lkw in LEADERSHIP_KEYWORDS):
            return 1.0
    # Check for "senior" without leadership
    for job in career_history:
        if "senior" in job.get("title", "").lower() or "sr" in job.get("title", "").lower():
            return 0.50
    return 0.15


def compute_avg_tenure(career_history: List[dict]) -> float:
    """
    Average tenure per job normalized to 0-1.
    Optimal range: 18-36 months. 
    Smoothly decays for job-hoppers (<18) or stagnation (>36).
    """
    if not career_history:
        return 0.50

    durations = [j.get("duration_months", 0) for j in career_history if j.get("duration_months", 0) > 0]
    if not durations:
        return 0.50

    import math
    avg = sum(durations) / len(durations)
    if 18.0 <= avg <= 36.0:
        return 1.0
    elif avg < 18.0:
        # Smoothly climbs from 0.2 to 1.0
        return round(0.20 + 0.80 * (avg / 18.0), 4)
    else:
        # Smoothly decays from 1.0 down towards 0.35
        return round(0.35 + 0.65 * math.exp(-(avg - 36.0) / 24.0), 4)


def compute_all_career_scores(career_history: List[dict]) -> Dict[str, float]:
    """Return all career trajectory scores."""
    return {
        "promotion_velocity": compute_promotion_velocity(career_history),
        "career_growth_score": compute_career_growth_score(career_history),
        "leadership_signal": compute_leadership_signal(career_history),
        "avg_tenure_score": compute_avg_tenure(career_history),
    }
