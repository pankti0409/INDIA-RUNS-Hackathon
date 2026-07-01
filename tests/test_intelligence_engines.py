"""
test_intelligence_engines.py — Unit tests for the 6 newly added Core Intelligence Engines:
1. Job Description Intelligence Engine (Block 2)
2. Dynamic Weight Generation Engine (Block 12)
3. Technology Taxonomy & Skill Graph (Block 4)
4. Candidate Intelligence Engine (Block 3)
5. Company & Industry Intelligence Engine (Block 13)
6. Decision Engine & Self-Verification (Block 10)
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from redrob_ranker.engines.jd_intelligence_engine import parse_jd, get_jd_intelligence
from redrob_ranker.engines.dynamic_weight_engine import generate_dynamic_weights, get_weight_profile
from redrob_ranker.engines.skill_graph import (
    compute_skill_similarity,
    compute_skill_set_coverage,
    compute_domain_coverage,
    compute_transferability_score,
)
from redrob_ranker.engines.candidate_intelligence_engine import build_candidate_intelligence
from redrob_ranker.engines.company_intelligence_engine import compute_company_intelligence
from redrob_ranker.engines.decision_engine import generate_hiring_decision


# ─────────────────────────────────────────────────────────────────────────────
# Test Fixtures / Mock Data
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_candidate_ml():
    return {
        "candidate_id": "TEST_CAND_001",
        "profile": {
            "current_title": "Senior AI/ML Engineer",
            "years_of_experience": 8,
            "location": "Bangalore",
            "country": "India",
            "summary": "Specialized in search ranking and dense retrieval systems. Designed and deployed vector databases at scale.",
            "headline": "Senior ML Engineer | Ranking & Search"
        },
        "skills": [
            {"name": "Python", "proficiency": "expert"},
            {"name": "PyTorch", "proficiency": "expert"},
            {"name": "FAISS", "proficiency": "advanced"},
            {"name": "Elasticsearch", "proficiency": "advanced"},
            {"name": "sentence-transformers", "proficiency": "advanced"},
        ],
        "career_history": [
            {
                "title": "Senior ML Engineer",
                "company": "Google",
                "duration_months": 36,
                "is_current": True,
                "description": "Led system design and development of dense retrieval pipelines. Deployed models serving 1M QPS with sub-50ms latency. Mentored 3 junior engineers."
            },
            {
                "title": "ML Engineer",
                "company": "Swiggy",
                "duration_months": 24,
                "is_current": False,
                "description": "Developed restaurant recommendation engine using collaborative filtering and PyTorch."
            }
        ],
        "education": [
            {
                "degree": "M.Tech",
                "institution": "IIT Bombay",
                "tier": "tier_1",
                "field_of_study": "Computer Science"
            }
        ],
        "redrob_signals": {
            "github_activity_score": 88,
            "profile_completeness_score": 95,
            "skill_assessment_scores": {"ML": 90}
        }
    }


@pytest.fixture
def sample_candidate_non_ml():
    return {
        "candidate_id": "TEST_CAND_002",
        "profile": {
            "current_title": "Graphic Designer",
            "years_of_experience": 4,
            "location": "Delhi",
            "country": "India",
            "summary": "Creative designer specializing in branding and UI layouts.",
            "headline": "Graphic Designer | UI"
        },
        "skills": [
            {"name": "Photoshop", "proficiency": "expert"},
            {"name": "Illustrator", "proficiency": "expert"},
        ],
        "career_history": [
            {
                "title": "Graphic Designer",
                "company": "Creative Agency",
                "duration_months": 48,
                "is_current": True,
                "description": "Designed marketing assets and web UI mockups."
            }
        ],
        "education": [],
        "redrob_signals": {
            "github_activity_score": -1,
            "profile_completeness_score": 50
        }
    }


# ─────────────────────────────────────────────────────────────────────────────
# 1. JD Intelligence Engine Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_jd_intelligence_engine_parsing():
    jd_text = """
    Senior AI/ML Engineer – Ranking & Retrieval
    We are looking for a staff engineer with 8+ years of experience.
    Must Have:
    - sentence-transformers and dense retrieval
    - FAISS and Elasticsearch
    - Learning to Rank (LTR), NDCG metrics
    Preferred:
    - Kubernetes and Triton serving
    Responsibilities:
    - Mentor junior engineers and design search architecture.
    """
    intel = parse_jd(jd_text)
    
    assert intel["primary_role_type"] == "retrieval_ranking"
    assert intel["seniority"] == "staff"
    assert intel["yoe_min"] == 8
    assert "faiss" in intel["mandatory_skills"]
    assert "elasticsearch" in intel["mandatory_skills"]
    assert "kubernetes" in intel["preferred_skills"]
    assert intel["leadership_required"] is True
    assert intel["location_required"] is True


def test_jd_intelligence_singleton():
    intel = get_jd_intelligence()
    assert intel is not None
    assert "primary_role_type" in intel
    assert "mandatory_skills" in intel


# ─────────────────────────────────────────────────────────────────────────────
# 2. Dynamic Weight Generation Engine Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_dynamic_weight_generation():
    jd_intel = {
        "primary_role_type": "retrieval_ranking",
        "seniority": "staff",
        "mandatory_skills": ["faiss", "sentence-transformers"],
        "preferred_skills": ["kubernetes"],
        "leadership_required": True,
        "research_required": False
    }
    profile = generate_dynamic_weights(jd_intel)
    weights = profile["feature_weights"]
    
    # Verify sum normalization
    assert abs(sum(weights.values()) - 1.0) < 1e-5
    # Verify specific boosts
    assert weights["core_skill_score"] > 0.15
    assert weights["leadership_signal"] > 0.05
    assert "scoring_profile" in profile


# ─────────────────────────────────────────────────────────────────────────────
# 3. Technology Taxonomy & Skill Graph Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_skill_graph_similarity():
    # Exact match
    assert compute_skill_similarity("faiss", "faiss") == 1.0
    # Proximity matching (FAISS is highly similar to Pinecone/Milvus)
    assert compute_skill_similarity("faiss", "milvus") >= 0.80
    assert compute_skill_similarity("faiss", "pinecone") >= 0.80
    # Two-hop / related matching
    assert compute_skill_similarity("faiss", "elasticsearch") >= 0.50
    # Unrelated
    assert compute_skill_similarity("faiss", "photoshop") == 0.0


def test_skill_set_coverage():
    cand_skills = {"faiss", "elasticsearch", "python"}
    jd_skills = {"milvus", "opensearch", "python", "kubernetes"}
    
    coverage = compute_skill_set_coverage(cand_skills, jd_skills)
    assert coverage["exact_coverage"] == 0.25  # python
    assert coverage["soft_coverage"] >= 0.75  # faiss->milvus, elastic->opensearch, python->python
    assert coverage["transferable_count"] >= 2


def test_domain_coverage():
    cand_skills = {"faiss", "milvus", "pinecone"}
    # vector_retrieval domain should be covered
    cov = compute_domain_coverage(cand_skills, ["vector_retrieval", "search_systems"])
    assert cov > 0.40


def test_transferability_score():
    score = compute_transferability_score(["recommendation"], ["search_and_ranking"])
    assert score >= 0.70


# ─────────────────────────────────────────────────────────────────────────────
# 4. Candidate Intelligence Engine Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_candidate_intelligence(sample_candidate_ml):
    jd_intel = get_jd_intelligence()
    intel = build_candidate_intelligence(sample_candidate_ml, jd_intel)
    
    assert intel["engineering_maturity_level"] in ("technical_leader", "system_designer")
    assert intel["leadership_evidence_score"] > 0.40
    assert intel["leadership_categories"]["mentoring"] is True
    assert intel["leadership_categories"]["ownership"] is True
    assert intel["project_complexity_score"] > 0.40
    assert intel["has_meaningful_transferability"] is True
    assert intel["transferable_skill_score"] > 0.40


# ─────────────────────────────────────────────────────────────────────────────
# 5. Company & Industry Intelligence Engine Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_company_intelligence(sample_candidate_ml):
    history = sample_candidate_ml["career_history"]
    intel = compute_company_intelligence(history)
    
    assert intel["has_big_tech_experience"] is True
    assert intel["has_product_company"] is True
    assert intel["is_pure_consulting"] is False
    assert intel["company_quality_score"] > 0.70
    assert intel["engineering_exposure_score"] > 0.70
    assert intel["best_company_type"] == "big_tech"


# ─────────────────────────────────────────────────────────────────────────────
# 6. Decision Engine & Self-Verification Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_decision_engine_hire_flow(sample_candidate_ml):
    # High-scoring features
    features = {
        "core_skill_score": 0.85,
        "role_specific_depth_score": 0.80,
        "yoe_score": 0.90,
        "trust_score": 0.95,
        "risk_probability": 0.02,
        "has_product_company": 1.0,
        "ai_experience_score": 0.80,
        "profile_completeness_score": 95.0,
        "engineering_maturity_score": 0.85,
        "production_at_scale": 1.0,
        "has_search_ranking_experience": 1.0,
        "has_big_tech_experience": 1.0
    }
    
    decision = generate_hiring_decision(sample_candidate_ml, features, 0.88, 1)
    
    assert decision["recommendation_key"] == "strong_hire"
    assert decision["confidence_tier"] in ("High", "Very High")
    assert len(decision["top_strengths"]) >= 3
    assert len(decision["risk_factors"]) == 0
    assert decision["self_verification"]["all_checks_passed"] is True
    assert decision["review_required"] is False


def test_decision_engine_reject_flow(sample_candidate_non_ml):
    # Disqualifier and low features
    features = {
        "core_skill_score": 0.0,
        "role_specific_depth_score": 0.0,
        "yoe_score": 0.10,
        "trust_score": 0.20,
        "risk_probability": 0.85,  # High risk
        "is_disqualifier_title": 1.0,
        "title_tier": "tier_5",
        "is_pure_consulting": 0.0
    }
    
    decision = generate_hiring_decision(sample_candidate_non_ml, features, 0.05, 95)
    
    assert decision["recommendation_key"] == "reject"
    assert len(decision["key_gaps"]) >= 2
    assert len(decision["risk_factors"]) >= 1
    assert decision["self_verification"]["all_checks_passed"] is True
