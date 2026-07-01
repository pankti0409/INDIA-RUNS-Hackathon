"""
resume_ingestion_engine.py — Module 14: Multi-Format Resume Ingestion Engine
Supports: PDF, DOCX, TXT, CSV, XLSX, JSON, JSONL
Parses and normalizes into the unified candidate schema.
Uses Qwen 2.5 3B Instruct for intelligent field extraction from unstructured text.
"""
import csv
import io
import json
import logging
import re
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# FORMAT READERS — raw text extraction
# ─────────────────────────────────────────────────────────────

def read_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF using pdfplumber."""
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    except ImportError:
        logger.warning("pdfplumber not installed — PDF support unavailable")
        return ""
    except Exception as e:
        logger.error(f"PDF read error: {e}")
        return ""


def read_docx(file_bytes: bytes) -> str:
    """Extract text from DOCX using python-docx."""
    try:
        from docx import Document
        doc = Document(io.BytesIO(file_bytes))
        return "\n".join(p.text for p in doc.paragraphs)
    except ImportError:
        logger.warning("python-docx not installed")
        return ""
    except Exception as e:
        logger.error(f"DOCX read error: {e}")
        return ""


def read_xlsx(file_bytes: bytes) -> str:
    """Extract text from XLSX using openpyxl."""
    try:
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
        lines = []
        for ws in wb.worksheets:
            for row in ws.iter_rows(values_only=True):
                row_str = " | ".join(str(c) for c in row if c is not None)
                if row_str.strip():
                    lines.append(row_str)
        return "\n".join(lines)
    except ImportError:
        logger.warning("openpyxl not installed")
        return ""
    except Exception as e:
        logger.error(f"XLSX read error: {e}")
        return ""


def read_csv_text(file_bytes: bytes) -> str:
    """Extract text from CSV."""
    try:
        text = file_bytes.decode("utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        lines = []
        for row in reader:
            lines.append(" | ".join(f"{k}: {v}" for k, v in row.items() if v))
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"CSV read error: {e}")
        return ""


def read_file_to_text(file_bytes: bytes, filename: str) -> str:
    """Dispatch to appropriate reader based on file extension."""
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return read_pdf(file_bytes)
    elif ext == ".docx":
        return read_docx(file_bytes)
    elif ext in (".xlsx", ".xls"):
        return read_xlsx(file_bytes)
    elif ext == ".csv":
        return read_csv_text(file_bytes)
    elif ext in (".txt", ".md"):
        return file_bytes.decode("utf-8", errors="replace")
    elif ext == ".json":
        try:
            data = json.loads(file_bytes.decode("utf-8", errors="replace"))
            return json.dumps(data, indent=2)
        except Exception:
            return file_bytes.decode("utf-8", errors="replace")
    elif ext == ".jsonl":
        lines = file_bytes.decode("utf-8", errors="replace").strip().split("\n")
        return "\n".join(lines[:10])  # First 10 records for preview
    else:
        return file_bytes.decode("utf-8", errors="replace")


# ─────────────────────────────────────────────────────────────
# RULE-BASED EXTRACTION (fast, no LLM)
# ─────────────────────────────────────────────────────────────

SKILL_KEYWORDS = {
    "python", "pytorch", "tensorflow", "faiss", "elasticsearch", "opensearch",
    "sentence-transformers", "transformers", "huggingface", "nlp", "llm", "rag",
    "vector search", "milvus", "pinecone", "weaviate", "qdrant", "bm25",
    "learning to rank", "lightgbm", "xgboost", "scikit-learn", "numpy", "pandas",
    "fastapi", "docker", "kubernetes", "mlops", "spark", "hadoop", "kafka",
    "recommendation system", "ranking", "retrieval", "embeddings", "fine-tuning",
    "bert", "gpt", "llama", "lora", "peft", "cuda", "deep learning",
    "machine learning", "data science", "sql", "postgresql", "mongodb",
    "aws", "gcp", "azure", "git", "java", "scala", "rust", "go", "c++",
}

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"(\+?\d[\d\s\-().]{7,14}\d)")
GITHUB_RE = re.compile(r"github\.com/([a-zA-Z0-9\-]+)", re.IGNORECASE)
LINKEDIN_RE = re.compile(r"linkedin\.com/in/([a-zA-Z0-9\-]+)", re.IGNORECASE)
YOE_RE = re.compile(r"(\d+)\s*\+?\s*(?:years?|yrs?)\s*(?:of\s*)?(?:experience|exp)", re.IGNORECASE)
LOCATION_RE = re.compile(
    r"\b(Bangalore|Bengaluru|Hyderabad|Pune|Mumbai|Delhi|Noida|Gurgaon|Chennai|Kolkata|"
    r"India|UK|USA|Singapore|Germany|Canada|Australia)\b",
    re.IGNORECASE,
)


def extract_fields_rule_based(text: str) -> Dict[str, Any]:
    """
    Fast rule-based extraction. Returns partial candidate schema.
    LLM extraction supplements this for fields it can't find.
    """
    result: Dict[str, Any] = {}

    # Email
    emails = EMAIL_RE.findall(text)
    if emails:
        result["email"] = emails[0]

    # Phone
    phones = PHONE_RE.findall(text)
    if phones:
        result["phone"] = phones[0].strip()

    # GitHub
    github = GITHUB_RE.search(text)
    if github:
        result["github_url"] = f"https://github.com/{github.group(1)}"

    # LinkedIn
    linkedin = LINKEDIN_RE.search(text)
    if linkedin:
        result["linkedin_url"] = f"https://linkedin.com/in/{linkedin.group(1)}"

    # Years of experience
    yoe_matches = YOE_RE.findall(text)
    if yoe_matches:
        result["years_of_experience"] = max(int(y) for y in yoe_matches)

    # Location
    locations = LOCATION_RE.findall(text)
    if locations:
        result["location"] = locations[0]
        result["country"] = "India" if any(
            loc in locations for loc in [
                "Bangalore", "Bengaluru", "Hyderabad", "Pune", "Mumbai",
                "Delhi", "Noida", "Gurgaon", "Chennai", "Kolkata", "India"
            ]
        ) else locations[0]

    # Skills (keyword match)
    text_lower = text.lower()
    matched_skills = [sk for sk in SKILL_KEYWORDS if sk in text_lower]
    result["extracted_skills"] = matched_skills

    return result


# ─────────────────────────────────────────────────────────────
# LLM EXTRACTION — Qwen 2.5 3B Instruct
# ─────────────────────────────────────────────────────────────

_qwen_model = None
_qwen_tokenizer = None
_qwen_loaded = False


def _load_qwen():
    """Load Qwen 2.5 3B Instruct with graceful fallback."""
    global _qwen_model, _qwen_tokenizer, _qwen_loaded
    if _qwen_loaded:
        return _qwen_model is not None

    _qwen_loaded = True
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        import torch

        model_name = "Qwen/Qwen2.5-3B-Instruct"
        logger.info(f"Loading {model_name}...")

        _qwen_tokenizer = AutoTokenizer.from_pretrained(model_name)
        _qwen_model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float32,  # CPU-safe
            device_map="cpu",
        )
        logger.info("Qwen 2.5 3B loaded.")
        return True
    except Exception as e:
        logger.warning(f"Qwen not available ({e}) — using rule-based extraction only")
        return False


def _qwen_extract(text: str, task_prompt: str, max_new_tokens: int = 512) -> str:
    """Run Qwen inference for structured extraction."""
    if not _load_qwen():
        return ""

    import torch
    messages = [
        {"role": "system", "content": "You are an expert resume parser. Extract structured information from resumes and return valid JSON only. No markdown, no explanation."},
        {"role": "user", "content": f"{task_prompt}\n\nResume Text:\n{text[:3000]}"},
    ]

    try:
        text_input = _qwen_tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = _qwen_tokenizer([text_input], return_tensors="pt")
        with torch.no_grad():
            outputs = _qwen_model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                temperature=None,
                top_p=None,
                pad_token_id=_qwen_tokenizer.eos_token_id,
            )
        generated = outputs[0][inputs["input_ids"].shape[1]:]
        return _qwen_tokenizer.decode(generated, skip_special_tokens=True).strip()
    except Exception as e:
        logger.error(f"Qwen inference failed: {e}")
        return ""


EXTRACTION_PROMPT = """Extract the following fields from this resume and return as JSON:
{
  "name": "full name",
  "current_title": "current job title",
  "summary": "2-3 sentence professional summary",
  "skills": ["skill1", "skill2", ...],
  "years_of_experience": number,
  "education": [{"degree": "", "institution": "", "year": 0}],
  "companies": ["company1", "company2"],
  "location": "city, country",
  "github_url": "url or null",
  "linkedin_url": "url or null"
}
Return ONLY the JSON, no other text."""


# ─────────────────────────────────────────────────────────────
# UNIFIED SCHEMA BUILDER
# ─────────────────────────────────────────────────────────────

def build_candidate_schema(
    raw_fields: Dict,
    llm_fields: Dict,
    source_filename: str,
) -> Dict:
    """
    Merge rule-based + LLM fields into unified candidate schema.
    LLM fields take precedence where available.
    """
    merged = {**raw_fields, **{k: v for k, v in llm_fields.items() if v}}

    candidate_id = f"IMPORT_{uuid.uuid4().hex[:8].upper()}"

    # Build skills list
    skills_raw = merged.get("skills", merged.get("extracted_skills", []))
    skills = [
        {"name": s, "proficiency": "intermediate", "endorsements": 0, "duration_months": 12}
        for s in (skills_raw if isinstance(skills_raw, list) else [])
    ]

    # Education
    education_raw = merged.get("education", [])
    education = []
    if isinstance(education_raw, list):
        for edu in education_raw:
            if isinstance(edu, dict):
                education.append({
                    "degree": edu.get("degree", ""),
                    "institution": edu.get("institution", ""),
                    "tier": "tier_2",
                    "field_of_study": "computer science",
                    "year": edu.get("year", 2020),
                })

    return {
        "candidate_id": candidate_id,
        "source_file": source_filename,
        "profile": {
            "name": merged.get("name", "Unknown"),
            "current_title": merged.get("current_title", ""),
            "headline": merged.get("current_title", ""),
            "summary": merged.get("summary", ""),
            "years_of_experience": merged.get("years_of_experience", 0),
            "location": merged.get("location", ""),
            "country": merged.get("country", ""),
            "email": merged.get("email", ""),
            "phone": merged.get("phone", ""),
            "github_url": merged.get("github_url", ""),
            "linkedin_url": merged.get("linkedin_url", ""),
            "current_company_size": "",
        },
        "skills": skills,
        "career_history": [
            {
                "title": merged.get("current_title", ""),
                "company": c,
                "duration_months": max(12, int(merged.get("years_of_experience", 1) * 12 / max(1, len(merged.get("companies", ["Unknown"]))))),
                "start_date": "2020-01-01",
                "end_date": None,
                "industry": "technology",
                "description": "",
            }
            for c in merged.get("companies", ["Unknown Company"])
        ],
        "education": education,
        "certifications": [],
        "languages": [{"language": "English", "proficiency": "professional"}],
        "redrob_signals": {
            "open_to_work_flag": True,
            "last_active_date": "2026-06-22",
            "notice_period_days": 30,
            "recruiter_response_rate": 0.5,
            "avg_response_time_hours": 24,
            "profile_completeness_score": 60,
            "verified_email": bool(merged.get("email")),
            "verified_phone": bool(merged.get("phone")),
            "linkedin_connected": bool(merged.get("linkedin_url")),
            "github_activity_score": 50 if merged.get("github_url") else -1,
            "connection_count": 200,
            "endorsements_received": 10,
            "applications_submitted_30d": 3,
            "profile_views_received_30d": 15,
            "saved_by_recruiters_30d": 2,
            "search_appearance_30d": 50,
            "interview_completion_rate": 0.7,
            "offer_acceptance_rate": -1,
            "skill_assessment_scores": {},
            "willing_to_relocate": True,
            "preferred_work_mode": "hybrid",
            "expected_salary_range_inr_lpa": {"min": 30, "max": 50},
        },
    }


def ingest_resume(file_bytes: bytes, filename: str, use_llm: bool = True) -> Dict:
    """
    Full pipeline: bytes → text → rule-based fields → LLM fields → schema.
    Returns unified candidate dict ready for ranking.
    """
    # Step 1: Extract raw text
    text = read_file_to_text(file_bytes, filename)
    if not text.strip():
        logger.warning(f"No text extracted from {filename}")
        return {}

    # Step 2: Rule-based extraction (fast)
    raw_fields = extract_fields_rule_based(text)

    # Step 3: LLM extraction (Qwen 2.5 3B)
    llm_fields = {}
    if use_llm:
        llm_output = _qwen_extract(text, EXTRACTION_PROMPT)
        if llm_output:
            try:
                # Strip any markdown code blocks
                clean = re.sub(r"```(?:json)?|```", "", llm_output).strip()
                llm_fields = json.loads(clean)
            except json.JSONDecodeError:
                logger.warning(f"LLM output not valid JSON: {llm_output[:200]}")

    # Step 4: Build unified schema
    candidate = build_candidate_schema(raw_fields, llm_fields, filename)
    logger.info(f"Ingested resume: {filename} → {candidate['candidate_id']}")
    return candidate


def ingest_multiple(files: List[Dict]) -> List[Dict]:
    """
    Ingest multiple resumes.
    files: list of {"bytes": bytes, "filename": str}
    Returns list of candidate dicts.
    """
    results = []
    for f in files:
        try:
            c = ingest_resume(f["bytes"], f["filename"])
            if c:
                results.append(c)
        except Exception as e:
            logger.error(f"Failed to ingest {f.get('filename', '?')}: {e}")
    return results
