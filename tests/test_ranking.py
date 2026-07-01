"""
test_ranking.py — Unit tests for the Redrob ranking system
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from redrob_ranker.engines.honeypot_engine import detect_honeypot
from redrob_ranker.engines.behavioral_engine import (
    compute_availability_score,
    compute_responsiveness_score,
    compute_trust_score,
)
from redrob_ranker.engines.feature_engine import (
    compute_title_score,
    is_disqualifier_title,
    compute_core_skill_match_score,
    compute_experience_score,
    extract_features,
)
from redrob_ranker.engines.ranking_engine import compute_final_score


# ─────────────────────────────────────────────────────────────
# Test fixtures
# ─────────────────────────────────────────────────────────────

def make_ml_candidate(overrides=None):
    """Create a canonical ML Engineer candidate (should rank highly)."""
    c = {
        "candidate_id": "CAND_0000001",
        "profile": {
            "anonymized_name": "Test User",
            "headline": "ML Engineer | Ranking & Retrieval",
            "summary": "Senior ML engineer with 7 years experience. Built production ranking systems using FAISS, Elasticsearch, and sentence-transformers. Deployed RAG pipelines at scale.",
            "location": "Noida, Uttar Pradesh",
            "country": "India",
            "years_of_experience": 7.0,
            "current_title": "Senior ML Engineer",
            "current_company": "Paytm",
            "current_company_size": "5001-10000",
            "current_industry": "FinTech",
        },
        "career_history": [
            {
                "company": "Paytm",
                "title": "Senior ML Engineer",
                "start_date": "2021-01-01",
                "end_date": None,
                "duration_months": 42,
                "is_current": True,
                "industry": "FinTech",
                "company_size": "5001-10000",
                "description": "Built production recommendation and search ranking systems using FAISS, Elasticsearch, and dense retrieval. Deployed to millions of users.",
            }
        ],
        "education": [
            {
                "institution": "IIT Delhi",
                "degree": "B.Tech",
                "field_of_study": "Computer Science",
                "start_year": 2013,
                "end_year": 2017,
                "grade": "8.5 CGPA",
                "tier": "tier_1",
            }
        ],
        "skills": [
            {"name": "Python", "proficiency": "expert", "endorsements": 80, "duration_months": 72},
            {"name": "FAISS", "proficiency": "advanced", "endorsements": 30, "duration_months": 36},
            {"name": "Elasticsearch", "proficiency": "advanced", "endorsements": 25, "duration_months": 42},
            {"name": "NLP", "proficiency": "advanced", "endorsements": 40, "duration_months": 48},
            {"name": "Sentence Transformers", "proficiency": "advanced", "endorsements": 20, "duration_months": 24},
        ],
        "certifications": [],
        "languages": [{"language": "English", "proficiency": "professional"}],
        "redrob_signals": {
            "profile_completeness_score": 95.0,
            "signup_date": "2024-01-01",
            "last_active_date": "2026-06-20",
            "open_to_work_flag": True,
            "profile_views_received_30d": 45,
            "applications_submitted_30d": 3,
            "recruiter_response_rate": 0.80,
            "avg_response_time_hours": 12.0,
            "skill_assessment_scores": {"Python": 95, "NLP": 88, "FAISS": 82},
            "connection_count": 500,
            "endorsements_received": 120,
            "notice_period_days": 30,
            "expected_salary_range_inr_lpa": {"min": 30, "max": 50},
            "preferred_work_mode": "hybrid",
            "willing_to_relocate": True,
            "github_activity_score": 85.0,
            "search_appearance_30d": 150,
            "saved_by_recruiters_30d": 12,
            "interview_completion_rate": 0.95,
            "offer_acceptance_rate": 0.80,
            "verified_email": True,
            "verified_phone": True,
            "linkedin_connected": True,
        },
    }
    if overrides:
        for k, v in overrides.items():
            if isinstance(v, dict) and isinstance(c.get(k), dict):
                c[k].update(v)
            else:
                c[k] = v
    return c


def make_disqualifier_candidate():
    """Marketing Manager with AI keywords — should rank very low (trap candidate)."""
    return {
        "candidate_id": "CAND_9999999",
        "profile": {
            "anonymized_name": "Trap User",
            "headline": "Marketing Manager | AI Enthusiast",
            "summary": "Marketing manager with experience in ChatGPT, LLMs, NLP.",
            "location": "Mumbai",
            "country": "India",
            "years_of_experience": 8.0,
            "current_title": "Marketing Manager",
            "current_company": "Acme Corp",
            "current_company_size": "201-500",
            "current_industry": "Marketing",
        },
        "career_history": [
            {
                "company": "Acme Corp",
                "title": "Marketing Manager",
                "start_date": "2020-01-01",
                "end_date": None,
                "duration_months": 78,
                "is_current": True,
                "industry": "Marketing",
                "company_size": "201-500",
                "description": "Led marketing campaigns and content strategy.",
            }
        ],
        "education": [
            {
                "institution": "Local College",
                "degree": "B.A.",
                "field_of_study": "Marketing",
                "start_year": 2012,
                "end_year": 2016,
                "tier": "tier_4",
            }
        ],
        "skills": [
            {"name": "NLP", "proficiency": "advanced", "endorsements": 0, "duration_months": 0},
            {"name": "FAISS", "proficiency": "expert", "endorsements": 0, "duration_months": 0},
            {"name": "Elasticsearch", "proficiency": "expert", "endorsements": 0, "duration_months": 0},
            {"name": "Python", "proficiency": "advanced", "endorsements": 0, "duration_months": 0},
            {"name": "Machine Learning", "proficiency": "expert", "endorsements": 0, "duration_months": 0},
            {"name": "RAG", "proficiency": "expert", "endorsements": 0, "duration_months": 0},
            {"name": "LLM", "proficiency": "expert", "endorsements": 0, "duration_months": 0},
        ],
        "certifications": [],
        "languages": [],
        "redrob_signals": {
            "profile_completeness_score": 70.0,
            "signup_date": "2024-06-01",
            "last_active_date": "2026-06-01",
            "open_to_work_flag": True,
            "profile_views_received_30d": 5,
            "applications_submitted_30d": 2,
            "recruiter_response_rate": 0.4,
            "avg_response_time_hours": 48.0,
            "skill_assessment_scores": {},
            "connection_count": 200,
            "endorsements_received": 5,
            "notice_period_days": 60,
            "expected_salary_range_inr_lpa": {"min": 15, "max": 25},
            "preferred_work_mode": "hybrid",
            "willing_to_relocate": False,
            "github_activity_score": -1,
            "search_appearance_30d": 20,
            "saved_by_recruiters_30d": 2,
            "interview_completion_rate": 0.5,
            "offer_acceptance_rate": -1,
            "verified_email": True,
            "verified_phone": False,
            "linkedin_connected": False,
        },
    }


# ─────────────────────────────────────────────────────────────
# Title scoring tests
# ─────────────────────────────────────────────────────────────

class TestTitleScoring:
    def test_ml_engineer_scores_high(self):
        assert compute_title_score("ML Engineer") >= 0.90

    def test_senior_ml_engineer_scores_high(self):
        assert compute_title_score("Senior Machine Learning Engineer") >= 0.90

    def test_search_engineer_scores_high(self):
        assert compute_title_score("Search Engineer") >= 0.90

    def test_recommendation_engineer_scores_high(self):
        assert compute_title_score("Recommendation Systems Engineer") >= 0.90

    def test_marketing_manager_scores_very_low(self):
        assert compute_title_score("Marketing Manager") < 0.10

    def test_hr_manager_scores_very_low(self):
        assert compute_title_score("HR Manager") < 0.10

    def test_accountant_scores_very_low(self):
        assert compute_title_score("Accountant") < 0.10

    def test_civil_engineer_scores_very_low(self):
        assert compute_title_score("Civil Engineer") < 0.10

    def test_data_scientist_scores_good(self):
        assert compute_title_score("Data Scientist") >= 0.80

    def test_ai_engineer_scores_high(self):
        assert compute_title_score("AI Engineer") >= 0.90


class TestDisqualifierDetection:
    def test_marketing_manager_is_disqualifier(self):
        assert is_disqualifier_title("Marketing Manager") is True

    def test_hr_manager_is_disqualifier(self):
        assert is_disqualifier_title("HR Manager") is True

    def test_ml_engineer_is_not_disqualifier(self):
        assert is_disqualifier_title("ML Engineer") is False

    def test_senior_ml_engineer_is_not_disqualifier(self):
        assert is_disqualifier_title("Senior Machine Learning Engineer") is False

    def test_content_writer_is_disqualifier(self):
        assert is_disqualifier_title("Content Writer") is True

    def test_graphic_designer_is_disqualifier(self):
        assert is_disqualifier_title("Graphic Designer") is True


# ─────────────────────────────────────────────────────────────
# Skill scoring tests
# ─────────────────────────────────────────────────────────────

class TestSkillScoring:
    def test_ai_skills_match(self):
        skills = [
            {"name": "FAISS", "proficiency": "advanced", "endorsements": 20, "duration_months": 24},
            {"name": "Elasticsearch", "proficiency": "advanced", "endorsements": 15, "duration_months": 36},
            {"name": "NLP", "proficiency": "expert", "endorsements": 30, "duration_months": 48},
        ]
        score, count = compute_core_skill_match_score(skills)
        assert count == 3
        assert score > 0.3

    def test_no_ai_skills_zero_count(self):
        skills = [
            {"name": "Photoshop", "proficiency": "expert", "endorsements": 20, "duration_months": 60},
            {"name": "Marketing", "proficiency": "expert", "endorsements": 30, "duration_months": 72},
        ]
        _, count = compute_core_skill_match_score(skills)
        assert count == 0

    def test_many_ai_skills_high_score(self):
        skills = [
            {"name": skill, "proficiency": "advanced", "endorsements": 20, "duration_months": 36}
            for skill in ["FAISS", "Elasticsearch", "NLP", "Python", "Sentence Transformers",
                          "Pinecone", "Weaviate", "RAG"]
        ]
        score, count = compute_core_skill_match_score(skills)
        assert count == 8
        assert score >= 0.70  # 8 advanced skills with endorsements, normalized to max 8


# ─────────────────────────────────────────────────────────────
# Honeypot detection tests
# ─────────────────────────────────────────────────────────────

class TestHoneypotDetection:
    def test_legitimate_ml_engineer_no_honeypot(self):
        c = make_ml_candidate()
        prob, reason = detect_honeypot(c)
        assert prob < 0.3, f"Legitimate ML engineer flagged as honeypot: {reason}"

    def test_disqualifier_title_with_ai_skills_is_honeypot(self):
        c = make_disqualifier_candidate()
        prob, reason = detect_honeypot(c)
        assert prob >= 0.5, f"Keyword stuffer not flagged: {reason}"

    def test_expert_skills_zero_months_flagged(self):
        c = make_ml_candidate()
        # Override skills with expert claims but 0 months
        c["skills"] = [
            {"name": "FAISS", "proficiency": "expert", "endorsements": 0, "duration_months": 0},
            {"name": "Elasticsearch", "proficiency": "expert", "endorsements": 0, "duration_months": 0},
            {"name": "NLP", "proficiency": "expert", "endorsements": 0, "duration_months": 0},
            {"name": "RAG", "proficiency": "expert", "endorsements": 0, "duration_months": 0},
            {"name": "Pinecone", "proficiency": "expert", "endorsements": 0, "duration_months": 0},
        ]
        prob, reason = detect_honeypot(c)
        assert prob > 0.3, f"Expert-zero-months pattern not flagged: {reason}"


# ─────────────────────────────────────────────────────────────
# Behavioral signal tests
# ─────────────────────────────────────────────────────────────

class TestBehavioralScoring:
    def test_open_to_work_and_recent_active_high_availability(self):
        signals = {
            "open_to_work_flag": True,
            "last_active_date": "2026-06-20",
            "notice_period_days": 15,
        }
        score = compute_availability_score(signals)
        assert score >= 0.90

    def test_not_open_stale_active_low_availability(self):
        signals = {
            "open_to_work_flag": False,
            "last_active_date": "2025-01-01",  # ~18 months ago
            "notice_period_days": 120,
        }
        score = compute_availability_score(signals)
        assert score <= 0.20

    def test_high_response_rate_high_responsiveness(self):
        signals = {
            "recruiter_response_rate": 0.90,
            "avg_response_time_hours": 6.0,
        }
        score = compute_responsiveness_score(signals)
        assert score >= 0.90

    def test_low_response_rate_low_responsiveness(self):
        signals = {
            "recruiter_response_rate": 0.05,
            "avg_response_time_hours": 200.0,
        }
        score = compute_responsiveness_score(signals)
        assert score <= 0.15

    def test_all_verified_full_trust(self):
        signals = {
            "verified_email": True,
            "verified_phone": True,
            "linkedin_connected": True,
        }
        score = compute_trust_score(signals)
        assert score == 1.0

    def test_nothing_verified_zero_trust(self):
        signals = {
            "verified_email": False,
            "verified_phone": False,
            "linkedin_connected": False,
        }
        score = compute_trust_score(signals)
        assert score == 0.0


# ─────────────────────────────────────────────────────────────
# End-to-end ranking tests
# ─────────────────────────────────────────────────────────────

class TestRankingLogic:
    def test_ml_engineer_scores_higher_than_marketing_manager(self):
        ml = make_ml_candidate()
        mkt = make_disqualifier_candidate()

        ml_feat = extract_features(ml)
        mkt_feat = extract_features(mkt)

        ml_score = compute_final_score(ml_feat)
        mkt_score = compute_final_score(mkt_feat)

        assert ml_score > mkt_score, (
            f"ML Engineer ({ml_score:.4f}) should outscore "
            f"Marketing Manager ({mkt_score:.4f})"
        )

    def test_marketing_manager_score_very_low(self):
        mkt = make_disqualifier_candidate()
        feat = extract_features(mkt)
        score = compute_final_score(feat)
        assert score < 0.30, f"Marketing Manager scored too high: {score:.4f}"

    def test_ml_engineer_score_reasonably_high(self):
        ml = make_ml_candidate()
        feat = extract_features(ml)
        score = compute_final_score(feat)
        assert score >= 0.70, f"ML Engineer scored too low: {score:.4f}"

    def test_score_in_valid_range(self):
        """All scores must be in [0, 1]."""
        for make_fn in [make_ml_candidate, make_disqualifier_candidate]:
            c = make_fn()
            feat = extract_features(c)
            score = compute_final_score(feat)
            assert 0.0 <= score <= 1.0, f"Score out of range: {score}"

    def test_india_location_preferred(self):
        """India-based ML engineer should outscore same profile from abroad."""
        india = make_ml_candidate()
        abroad = make_ml_candidate()
        abroad["profile"]["country"] = "USA"
        abroad["profile"]["location"] = "San Francisco"

        india_feat = extract_features(india)
        abroad_feat = extract_features(abroad)
        india_score = compute_final_score(india_feat)
        abroad_score = compute_final_score(abroad_feat)

        assert india_score > abroad_score, (
            "India-based candidate should outscore abroad candidate"
        )

    def test_active_candidate_beats_inactive(self):
        """Recently active candidate should outscore stale one with same skills."""
        active = make_ml_candidate()
        inactive = make_ml_candidate()
        inactive["redrob_signals"]["last_active_date"] = "2025-01-01"
        inactive["redrob_signals"]["open_to_work_flag"] = False
        inactive["redrob_signals"]["recruiter_response_rate"] = 0.05

        active_feat = extract_features(active)
        inactive_feat = extract_features(inactive)
        active_score = compute_final_score(active_feat)
        inactive_score = compute_final_score(inactive_feat)

        assert active_score > inactive_score, (
            "Active candidate should outscore inactive one"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
