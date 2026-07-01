"""
jd_ingestion_engine.py — Module 15: JD Ingestion Engine
Supports: Text input, PDF upload, DOCX upload
Extracts structured JD requirements → auto-reruns ranking with new JD.
Uses Qwen 2.5 3B Instruct for intelligent field extraction.
"""
import io
import json
import logging
import re
from typing import Dict, List, Set, Optional

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# JD TEXT READERS (reuse resume reader helpers)
# ─────────────────────────────────────────────────────────────

def read_jd_file(file_bytes: bytes, filename: str) -> str:
    """Extract text from uploaded JD file."""
    from redrob_ranker.engines.resume_ingestion_engine import read_file_to_text
    return read_file_to_text(file_bytes, filename)


# ─────────────────────────────────────────────────────────────
# RULE-BASED JD EXTRACTION
# ─────────────────────────────────────────────────────────────

SENIORITY_PATTERNS = {
    "intern": r"\b(intern|internship|trainee|fresher)\b",
    "junior": r"\b(junior|jr\.|associate|entry.level|0.?2 years?)\b",
    "mid": r"\b(mid.level|intermediate|2.?5 years?)\b",
    "senior": r"\b(senior|sr\.|5.?\+|lead)\b",
    "principal": r"\b(principal|staff|architect|10.?\+)\b",
    "director": r"\b(director|vp|head of|chief)\b",
}

YOE_RANGE_RE = re.compile(
    r"(\d+)\s*(?:to|\-)\s*(\d+)\s*(?:years?|yrs?)", re.IGNORECASE
)
MIN_YOE_RE = re.compile(r"(\d+)\+?\s*(?:years?|yrs?)(?:\s*(?:of\s*)?(?:experience|exp))?", re.IGNORECASE)

SKILL_TERMS = {
    # Must-have for ML/IR
    "faiss", "elasticsearch", "opensearch", "milvus", "pinecone", "weaviate", "qdrant",
    "sentence-transformers", "bge", "e5", "embeddings", "dense retrieval", "bi-encoder",
    "learning to rank", "ltr", "lambdamart", "ndcg", "bm25", "information retrieval",
    "rag", "retrieval augmented generation", "hybrid search", "ann search", "hnsw",
    "pytorch", "tensorflow", "transformers", "bert", "llm", "fine-tuning", "lora",
    "lightgbm", "xgboost", "scikit-learn", "python", "numpy", "pandas", "spark",
    "nlp", "natural language processing", "recommendation system", "mlops",
    "vector search", "vector database", "text search", "reranking",
    # General
    "docker", "kubernetes", "aws", "gcp", "azure", "git", "sql", "postgresql",
    "fastapi", "flask", "django", "java", "scala", "go", "rust", "c++",
}

LOCATION_RE = re.compile(
    r"\b(Bangalore|Bengaluru|Hyderabad|Pune|Mumbai|Delhi|Noida|Gurgaon|Chennai|"
    r"India|Remote|Hybrid|San Francisco|New York|London|Singapore|Berlin)\b",
    re.IGNORECASE,
)

WORK_MODE_RE = re.compile(r"\b(remote|hybrid|on.?site|in.?office|work from home)\b", re.IGNORECASE)


def extract_jd_rule_based(text: str) -> Dict:
    """Fast rule-based layout-aware extraction from JD text."""
    lines = [l.strip() for l in text.split("\n")]
    
    sections = {}
    current_header = "intro"
    sections[current_header] = []
    
    for line in lines:
        if not line:
            continue
        # Match header line, e.g., # Requirements, ## Nice-to-Have
        header_match = re.match(r"^(#{1,6})\s+(.*)$", line)
        if header_match:
            current_header = header_match.group(2).lower().strip()
            # remove formatting characters like *, _, ` and normalize dashes to spaces
            current_header = re.sub(r"[\*\_`]", "", current_header)
            current_header = current_header.replace("-", " ")
            sections[current_header] = []
        else:
            sections[current_header].append(line)
            
    # Classify sections
    REQUIRED_KEYWORDS = ["require", "must have", "qualification", "what you need", "what we're looking for", "skills required", "essential"]
    PREFERRED_KEYWORDS = ["preferred", "nice to have", "plus", "bonus", "desired", "good to have", "advantages", "optional"]
    YOE_KEYWORDS = ["experience", "yoe", "background"]
    ROLE_KEYWORDS = ["role", "title", "position", "job description", "about the role"]
    LOCATION_KEYWORDS = ["location", "office", "where"]
    
    req_lines = []
    pref_lines = []
    yoe_lines = []
    role_lines = []
    loc_lines = []
    
    for h, sect_lines in sections.items():
        if any(kw in h for kw in PREFERRED_KEYWORDS):
            pref_lines.extend(sect_lines)
        elif any(kw in h for kw in REQUIRED_KEYWORDS):
            req_lines.extend(sect_lines)
        elif any(kw in h for kw in YOE_KEYWORDS):
            yoe_lines.extend(sect_lines)
            req_lines.extend(sect_lines)
        elif any(kw in h for kw in ROLE_KEYWORDS):
            role_lines.extend(sect_lines)
        elif any(kw in h for kw in LOCATION_KEYWORDS):
            loc_lines.extend(sect_lines)
            
    # Default to intro if required lines empty
    if not req_lines and "intro" in sections:
        req_lines.extend(sections["intro"])
        
    # Helper to parse skills from a list of lines
    def extract_skills_from_lines(target_lines: List[str]) -> List[str]:
        extracted = set()
        for line in target_lines:
            # clean bullet point markers
            clean = re.sub(r"^[\s\-\*\+\d\.\)]+\s*", "", line).strip()
            if not clean:
                continue
            
            # 1. Exact match of SKILL_TERMS
            line_lower = clean.lower()
            for term in SKILL_TERMS:
                pattern = r"\b" + re.escape(term) + r"\b"
                if re.search(pattern, line_lower):
                    extracted.add(term)
                    
            # 2. Also search for capitalized words/phrases of length 2-25 that might be skills (excluding common English stop words)
            cap_words = re.findall(r"\b[A-Z][a-zA-Z0-9\-\+\#\.]*\b", clean)
            for cw in cap_words:
                cw_lower = cw.lower()
                STOPWORDS = {"the", "a", "an", "and", "or", "but", "if", "then", "else", "when", "at", "by", "for", "with", "about", "against", "between", "into", "through", "during", "before", "after", "above", "below", "to", "from", "up", "down", "in", "out", "on", "off", "over", "under", "again", "further", "then", "once", "here", "there", "when", "where", "why", "how", "all", "any", "both", "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very", "s", "t", "can", "will", "just", "don", "should", "now"}
                if cw_lower not in STOPWORDS and len(cw_lower) > 1:
                    extracted.add(cw_lower)
                    
        return sorted(list(extracted))
        
    # Extract skills
    req_skills = extract_skills_from_lines(req_lines)
    pref_skills = extract_skills_from_lines(pref_lines)
    
    # Remove duplicates from preferred if they are in required
    pref_skills = [s for s in pref_skills if s not in req_skills]
    
    # ─────────────────────────────────────────────────────────────
    # Years of Experience (YOE)
    # ─────────────────────────────────────────────────────────────
    yoe_search_text = "\n".join(yoe_lines) if yoe_lines else ("\n".join(req_lines) if req_lines else text)
    
    yoe_min = 3
    yoe_max = 10
    
    range_match = YOE_RANGE_RE.search(yoe_search_text)
    if range_match:
        yoe_min = int(range_match.group(1))
        yoe_max = int(range_match.group(2))
    else:
        min_match = MIN_YOE_RE.search(yoe_search_text)
        if min_match:
            yoe_min = int(min_match.group(1))
            yoe_max = max(yoe_min + 5, int(yoe_min * 1.5))
            
    # ─────────────────────────────────────────────────────────────
    # Job Title
    # ─────────────────────────────────────────────────────────────
    job_title = "Unknown Role"
    first_h1 = None
    for line in lines:
        m = re.match(r"^#\s+(.*)$", line)
        if m:
            first_h1 = m.group(1).strip()
            break
    if first_h1:
        job_title = first_h1
    elif role_lines:
        job_title = role_lines[0]
    else:
        for line in lines:
            if line and not line.startswith("#"):
                job_title = line
                break
    job_title = re.sub(r"[\*\_`]", "", job_title)
    
    # ─────────────────────────────────────────────────────────────
    # Location and Work Mode
    # ─────────────────────────────────────────────────────────────
    loc_search_text = "\n".join(loc_lines) if loc_lines else text
    location = "India"
    loc_match = LOCATION_RE.search(loc_search_text)
    if loc_match:
        location = loc_match.group(1).title()
        
    work_mode = "hybrid"
    wm_match = WORK_MODE_RE.search(loc_search_text)
    if wm_match:
        work_mode = wm_match.group(1).lower()
        if "remote" in work_mode:
            work_mode = "remote"
        elif "hybrid" in work_mode:
            work_mode = "hybrid"
        else:
            work_mode = "onsite"
            
    seniority = "senior"
    for level, pattern in SENIORITY_PATTERNS.items():
        if re.search(pattern, job_title, re.IGNORECASE) or re.search(pattern, text, re.IGNORECASE):
            seniority = level
            break
            
    return {
        "job_title": job_title,
        "seniority": seniority,
        "yoe_min": yoe_min,
        "yoe_max": yoe_max,
        "required_skills": req_skills,
        "nice_to_have_skills": pref_skills,
        "location": location,
        "work_mode": work_mode
    }


# ─────────────────────────────────────────────────────────────
# LLM-BASED JD EXTRACTION — Qwen 2.5 3B
# ─────────────────────────────────────────────────────────────

JD_EXTRACTION_PROMPT = """Extract structured job requirements from this job description and return as JSON:
{
  "job_title": "exact job title",
  "seniority": "junior|mid|senior|principal|director",
  "required_skills": ["skill1", "skill2", ...],
  "nice_to_have_skills": ["skill1", ...],
  "years_of_experience_min": number,
  "years_of_experience_max": number,
  "location": "city, country or Remote",
  "work_mode": "remote|hybrid|onsite",
  "product_company_preferred": true/false,
  "key_responsibilities": ["responsibility1", ...],
  "disqualifiers": ["anything that would disqualify a candidate"]
}
Return ONLY the JSON."""


def extract_jd_with_llm(text: str) -> Dict:
    """Use Qwen 2.5 3B to extract structured JD fields."""
    try:
        from redrob_ranker.engines.resume_ingestion_engine import _qwen_extract
        llm_output = _qwen_extract(text, JD_EXTRACTION_PROMPT, max_new_tokens=600)
        if llm_output:
            clean = re.sub(r"```(?:json)?|```", "", llm_output).strip()
            return json.loads(clean)
    except Exception as e:
        logger.warning(f"LLM JD extraction failed: {e}")
    return {}


# ─────────────────────────────────────────────────────────────
# UNIFIED JD SCHEMA
# ─────────────────────────────────────────────────────────────

def ingest_jd(text: str = "", file_bytes: bytes = None, filename: str = "", use_llm: bool = True) -> Dict:
    """
    Parse a job description from text or file.
    Returns structured JD requirements dict.
    """
    if file_bytes and filename:
        text = read_jd_file(file_bytes, filename)

    if not text.strip():
        return {}

    # Rule-based extraction
    rule_fields = extract_jd_rule_based(text)

    # LLM extraction
    llm_fields = {}
    if use_llm:
        llm_fields = extract_jd_with_llm(text)

    # Merge (LLM takes precedence)
    merged = {**rule_fields, **{k: v for k, v in llm_fields.items() if v}}

    # Build unified JD schema
    all_skills = list(set(
        rule_fields.get("required_skills", [])
        + llm_fields.get("required_skills", [])
    ))

    jd = {
        "job_title": merged.get("job_title", "Unknown Role"),
        "seniority": merged.get("seniority", "senior"),
        "required_skills": all_skills,
        "nice_to_have_skills": merged.get("nice_to_have_skills", []),
        "years_of_experience_min": merged.get("yoe_min", merged.get("years_of_experience_min", 3)),
        "years_of_experience_max": merged.get("yoe_max", merged.get("years_of_experience_max", 10)),
        "location": merged.get("location", "India"),
        "work_mode": merged.get("work_mode", "hybrid"),
        "product_company_preferred": merged.get("product_company_preferred", True),
        "key_responsibilities": merged.get("key_responsibilities", []),
        "disqualifiers": merged.get("disqualifiers", []),
        "raw_text": text[:2000],
    }

    logger.info(f"JD parsed: {jd['job_title']} | {len(all_skills)} skills | {jd['seniority']}")
    return jd


def jd_to_config_override(jd: Dict) -> Dict:
    """
    Convert parsed JD into config overrides for the ranking engine.
    Allows dynamic re-ranking with a new JD without code changes.
    """
    required_skills_set = set(s.lower().strip() for s in jd.get("required_skills", []))
    yoe_min = jd.get("years_of_experience_min", 3)
    yoe_max = jd.get("years_of_experience_max", 10)
    yoe_ideal = (yoe_min + yoe_max) / 2

    return {
        "REQUIRED_SKILLS": required_skills_set,
        "PREFERRED_SKILLS": set(s.lower().strip() for s in jd.get("nice_to_have_skills", [])),
        "YOE_IDEAL_MIN": yoe_min,
        "YOE_IDEAL_MAX": yoe_max,
        "YOE_IDEAL_MID": yoe_ideal,
        "JD_TITLE": jd.get("job_title", ""),
        "JD_LOCATION": jd.get("location", "India"),
        "JD_WORK_MODE": jd.get("work_mode", "hybrid"),
        "PRODUCT_COMPANY_REQUIRED": jd.get("product_company_preferred", True),
    }
