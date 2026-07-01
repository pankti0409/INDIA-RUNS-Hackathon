import sys
import os
import json
import pytest
import gzip
import zipfile
import io

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from redrob_ranker.utils.file_detector import detect_file_type, profile_file_metadata

def test_detect_empty_file():
    result = detect_file_type(b"", "test.json")
    assert result["type"] == "Unknown File"
    assert "empty" in result["error"].lower()

def test_detect_candidate_dataset_json():
    candidate = {
        "candidate_id": "CAND_001",
        "profile": {
            "name": "John Doe",
            "years_of_experience": 5
        },
        "skills": [{"name": "Python"}]
    }
    content = json.dumps([candidate]).encode("utf-8")
    result = detect_file_type(content, "candidates.json")
    assert result["type"] == "Candidate Dataset"

def test_detect_candidate_dataset_jsonl():
    candidate = {
        "candidate_id": "CAND_001",
        "profile": {"name": "John Doe"}
    }
    content = (json.dumps(candidate) + "\n").encode("utf-8")
    result = detect_file_type(content, "candidates.jsonl")
    assert result["type"] == "Candidate Dataset"

def test_detect_schema_definition():
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "properties": {
            "candidate_id": {"type": "string"}
        }
    }
    content = json.dumps(schema).encode("utf-8")
    result = detect_file_type(content, "schema.json")
    assert result["type"] == "Schema Definition"

def test_detect_job_description():
    jd = "Job Description:\nWe are looking for a Software Developer.\nRequirements:\n- Python\n- Responsibilities:\nCoding and testing."
    content = jd.encode("utf-8")
    result = detect_file_type(content, "jd.md")
    assert result["type"] == "Job Description"

def test_detect_corrupted_gzip():
    content = b"corrupted data"
    result = detect_file_type(content, "candidates.jsonl.gz")
    assert "gzip" in result["error"].lower()

def test_detect_corrupted_zip():
    content = b"corrupted data"
    result = detect_file_type(content, "candidates.zip")
    assert "zip" in result["error"].lower()
