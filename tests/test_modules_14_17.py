import sys
import os
import json
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from redrob_ranker.engines.resume_ingestion_engine import (
    read_file_to_text,
    extract_fields_rule_based,
    build_candidate_schema,
    ingest_resume,
)
from redrob_ranker.engines.jd_ingestion_engine import (
    extract_jd_rule_based,
    ingest_jd,
    jd_to_config_override,
)
from redrob_ranker.engines.gap_analysis_engine import (
    detect_skill_gaps,
    detect_experience_gaps,
    detect_behavioral_risks,
    analyze_candidate_gap,
)
from redrob_ranker.engines.resume_quality_engine import (
    check_completeness,
    detect_weak_areas,
    analyze_resume_quality,
)

# Mock resume text and schema for testing
MOCK_RESUME_TEXT = """
Jane Doe
Senior ML Engineer
jane.doe@example.com | +91 99999 88888
github.com/janedoe | linkedin.com/in/janedoe
Bangalore, India

Summary:
Senior Machine Learning Engineer with 6 years of experience building and deploying ranking systems.
Expert in Python, PyTorch, FAISS, and Elasticsearch.

Skills:
Python, PyTorch, FAISS, Elasticsearch, NLP, RAG, Docker
"""

def test_resume_rule_based_extraction():
    res = extract_fields_rule_based(MOCK_RESUME_TEXT)
    assert res["email"] == "jane.doe@example.com"
    assert res["phone"] == "+91 99999 88888"
    assert res["github_url"] == "https://github.com/janedoe"
    assert res["linkedin_url"] == "https://linkedin.com/in/janedoe"
    assert res["years_of_experience"] == 6
    assert "faiss" in res["extracted_skills"]
    assert "elasticsearch" in res["extracted_skills"]

def test_build_candidate_schema():
    raw_fields = {
        "email": "jane@doe.com",
        "phone": "123",
        "github_url": "git",
        "location": "Noida",
        "country": "India",
        "years_of_experience": 5,
        "extracted_skills": ["python", "faiss"],
    }
    llm_fields = {
        "name": "Jane Doe",
        "current_title": "Senior ML Engineer",
        "companies": ["Acme Corp", "Tech Corp"],
    }
    candidate = build_candidate_schema(raw_fields, llm_fields, "resume.pdf")
    assert candidate["profile"]["name"] == "Jane Doe"
    assert candidate["profile"]["current_title"] == "Senior ML Engineer"
    assert candidate["profile"]["email"] == "jane@doe.com"
    assert len(candidate["skills"]) == 2
    assert len(candidate["career_history"]) == 2
    assert candidate["source_file"] == "resume.pdf"

@patch("redrob_ranker.engines.resume_ingestion_engine._load_qwen")
@patch("redrob_ranker.engines.resume_ingestion_engine._qwen_extract")
def test_ingest_resume_no_llm(mock_extract, mock_load):
    mock_load.return_value = False
    candidate = ingest_resume(MOCK_RESUME_TEXT.encode("utf-8"), "resume.txt", use_llm=False)
    assert candidate["profile"]["email"] == "jane.doe@example.com"
    assert candidate["profile"]["years_of_experience"] == 6
    assert any(s["name"] == "faiss" for s in candidate["skills"])

def test_jd_rule_based_extraction():
    jd_text = """
    Job Title: Senior Search and Recommendation Engineer
    Location: Remote / Hybrid Noida
    Experience: 5 to 8 years
    Skills Required: FAISS, Elasticsearch, Python, PyTorch, BM25, RAG.
    """
    res = extract_jd_rule_based(jd_text)
    assert res["job_title"] == "Job Title: Senior Search and Recommendation Engineer"
    assert res["yoe_min"] == 5
    assert res["yoe_max"] == 8
    assert "faiss" in res["required_skills"]
    assert "elasticsearch" in res["required_skills"]

def test_jd_ingest_and_override():
    jd_text = """
    Senior Search Engineer
    Experience: 4+ years
    Required: Python, FAISS, Milvus.
    """
    jd = ingest_jd(text=jd_text, use_llm=False)
    assert jd["job_title"] == "Senior Search Engineer"
    assert "python" in jd["required_skills"]
    
    override = jd_to_config_override(jd)
    assert "python" in override["REQUIRED_SKILLS"]
    assert override["YOE_IDEAL_MIN"] == 4

def test_gap_analysis():
    candidate = {
        "profile": {
            "years_of_experience": 3,
            "country": "USA",
        },
        "skills": [
            {"name": "Python"},
            {"name": "PyTorch"},
        ],
        "career_history": [
            {"company": "TCS", "title": "Developer"}
        ],
        "redrob_signals": {
            "recruiter_response_rate": 0.1,
            "notice_period_days": 120,
            "open_to_work_flag": False,
        }
    }
    
    required_skills = {"python", "faiss"}
    nice_to_have = {"milvus"}
    
    # 1. Test skill gaps
    sg = detect_skill_gaps(candidate["skills"], required_skills, nice_to_have)
    assert sg["matched_required"] == ["python"]
    assert sg["missing_required"] == ["faiss"]
    assert sg["coverage_pct"] == 50.0
    
    # 2. Test experience gaps
    jd_cfg = {"yoe_min": 5, "yoe_max": 9, "product_company_preferred": True, "location": "India"}
    eg = detect_experience_gaps(candidate, jd_cfg)
    assert any("below minimum" in g for g in eg)
    assert any("services/consulting" in g for g in eg)
    
    # 3. Test behavioral risks
    br = detect_behavioral_risks(candidate)
    assert any("low recruiter response rate" in r for r in br)
    assert any("notice period" in r for r in br)
    assert any("Not actively open to work" in r for r in br)

def test_resume_quality():
    candidate = {
        "profile": {
            "summary": "Short",
            "current_title": "ML Eng",
            "location": "Noida",
            "email": "jane@doe.com",
        },
        "skills": [
            {"name": "Python", "proficiency": "beginner", "duration_months": 0}
        ],
        "career_history": [],
        "redrob_signals": {
            "profile_completeness_score": 30,
            "github_activity_score": -1,
        }
    }
    
    completeness, present, missing = check_completeness(candidate)
    assert "Work Experience" in [m.replace("❌ ", "").replace(" (required)", "") for m in missing]
    
    weak = detect_weak_areas(candidate)
    assert any("Summary is too short" in w for w in weak)
    assert any("skills missing duration" in w for w in weak)
    
    quality = analyze_resume_quality(candidate, use_llm=False)
    assert quality["quality_score"] < 50
    assert quality["quality_grade"] == "Needs Work"
