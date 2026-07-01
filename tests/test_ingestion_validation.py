import sys
import os
import json
import pytest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from redrob_ranker.utils.data_ingestion import (
    map_dynamic_candidate,
    parse_tabular_candidate,
    stream_candidates_from_bytes
)
from redrob_ranker.utils.schema_validator import SchemaValidator
from redrob_ranker.engines.jd_ingestion_engine import extract_jd_rule_based

# ─────────────────────────────────────────────────────────────
# MOCK DATA FOR INGESTION & VALIDATION
# ─────────────────────────────────────────────────────────────

MOCK_CANDIDATE_RAW = {
    "id": "CAND_9999999",
    "personal": {
        "name": "Alex Smith",
        "title": "Machine Learning Engineer",
        "about": "Expert in search systems and ranking architectures.",
        "location": "Gurgaon",
        "yoe": 6.5
    },
    "work_history": [
        {
            "company": "Tech Corp",
            "title": "Senior ML Engineer",
            "start": "2022-01-01",
            "end": "2025-12-31",
            "duration": 48,
            "current": True,
            "description": "Led vector search implementation using FAISS."
        }
    ],
    "skills": ["python", "faiss", "elasticsearch"],
    "signals": {
        "profile_completeness_score": 90.0,
        "signup_date": "2024-01-01",
        "last_active_date": "2026-06-20",
        "open_to_work_flag": True,
        "recruiter_response_rate": 0.85,
        "avg_response_time_hours": 12.0,
        "connection_count": 120,
        "notice_period_days": 15,
        "expected_salary_range_inr_lpa": {"min": 30, "max": 45},
        "preferred_work_mode": "remote",
        "willing_to_relocate": True,
        "github_activity_score": 75.0,
        "verified_email": True,
        "verified_phone": True,
        "linkedin_connected": True
    }
}

MOCK_JD_MD = """
# Senior AI/ML Engineer (Ranking & Retrieval)

## About the Position
Join our team to build next-generation search engines.

## Requirements
- 5 to 9 years of professional experience building ML systems.
- Proven expertise in Python, PyTorch, FAISS, and Elasticsearch.
- Deep understanding of dense retrieval and cross-encoder reranking.

## Nice-to-Have
- Familiarity with MLOps pipelines including Docker and Kubernetes.
- Experience with PyTorch LightGBM and HuggingFace.

## Location & Environment
- Location: Bangalore, India
- Environment: Hybrid work mode
"""

# ─────────────────────────────────────────────────────────────
# TESTS
# ─────────────────────────────────────────────────────────────

def test_dynamic_key_synonym_mapping():
    mapped = map_dynamic_candidate(MOCK_CANDIDATE_RAW)
    assert mapped["candidate_id"] == "CAND_9999999"
    assert mapped["profile"]["anonymized_name"] == "Alex Smith"
    assert mapped["profile"]["years_of_experience"] == 6.5
    assert len(mapped["career_history"]) == 1
    assert mapped["career_history"][0]["company"] == "Tech Corp"
    assert any(s["name"] == "faiss" for s in mapped["skills"])
    assert mapped["redrob_signals"]["notice_period_days"] == 15

def test_tabular_row_parsing():
    row = {
        "candidate_id": "CAND_1111111",
        "name": "Jane Doe",
        "experience": "4.5",
        "skills": "Python, FAISS, Elasticsearch"
    }
    mapped = parse_tabular_candidate(row)
    assert mapped["candidate_id"] == "CAND_1111111"
    assert mapped["profile"]["years_of_experience"] == 4.5
    assert len(mapped["skills"]) == 3
    assert any(s["name"] == "Python" for s in mapped["skills"])

def test_layout_aware_jd_parsing():
    jd = extract_jd_rule_based(MOCK_JD_MD)
    assert jd["job_title"] == "Senior AI/ML Engineer (Ranking & Retrieval)"
    assert jd["yoe_min"] == 5
    assert jd["yoe_max"] == 9
    assert jd["location"] == "Bangalore"
    assert jd["work_mode"] == "hybrid"
    
    # Required skills checks
    assert "faiss" in jd["required_skills"]
    assert "elasticsearch" in jd["required_skills"]
    
    # Preferred skills checks
    assert "docker" in jd["nice_to_have_skills"]
    assert "kubernetes" in jd["nice_to_have_skills"]
    # Should not overlap
    assert "faiss" not in jd["nice_to_have_skills"]

def test_schema_validator_good():
    validator = SchemaValidator()
    # If candidate_schema.json is present, check that mapped candidate is valid
    if validator.schema:
        mapped = map_dynamic_candidate(MOCK_CANDIDATE_RAW)
        errors = validator.validate_candidate(mapped)
        assert len(errors) == 0, f"Expected valid candidate, got errors: {errors}"

def test_schema_validator_invalid():
    validator = SchemaValidator()
    if validator.schema:
        invalid_candidate = {
            "candidate_id": "INVALID_ID_FORMAT",
            "profile": {},  # missing all required fields
            "career_history": []
        }
        errors = validator.validate_candidate(invalid_candidate)
        assert len(errors) > 0
        assert any("pattern" in e for e in errors)
        assert any("Missing root required field" in e for e in errors)
