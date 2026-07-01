"""
data_ingestion.py — Multi-Format candidate ingestion
Supports: streaming .jsonl, gzipped .jsonl.gz, standard .json array, .csv, .xlsx, and .zip archives.
Provides dynamic key synonym mapper.
"""
import csv
import gzip
import io
import json
import logging
import zipfile
from pathlib import Path
from typing import Dict, Iterator, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)

def map_dynamic_candidate(raw: dict) -> dict:
    """
    Maps dynamic raw dictionary keys to the standard internal candidate schema.
    Tolerates missing elements, field name variations, and sub-field layouts.
    """
    mapped = {}
    
    # 1. Candidate ID
    cid = None
    for k in ["candidate_id", "id", "cid", "candidateId"]:
        if k in raw:
            cid = str(raw[k])
            break
    if not cid:
        cid = "CAND_0000000"
    mapped["candidate_id"] = cid
    
    # 2. Profile
    profile = {}
    profile_raw = None
    for k in ["profile", "bio", "personal", "personal_info"]:
        if k in raw and isinstance(raw[k], dict):
            profile_raw = raw[k]
            break
            
    if profile_raw:
        profile["anonymized_name"] = profile_raw.get("anonymized_name", profile_raw.get("name", "Unknown Candidate"))
        profile["headline"] = profile_raw.get("headline", profile_raw.get("title", ""))
        profile["summary"] = profile_raw.get("summary", profile_raw.get("about", ""))
        profile["location"] = profile_raw.get("location", profile_raw.get("city", "India"))
        profile["country"] = profile_raw.get("country", "India")
        
        yoe = profile_raw.get("years_of_experience", profile_raw.get("experience", profile_raw.get("yoe", 5.0)))
        profile["years_of_experience"] = float(yoe) if yoe is not None else 5.0
        
        profile["current_title"] = profile_raw.get("current_title", profile_raw.get("job_title", ""))
        profile["current_company"] = profile_raw.get("current_company", profile_raw.get("company", ""))
        profile["current_company_size"] = profile_raw.get("current_company_size", profile_raw.get("company_size", "51-200"))
        profile["current_industry"] = profile_raw.get("current_industry", profile_raw.get("industry", "IT"))
    else:
        # Fallback to direct root elements
        profile["anonymized_name"] = raw.get("name", raw.get("anonymized_name", "Unknown Candidate"))
        profile["headline"] = raw.get("headline", raw.get("title", ""))
        profile["summary"] = raw.get("summary", raw.get("about", ""))
        profile["location"] = raw.get("location", raw.get("city", "India"))
        profile["country"] = raw.get("country", "India")
        
        yoe = raw.get("years_of_experience", raw.get("experience", raw.get("yoe", 5.0)))
        profile["years_of_experience"] = float(yoe) if yoe is not None else 5.0
        
        profile["current_title"] = raw.get("current_title", raw.get("job_title", ""))
        profile["current_company"] = raw.get("current_company", raw.get("company", ""))
        profile["current_company_size"] = raw.get("current_company_size", raw.get("company_size", "51-200"))
        profile["current_industry"] = raw.get("current_industry", raw.get("industry", "IT"))
        
    mapped["profile"] = profile
    
    # 3. Career History
    career = []
    career_raw = None
    for k in ["career_history", "career", "work_history", "experience_history", "jobs", "employment"]:
        if k in raw and isinstance(raw[k], list):
            career_raw = raw[k]
            break
    if not career_raw and "experience" in raw and isinstance(raw["experience"], list):
        career_raw = raw["experience"]
            
    if career_raw:
        for job in career_raw:
            if isinstance(job, dict):
                job_mapped = {
                    "company": job.get("company", job.get("employer", "")),
                    "title": job.get("title", job.get("role", "")),
                    "start_date": job.get("start_date", job.get("start", "2020-01-01")),
                    "end_date": job.get("end_date", job.get("end", None)),
                    "duration_months": int(job.get("duration_months", job.get("duration", 12))),
                    "is_current": bool(job.get("is_current", job.get("current", False))),
                    "industry": job.get("industry", "Technology"),
                    "company_size": job.get("company_size", "51-200"),
                    "description": job.get("description", job.get("duties", ""))
                }
                career.append(job_mapped)
    mapped["career_history"] = career
    
    # 4. Education
    education = []
    edu_raw = None
    for k in ["education", "academic", "studies", "degrees"]:
        if k in raw and isinstance(raw[k], list):
            edu_raw = raw[k]
            break
    if edu_raw:
        for edu in edu_raw:
            if isinstance(edu, dict):
                edu_mapped = {
                    "institution": edu.get("institution", edu.get("school", edu.get("university", ""))),
                    "degree": edu.get("degree", ""),
                    "field_of_study": edu.get("field_of_study", edu.get("field", edu.get("major", ""))),
                    "start_year": int(edu.get("start_year", edu.get("start", 2015))),
                    "end_year": int(edu.get("end_year", edu.get("end", 2019))),
                    "grade": edu.get("grade", edu.get("gpa", None)),
                    "tier": edu.get("tier", "unknown")
                }
                education.append(edu_mapped)
    mapped["education"] = education
    
    # 5. Skills
    skills = []
    skills_raw = None
    for k in ["skills", "technologies", "expertise"]:
        if k in raw and isinstance(raw[k], list):
            skills_raw = raw[k]
            break
    if skills_raw:
        for s in skills_raw:
            if isinstance(s, dict):
                s_mapped = {
                    "name": s.get("name", s.get("skill", "")),
                    "proficiency": s.get("proficiency", s.get("level", "intermediate")).lower(),
                    "endorsements": int(s.get("endorsements", s.get("count", 0))),
                    "duration_months": int(s.get("duration_months", s.get("duration", 0)))
                }
                skills.append(s_mapped)
            elif isinstance(s, str):
                skills.append({
                    "name": s,
                    "proficiency": "intermediate",
                    "endorsements": 5,
                    "duration_months": 24
                })
    mapped["skills"] = skills
    
    # 6. Redrob Signals
    signals = {}
    signals_raw = None
    for k in ["redrob_signals", "signals", "behavioral", "activity_metrics"]:
        if k in raw and isinstance(raw[k], dict):
            signals_raw = raw[k]
            break
            
    if signals_raw:
        signals["profile_completeness_score"] = float(signals_raw.get("profile_completeness_score", 80.0))
        signals["signup_date"] = signals_raw.get("signup_date", "2024-01-01")
        signals["last_active_date"] = signals_raw.get("last_active_date", "2026-06-20")
        signals["open_to_work_flag"] = bool(signals_raw.get("open_to_work_flag", True))
        signals["profile_views_received_30d"] = int(signals_raw.get("profile_views_received_30d", 10))
        signals["applications_submitted_30d"] = int(signals_raw.get("applications_submitted_30d", 5))
        signals["recruiter_response_rate"] = float(signals_raw.get("recruiter_response_rate", 0.70))
        signals["avg_response_time_hours"] = float(signals_raw.get("avg_response_time_hours", 24.0))
        signals["skill_assessment_scores"] = signals_raw.get("skill_assessment_scores", {})
        signals["connection_count"] = int(signals_raw.get("connection_count", 100))
        signals["endorsements_received"] = int(signals_raw.get("endorsements_received", 10))
        signals["notice_period_days"] = int(signals_raw.get("notice_period_days", 30))
        signals["expected_salary_range_inr_lpa"] = signals_raw.get("expected_salary_range_inr_lpa", {"min": 15, "max": 30})
        signals["preferred_work_mode"] = signals_raw.get("preferred_work_mode", "hybrid")
        signals["willing_to_relocate"] = bool(signals_raw.get("willing_to_relocate", True))
        signals["github_activity_score"] = float(signals_raw.get("github_activity_score", 0.0))
        signals["search_appearance_30d"] = int(signals_raw.get("search_appearance_30d", 50))
        signals["saved_by_recruiters_30d"] = int(signals_raw.get("saved_by_recruiters_30d", 5))
        signals["interview_completion_rate"] = float(signals_raw.get("interview_completion_rate", 0.90))
        signals["offer_acceptance_rate"] = float(signals_raw.get("offer_acceptance_rate", 0.80))
        signals["verified_email"] = bool(signals_raw.get("verified_email", True))
        signals["verified_phone"] = bool(signals_raw.get("verified_phone", True))
        signals["linkedin_connected"] = bool(signals_raw.get("linkedin_connected", True))
    else:
        # Default mock signals
        signals = {
            "profile_completeness_score": 85.0,
            "signup_date": "2024-01-01",
            "last_active_date": "2026-06-20",
            "open_to_work_flag": True,
            "profile_views_received_30d": 15,
            "applications_submitted_30d": 5,
            "recruiter_response_rate": 0.80,
            "avg_response_time_hours": 12.0,
            "skill_assessment_scores": {},
            "connection_count": 250,
            "endorsements_received": 15,
            "notice_period_days": 30,
            "expected_salary_range_inr_lpa": {"min": 25, "max": 45},
            "preferred_work_mode": "hybrid",
            "willing_to_relocate": True,
            "github_activity_score": 50.0,
            "search_appearance_30d": 80,
            "saved_by_recruiters_30d": 8,
            "interview_completion_rate": 0.95,
            "offer_acceptance_rate": 0.85,
            "verified_email": True,
            "verified_phone": True,
            "linkedin_connected": True
        }
    mapped["redrob_signals"] = signals
    
    mapped["certifications"] = raw.get("certifications", [])
    mapped["languages"] = raw.get("languages", [])
    
    return mapped

def parse_tabular_candidate(row: dict) -> dict:
    """Converts a flat row dictionary (from CSV/XLSX) to candidate JSON representation."""
    raw = {}
    
    # Candidate ID
    raw["candidate_id"] = str(row.get("candidate_id", row.get("id", ""))).strip()
    
    # Profile
    raw["profile"] = {
        "anonymized_name": str(row.get("name", row.get("anonymized_name", "Unknown"))),
        "headline": str(row.get("headline", "")),
        "summary": str(row.get("summary", "")),
        "location": str(row.get("location", "India")),
        "country": str(row.get("country", "India")),
        "years_of_experience": float(row.get("years_of_experience", row.get("experience", row.get("yoe", 5)))),
        "current_title": str(row.get("current_title", row.get("title", ""))),
        "current_company": str(row.get("current_company", row.get("company", ""))),
        "current_company_size": str(row.get("current_company_size", "51-200")),
        "current_industry": str(row.get("current_industry", ""))
    }
    
    # Skills
    skills = []
    skills_raw = str(row.get("skills", row.get("extracted_skills", ""))).split(",")
    for s in skills_raw:
        s = s.strip()
        if s:
            skills.append({
                "name": s,
                "proficiency": "intermediate",
                "endorsements": 5,
                "duration_months": 24
            })
    raw["skills"] = skills
    
    # Empty default lists
    raw["career_history"] = []
    raw["education"] = []
    raw["redrob_signals"] = {}
    
    return map_dynamic_candidate(raw)

def stream_candidates_from_bytes(file_bytes: bytes, filename: str) -> Iterator[dict]:
    """
    Streams parsed candidate dicts from uploaded bytes dynamically based on format.
    Does not load the full file in memory for line streams.
    """
    fn_lower = filename.lower()
    
    if fn_lower.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
            for zip_fn in z.namelist():
                if zip_fn.lower().endswith((".jsonl", ".jsonl.gz", ".json", ".csv", ".xlsx")):
                    inner_bytes = z.read(zip_fn)
                    yield from stream_candidates_from_bytes(inner_bytes, zip_fn)
                    return
        return

    if fn_lower.endswith(".gz"):
        with gzip.GzipFile(fileobj=io.BytesIO(file_bytes), mode="rb") as f:
            for line_bytes in f:
                line = line_bytes.decode("utf-8", errors="replace").strip()
                if line:
                    try:
                        raw = json.loads(line)
                        yield map_dynamic_candidate(raw)
                    except Exception:
                        pass
        return

    if fn_lower.endswith(".jsonl"):
        bio = io.BytesIO(file_bytes)
        for line_bytes in bio:
            line = line_bytes.decode("utf-8", errors="replace").strip()
            if line:
                try:
                    raw = json.loads(line)
                    yield map_dynamic_candidate(raw)
                except Exception:
                    pass
        return

    if fn_lower.endswith(".json"):
        # For standard json, load it as array of objects
        try:
            data = json.loads(file_bytes.decode("utf-8", errors="replace"))
            if isinstance(data, list):
                for item in data:
                    yield map_dynamic_candidate(item)
            elif isinstance(data, dict):
                # single object wrap
                yield map_dynamic_candidate(data)
        except Exception as e:
            logger.warning(f"Failed to parse JSON file {filename}: {e}")
        return

    if fn_lower.endswith(".csv"):
        # Parse CSV
        text = file_bytes.decode("utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            yield parse_tabular_candidate(row)
        return

    if fn_lower.endswith((".xlsx", ".xls")):
        # Parse Excel using pandas
        df = pd.read_excel(io.BytesIO(file_bytes))
        for _, row in df.iterrows():
            yield parse_tabular_candidate(row.to_dict())
        return
