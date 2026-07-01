"""
behavioral_engine.py — Redrob signal composite scoring
Converts raw behavioral signals into continuous multiplicative scores.
Implements: Priority 4 (Multiplicative Hireability), Priority 7 (Behavioral Multipliers), Priority 8 (Remove Step Functions).
"""
import logging
import math
from datetime import datetime
from typing import Dict, Tuple

from redrob_ranker.config import REFERENCE_DATE_STR

logger = logging.getLogger(__name__)

REFERENCE_DATE = datetime.strptime(REFERENCE_DATE_STR, "%Y-%m-%d")


def _days_since(date_str: str) -> int:
    """Returns days since the reference date (YYYY-MM-DD)."""
    if not date_str:
        return 9999
    try:
        dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
        return max(0, (REFERENCE_DATE - dt).days)
    except ValueError:
        return 9999


def compute_location_factor(profile: dict, signals: dict) -> float:
    from redrob_ranker.config import PREFERRED_CITIES
    country = profile.get("country", "").strip()
    location = profile.get("location", "").lower().strip()
    
    loc_score = 0.55
    if country.lower() == "india":
        loc_score = 0.75
        for city in PREFERRED_CITIES:
            if city in location:
                loc_score = 1.0
                break
    else:
        if signals.get("willing_to_relocate", False):
            loc_score = 0.70
    return loc_score


def compute_hireability_probability(signals: dict, profile: dict = None) -> float:
    """
    Module 7: Hireability Engine (Multiplicative Upgrade).
    Estimates the realistic probability that a candidate can be hired.
    Combines 10 indicators multiplicatively. Uses continuous sigmoidal and exponential decay curves.
    """
    # 1. Open to Work (OTW) Status
    otw = signals.get("open_to_work_flag", False)
    otw_factor = 1.0 if otw else 0.70  # Passive but still recruitable

    # 2. Activity Recency (Exponential Decay)
    days_since_active = _days_since(signals.get("last_active_date", ""))
    # Decays from 1.0 to 0.4 over ~180 days
    activity_factor = 0.4 + 0.6 * math.exp(-0.005 * days_since_active)

    # 3. Notice Period (Sigmoid Decay)
    notice_days = signals.get("notice_period_days", 90)
    # Inflection point at 60 days, slope scaling factor 15
    notice_factor = 0.5 + 0.5 / (1.0 + math.exp((notice_days - 60) / 15))

    # 4. Recruiter Response Rate
    response_rate = signals.get("recruiter_response_rate", 0)
    response_rate_factor = 0.4 + 0.6 * response_rate

    # 5. Average Response Time in Hours (Sigmoid Decay)
    response_hours = signals.get("avg_response_time_hours", 999)
    # Inflection point at 48 hours, slope scaling factor 24
    response_time_factor = 0.6 + 0.4 / (1.0 + math.exp((response_hours - 48) / 24))

    # 6. Interview Completion Rate (ICR)
    icr = signals.get("interview_completion_rate", 0)
    icr_factor = 0.3 + 0.7 * icr

    # 7. Offer Acceptance Rate (OAR)
    oar = signals.get("offer_acceptance_rate", -1)
    if oar >= 0:
        oar_factor = 0.4 + 0.6 * oar
    else:
        oar_factor = 0.85  # Neutral default for no historical offers

    # 8. Platform Engagement (Applications + Recruiter saves + Search appearances)
    apps = signals.get("applications_submitted_30d", 0)
    saved = signals.get("saved_by_recruiters_30d", 0)
    searches = signals.get("search_appearance_30d", 0)
    
    engagement_sum = (apps / 10.0) + (saved / 10.0) + (searches / 200.0)
    engagement_factor = 0.7 + 0.3 * min(1.0, engagement_sum)

    # Multiplicative aggregation
    prob = (
        otw_factor
        * activity_factor
        * notice_factor
        * response_rate_factor
        * response_time_factor
        * icr_factor
        * oar_factor
        * engagement_factor
    )
    
    num_factors = 8
    if profile is not None:
        prob *= compute_location_factor(profile, signals)
        num_factors += 1
        
    # Scale via geometric mean to prevent exponential decay of multiple passive factors
    prob = math.pow(prob, 1.0 / num_factors)
    
    return round(min(1.0, max(0.0, prob)), 4)


def compute_all_behavioral_scores(signals: dict, profile: dict = None) -> Dict[str, float]:
    """
    Computes composites for the feature vector.
    Conforms to the new multiplicative structure.
    """
    return {
        "hireability_probability": compute_hireability_probability(signals, profile),
    }


def compute_availability_score(signals: dict) -> float:
    """Compatibility function for unit tests."""
    otw = signals.get("open_to_work_flag", False)
    days = _days_since(signals.get("last_active_date", ""))
    notice = signals.get("notice_period_days", 90)
    
    otw_factor = 1.0 if otw else 0.70
    activity_factor = 0.4 + 0.6 * math.exp(-0.005 * days)
    notice_factor = 0.5 + 0.5 / (1.0 + math.exp((notice - 60) / 15))
    
    return round(otw_factor * activity_factor * notice_factor, 4)


def compute_responsiveness_score(signals: dict) -> float:
    """Compatibility function for unit tests."""
    rate = signals.get("recruiter_response_rate", 0)
    hours = signals.get("avg_response_time_hours", 999)
    
    rate_factor = 0.5 * rate
    time_factor = 0.5 * (1.0 / (1.0 + math.exp((hours - 48) / 12)))
    
    return round(rate_factor + time_factor, 4)


def compute_trust_score(signals: dict) -> float:
    """Compatibility function for unit tests."""
    email = signals.get("verified_email", False)
    phone = signals.get("verified_phone", False)
    linkedin = signals.get("linkedin_connected", False)
    
    score = 0.0
    if email: score += 0.40
    if phone: score += 0.35
    if linkedin: score += 0.25
    return round(score, 4)

