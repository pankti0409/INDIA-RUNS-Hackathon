"""
feature_engine.py — Extract ranking features per candidate
All features normalized to [0, 1] range.
Implements: Priority 1 (Role-Specific Candidate Intelligence), Priority 5 (Trust Engine), Priority 8 (Remove Step Functions).
"""
import logging
import math
import re
from datetime import datetime
from typing import Dict, List, Set, Tuple

from redrob_ranker.config import (
    CONSULTING_COMPANIES,
    DEGREE_SCORES,
    DISQUALIFIER_TITLES,
    EDUCATION_TIER_SCORES,
    IDEAL_TITLES,
    LOCATION_SCORES,
    NON_AI_SKILLS,
    PREFERRED_CITIES,
    PREFERRED_COUNTRY,
    PREFERRED_SKILLS,
    PROFICIENCY_SCORES,
    REFERENCE_DATE_STR,
    RELEVANT_FIELDS,
    REQUIRED_SKILLS,
    ROLE_TIER_SCORES,
    SKILL_NORMALIZE,
)
from redrob_ranker.engines.behavioral_engine import compute_all_behavioral_scores
from redrob_ranker.engines.honeypot_engine import detect_honeypot
from redrob_ranker.engines.career_engine import compute_all_career_scores
from redrob_ranker.engines.skill_ontology import (
    compute_ontology_skill_score,
    get_skill_family,
)
from redrob_ranker.engines.candidate_intelligence_engine import build_candidate_intelligence
from redrob_ranker.engines.company_intelligence_engine import compute_company_intelligence
from redrob_ranker.engines.skill_graph import (
    compute_skill_set_coverage,
    compute_domain_coverage,
)

logger = logging.getLogger(__name__)

REFERENCE_DATE = datetime.strptime(REFERENCE_DATE_STR, "%Y-%m-%d")

# Priority 1: Keywords mapping for 8 role-specific candidate intelligence dimensions
DIMENSION_KEYWORDS = {
    "vector_search": {"faiss", "hnsw", "milvus", "pinecone", "weaviate", "qdrant", "vector database", "ann search", "approximate nearest neighbor", "dense retrieval", "bi-encoder", "cross-encoder"},
    "retrieval": {"sentence-transformers", "embeddings", "bge", "e5", "dense retrieval", "information retrieval", "bm25", "hybrid search", "tf-idf", "retrieval augmented generation", "rag"},
    "ranking": {"learning to rank", "ltr", "lambdamart", "ranknet", "ranking", "ndcg", "mrr", "map", "neural ranking", "re-ranking", "reranking"},
    "search_systems": {"elasticsearch", "opensearch", "solr", "lucene", "inverted index", "search engine", "search systems"},
    "recommendation_systems": {"recommendation system", "collaborative filtering", "matrix factorization", "recsys", "als", "recommender"},
    "production_ml": {"production", "deployed", "shipped", "live", "inference", "latency", "throughput", "ab testing", "a/b testing"},
    "ml_infrastructure": {"mlops", "model deployment", "serving", "fastapi", "triton", "docker", "kubernetes", "kubeflow", "mlflow", "feature store"},
    "research_depth": {"phd", "ph.d", "m.tech", "ms", "research", "publication", "paper", "scientific", "journal"}
}


def _normalize_text(text: str) -> str:
    return text.lower().strip()


def _normalize_skill_name(name: str) -> str:
    n = _normalize_text(name)
    return SKILL_NORMALIZE.get(n, n)


def _days_since(date_str: str) -> int:
    if not date_str:
        return 9999
    try:
        dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
        return max(0, (REFERENCE_DATE - dt).days)
    except ValueError:
        return 9999


# ─────────────────────────────────────────────────────────────
# TITLE / ROLE FEATURES
# ─────────────────────────────────────────────────────────────

def get_title_tier(title: str) -> str:
    """Return the role tier (tier_1..tier_5) for a given title string."""
    title_lower = _normalize_text(title)

    # Tier 5: Hard disqualifiers
    for dt in DISQUALIFIER_TITLES:
        if dt in title_lower:
            return "tier_5"

    # Tier 1: Retrieval / Ranking / Search / Recommendation
    tier1_kws = [
        "retrieval", "ranking", "search engineer", "recommendation engineer",
        "search ranking", "relevance engineer", "vector search", "semantic search",
        "information retrieval",
    ]
    for kw in tier1_kws:
        if kw in title_lower:
            return "tier_1"

    # Tier 2: ML/AI Engineers, Applied Scientists, Data Scientists
    tier2_kws = [
        "ml engineer", "machine learning engineer", "ai engineer", "nlp engineer",
        "research engineer", "applied scientist", "applied ml", "data scientist",
        "deep learning engineer", "ai/ml",
    ]
    for kw in tier2_kws:
        if kw in title_lower:
            return "tier_2"

    # Tier 4: Adjacent technical (frontend, devops, mobile, etc.) — BEFORE tier_3 to prevent SWE match
    tier4_kws = [
        "frontend", "front-end", "front end", "devops", "mobile developer", "mobile engineer",
        "ios developer", "android developer", "cloud engineer", "sre", "site reliability",
        "java developer", ".net developer", "dotnet", "react developer", "angular",
        "full stack developer", "full stack engineer", "analytics engineer", "data engineer",
        "platform engineer", "qa engineer", "quality assurance", "ui/ux", "ux designer",
        "bi developer", "etl developer", "embedded engineer",
    ]
    for kw in tier4_kws:
        if kw in title_lower:
            return "tier_4"

    # Tier 3: Software Engineer / Backend Engineer / Generic technical
    tier3_kws = [
        "software engineer", "backend engineer", "backend developer", "engineer",
        "developer", "architect", "technical lead", "tech lead",
    ]
    for kw in tier3_kws:
        if kw in title_lower:
            return "tier_3"

    return "tier_3"  # Default for unknown technical roles


def compute_title_score(title: str) -> float:
    """Score based on how well the title matches the JD role using 5-tier taxonomy."""
    title_lower = _normalize_text(title)

    # Check exact/substring matches in IDEAL_TITLES first
    for known_title, score in IDEAL_TITLES.items():
        if known_title in title_lower:
            return score

    # Use tier-based fallback
    tier = get_title_tier(title)
    tier_fallbacks = {
        "tier_1": 0.92,
        "tier_2": 0.80,
        "tier_3": 0.50,
        "tier_4": 0.22,
        "tier_5": 0.05,
    }
    return tier_fallbacks.get(tier, 0.25)


def is_disqualifier_title(title: str) -> bool:
    title_lower = _normalize_text(title)
    return any(dt in title_lower for dt in DISQUALIFIER_TITLES)


def is_tier4_title(title: str) -> bool:
    """Returns True for adjacent-technical roles that should be penalized."""
    return get_title_tier(title) == "tier_4"


def compute_career_title_score(career_history: list) -> float:
    if not career_history:
        return 0.0

    best_title_score = 0.0
    for job in career_history:
        job_title = job.get("title", "")
        score = compute_title_score(job_title)
        best_title_score = max(best_title_score, score)

    return best_title_score


# ─────────────────────────────────────────────────────────────
# SKILL FEATURES
# ─────────────────────────────────────────────────────────────

def compute_core_skill_match_score(skills: list) -> Tuple[float, int]:
    if not skills:
        return 0.0, 0

    total_weight = 0.0
    match_count = 0

    for skill in skills:
        name_norm = _normalize_skill_name(skill["name"])
        if name_norm in REQUIRED_SKILLS:
            proficiency = skill.get("proficiency", "beginner").lower()
            prof_score = PROFICIENCY_SCORES.get(proficiency, 0.20)
            
            endorsements = min(skill.get("endorsements", 0), 50)
            endorsement_bonus = 0.1 * (endorsements / 50.0)

            duration = min(skill.get("duration_months", 0), 60)
            duration_factor = 0.7 + 0.3 * (duration / 60.0)

            skill_score = prof_score * duration_factor + endorsement_bonus
            total_weight += min(1.0, skill_score)
            match_count += 1

    max_expected = 8
    normalized = min(1.0, total_weight / max_expected)
    return round(normalized, 4), match_count


def compute_preferred_skill_score(skills: list) -> float:
    if not skills:
        return 0.0
    
    skill_names = {_normalize_skill_name(s["name"]) for s in skills}
    matches = skill_names & PREFERRED_SKILLS
    return min(1.0, len(matches) / 5.0)


def compute_retrieval_skill_score(skills: list) -> float:
    retrieval_skills = {
        "faiss", "elasticsearch", "milvus", "weaviate", "pinecone",
        "qdrant", "opensearch", "vector search", "vector database",
        "hybrid search", "bm25", "annoy", "scann",
    }
    score = 0.0
    for skill in skills:
        norm = _normalize_skill_name(skill["name"])
        if norm in retrieval_skills:
            prof = PROFICIENCY_SCORES.get(skill.get("proficiency", "beginner").lower(), 0.2)
            score += prof
    return min(1.0, score / 2.0)


def compute_embedding_skill_score(skills: list) -> float:
    embedding_skills = {
        "sentence-transformers", "bge", "e5", "embeddings",
        "text embeddings", "dense retrieval", "bi-encoder",
    }
    for skill in skills:
        norm = _normalize_skill_name(skill["name"])
        if norm in embedding_skills:
            prof = PROFICIENCY_SCORES.get(skill.get("proficiency", "beginner").lower(), 0.2)
            return min(1.0, prof * 1.2)
    return 0.0


def compute_python_score(skills: list) -> float:
    for skill in skills:
        if _normalize_skill_name(skill["name"]) == "python":
            prof = PROFICIENCY_SCORES.get(skill.get("proficiency", "beginner").lower(), 0.2)
            return prof
    return 0.0


def compute_assessment_score(signals: dict, skills: list) -> Tuple[float, float]:
    assessments = signals.get("skill_assessment_scores", {})
    if not assessments:
        return 0.0, 0.0

    all_scores = list(assessments.values())
    avg_score = sum(all_scores) / len(all_scores) / 100.0

    ai_assessment_keys = {
        k.lower(): v
        for k, v in assessments.items()
        if any(
            ai_kw in k.lower()
            for ai_kw in [
                "nlp", "ml", "machine learning", "deep learning",
                "pytorch", "tensorflow", "transformers", "llm",
                "rag", "embedding", "retrieval", "ranking",
            ]
        )
    }
    if ai_assessment_keys:
        ai_avg = sum(ai_assessment_keys.values()) / len(ai_assessment_keys) / 100.0
    else:
        ai_avg = avg_score * 0.7

    return round(avg_score, 4), round(ai_avg, 4)


# ─────────────────────────────────────────────────────────────
# EXPERIENCE FEATURES (Smooth Rework)
# ─────────────────────────────────────────────────────────────

def compute_experience_score(profile: dict, career_history: list) -> Dict[str, float]:
    """Computes experience scores without step functions."""
    yoe = float(profile.get("years_of_experience", 0))

    try:
        from redrob_ranker.config import JD_EXPERIENCE_RANGE
        min_yoe, max_yoe = JD_EXPERIENCE_RANGE
    except Exception:
        min_yoe, max_yoe = 5.0, 9.0

    # Target YoE is min_yoe to max_yoe years. 
    # Smooth bell-like scaling: peaks at 1.0 between min_yoe and max_yoe, decays on either side
    if min_yoe <= yoe <= max_yoe:
        yoe_score = 1.0
    elif yoe < min_yoe:
        denom = float(min_yoe) if min_yoe > 0 else 1.0
        yoe_score = 0.20 + 0.80 * (yoe / denom)
    else:
        # Decays from 1.0 down towards 0.40
        yoe_score = 0.40 + 0.60 * math.exp(-(yoe - max_yoe) / 3.0)

    product_company_months = 0.0
    has_product_company = False
    ai_role_months = 0.0
    pure_consulting = True

    for job in career_history:
        company_lower = job.get("company", "").lower()
        title_lower = job.get("title", "").lower()
        duration = float(job.get("duration_months", 0))

        is_consulting = any(cc in company_lower for cc in CONSULTING_COMPANIES)
        if not is_consulting:
            pure_consulting = False
            product_company_months += duration
            has_product_company = True

        ai_role_keywords = [
            "ml", "machine learning", "ai", "data scien", "nlp",
            "search", "ranking", "recommendation", "retrieval",
        ]
        if any(kw in title_lower for kw in ai_role_keywords):
            ai_role_months += duration

    product_score = min(1.0, product_company_months / 48.0)
    if pure_consulting:
        product_score *= 0.3

    ai_exp_score = min(1.0, ai_role_months / 36.0)  # Full credit at 36 months (was 48)

    return {
        "yoe_score": round(yoe_score, 4),
        "product_company_score": round(product_score, 4),
        "ai_experience_score": round(ai_exp_score, 4),
        "is_pure_consulting": pure_consulting,
        "has_product_company": has_product_company,
    }


# ─────────────────────────────────────────────────────────────
# EDUCATION FEATURES
# ─────────────────────────────────────────────────────────────

def compute_education_score(education: list) -> float:
    if not education:
        return 0.40

    best_score = 0.0
    for edu in education:
        tier = edu.get("tier", "unknown").lower()
        tier_score = EDUCATION_TIER_SCORES.get(tier, 0.5)

        degree = edu.get("degree", "").lower().strip()
        degree_score = 0.65
        for deg_key, deg_val in DEGREE_SCORES.items():
            if deg_key in degree:
                degree_score = deg_val
                break

        field = edu.get("field_of_study", "").lower()
        field_score = 0.50
        if any(rf in field for rf in RELEVANT_FIELDS):
            field_score = 1.0

        edu_score = 0.40 * tier_score + 0.35 * degree_score + 0.25 * field_score
        best_score = max(best_score, edu_score)

    return round(best_score, 4)


# ─────────────────────────────────────────────────────────────
# LOCATION FEATURES
# ─────────────────────────────────────────────────────────────

def compute_location_score(profile: dict) -> float:
    country = profile.get("country", "").strip()
    location = profile.get("location", "").lower().strip()

    if country == PREFERRED_COUNTRY:
        for city in PREFERRED_CITIES:
            if city in location:
                return LOCATION_SCORES["preferred_city"]
        return LOCATION_SCORES["india_other"]

    return LOCATION_SCORES["abroad"]


# ─────────────────────────────────────────────────────────────
# GITHUB / OPEN SOURCE FEATURES
# ─────────────────────────────────────────────────────────────

def compute_github_score(signals: dict) -> float:
    github_raw = signals.get("github_activity_score", -1)
    if github_raw < 0:
        return 0.20
    return round(github_raw / 100.0, 4)


# ─────────────────────────────────────────────────────────────
# ROLE-SPECIFIC CANDIDATE INTELLIGENCE ENGINE (Priority 1)
# ─────────────────────────────────────────────────────────────

def compute_role_specific_depth(skills: list, career: list, profile: dict) -> Dict[str, float]:
    """
    Evaluates candidates across 8 core ML/Retrieval experience dimensions.
    Scores [0.2 to 1.0] based on professional use, production use, and production scale.
    PHASE 5: Enhanced scale detection — infers depth from context, not keyword count.
    """
    profile_text = (profile.get("summary", "") + " " + profile.get("headline", "")).lower()
    skills_set = {s["name"].lower().strip() for s in skills}

    # Phase 5: Richer scale keywords — detect production at scale
    SCALE_KEYWORDS = [
        "scale", "million", "billion", "qps", "latency", "throughput", "sharding",
        "distributed", "gb", "tb", "petabyte", "100m", "1m", "10m", "real-time",
        "low latency", "high throughput", "p99", "p95", "100ms", "requests per second",
        "large scale", "at scale", "production grade",
    ]
    PRODUCTION_KEYWORDS = ["production", "deployed", "shipped", "live", "serving", "prod", "launched"]

    # Process career history — weight recent/current jobs more heavily
    jobs_processed = []
    sorted_career = sorted(career, key=lambda j: j.get("start_date", ""), reverse=True)
    for job_idx, job in enumerate(sorted_career):
        title = job.get("title", "").lower()
        # Use FULL description (not truncated)
        desc = job.get("description", "").lower()
        full_text = f"{title} {desc}"

        has_production = any(pk in desc for pk in PRODUCTION_KEYWORDS)
        has_scale = any(sk in desc for sk in SCALE_KEYWORDS)
        # Weight: current job = 3x, second most recent = 2x, rest = 1x
        weight = 3.0 if job.get("is_current") else (2.0 if job_idx == 1 else 1.0)

        jobs_processed.append({
            "full_text": full_text,
            "has_production": has_production,
            "has_scale": has_scale,
            "weight": weight
        })

    depth_scores = {}
    has_production_at_scale = False

    for dim_name, keywords in DIMENSION_KEYWORDS.items():
        max_level = 0.0

        # Level 1: Mentioned in skills (0.2)
        if any(kw in skills_set for kw in keywords):
            max_level = max(max_level, 0.2)

        # Level 2: Used in profile summary/headline (0.4)
        if any(kw in profile_text for kw in keywords):
            max_level = max(max_level, 0.4)

        # Check job records for professional and scale usage
        for job in jobs_processed:
            if any(kw in job["full_text"] for kw in keywords):
                # Level 3: Used professionally (0.6)
                level = 0.6
                if job["has_production"]:
                    level = 0.8  # Level 4: Used in production (0.8)
                    if job["has_scale"]:
                        level = 1.0  # Level 5: Used at scale in production (1.0)
                        has_production_at_scale = True
                # Apply job recency weight — but cap at 1.0
                weighted_level = min(1.0, level * (0.7 + 0.1 * job["weight"]))
                max_level = max(max_level, weighted_level)

        depth_scores[f"{dim_name}_depth_score"] = max_level

    depth_scores["has_production_at_scale"] = 1.0 if has_production_at_scale else 0.0
    return depth_scores


# ─────────────────────────────────────────────────────────────
# TRUST ENGINE (Priority 5)
# ─────────────────────────────────────────────────────────────

def compute_trust_score(signals: dict, completeness: float, avg_assessment: float, github_score: float) -> float:
    """Computes a composite trust score [0.0 -> 1.0] indicating profile authenticity."""
    verified_email = signals.get("verified_email", False)
    verified_phone = signals.get("verified_phone", False)
    linkedin = signals.get("linkedin_connected", False)
    
    id_trust = 0.0
    if verified_email: id_trust += 0.40
    if verified_phone: id_trust += 0.35
    if linkedin: id_trust += 0.25
    
    comp_factor = completeness / 100.0
    
    endorsements = signals.get("endorsements_received", 0)
    social_factor = min(1.0, endorsements / 50.0)
    
    assess_factor = avg_assessment if avg_assessment > 0 else 0.60
    gh_factor = github_score if github_score >= 0 else 0.70
    
    trust = (
        0.40 * id_trust 
        + 0.20 * comp_factor 
        + 0.15 * social_factor 
        + 0.15 * assess_factor 
        + 0.10 * gh_factor
    )
    return round(min(1.0, max(0.0, trust)), 4)


# ─────────────────────────────────────────────────────────────
# COMPREHENSIVE FEATURE EXTRACTION
# ─────────────────────────────────────────────────────────────

def extract_features(
    candidate: dict,
    semantic_scores: dict = None,
) -> Dict[str, float]:
    """Extracts all continuous ranking features for a single candidate."""
    cid = candidate.get("candidate_id", "UNKNOWN")
    profile = candidate.get("profile", {})
    career_history = candidate.get("career_history", [])
    education = candidate.get("education", [])
    skills = candidate.get("skills", [])
    certifications = candidate.get("certifications", [])
    signals = candidate.get("redrob_signals", {})
    languages = candidate.get("languages", [])

    title = profile.get("current_title", "")

    features: Dict[str, float] = {"candidate_id": cid}

    # ── 1. Title Features ──────────────────────────────────────────────────
    features["title_score"] = compute_title_score(title)
    features["career_best_title_score"] = compute_career_title_score(career_history)
    features["combined_title_score"] = (
        0.65 * features["title_score"] + 0.35 * features["career_best_title_score"]
    )
    features["is_disqualifier_title"] = 1.0 if is_disqualifier_title(title) else 0.0

    # ── 2. Skill Features ──────────────────────────────────────────────────
    core_skill_score, core_skill_count = compute_core_skill_match_score(skills)
    features["core_skill_score"] = core_skill_score
    features["core_skill_count"] = min(1.0, core_skill_count / 8.0)
    features["preferred_skill_score"] = compute_preferred_skill_score(skills)
    features["retrieval_skill_score"] = compute_retrieval_skill_score(skills)
    features["embedding_skill_score"] = compute_embedding_skill_score(skills)
    features["python_score"] = compute_python_score(skills)
    features["total_skill_count"] = min(1.0, len(skills) / 15.0)

    total_endorsed = sum(1 for s in skills if s.get("endorsements", 0) > 0)
    features["endorsed_skill_ratio"] = total_endorsed / max(1, len(skills))

    total_endorsements = sum(s.get("endorsements", 0) for s in skills)
    features["avg_skill_endorsements"] = min(1.0, (total_endorsements / max(1, len(skills))) / 30.0)

    durations = [s.get("duration_months", 0) for s in skills if s.get("duration_months", 0) > 0]
    avg_duration = sum(durations) / max(1, len(durations))
    features["avg_skill_depth"] = min(1.0, avg_duration / 48.0)

    # ── 2b. Skill Ontology Features (Module 2 Upgrade) ────────────────────
    skill_names_normalized = {_normalize_skill_name(s["name"]) for s in skills}
    features["ontology_skill_score"] = compute_ontology_skill_score(
        skill_names_normalized, REQUIRED_SKILLS
    )
    families = {get_skill_family(s) for s in skill_names_normalized} - {"other"}
    features["skill_family_coverage"] = min(1.0, len(families) / 5.0)

    # ── 3. Assessment Features ─────────────────────────────────────────────
    avg_assessment, ai_assessment = compute_assessment_score(signals, skills)
    features["avg_assessment_score"] = avg_assessment
    features["ai_assessment_score"] = ai_assessment
    features["has_assessments"] = 1.0 if signals.get("skill_assessment_scores") else 0.0
    assessment_count = len(signals.get("skill_assessment_scores", {}))
    features["assessment_count"] = min(1.0, assessment_count / 5.0)
    features["technical_validation_score"] = min(
        1.0, features["assessment_count"] * avg_assessment
    )

    # ── 4. Experience Features ─────────────────────────────────────────────
    exp_scores = compute_experience_score(profile, career_history)
    features.update({
        "yoe_score": exp_scores["yoe_score"],
        "product_company_score": exp_scores["product_company_score"],
        "ai_experience_score": exp_scores["ai_experience_score"],
        "is_pure_consulting": float(exp_scores["is_pure_consulting"]),
        "has_product_company": float(exp_scores["has_product_company"]),
    })

    company_size = profile.get("current_company_size", "")
    size_score_map = {
        "10001+": 1.0, "5001-10000": 0.90, "1001-5000": 0.80,
        "501-1000": 0.65, "201-500": 0.50, "51-200": 0.40,
        "11-50": 0.30, "1-10": 0.20,
    }
    features["company_size_score"] = size_score_map.get(company_size, 0.40)
    features["job_diversity_score"] = min(1.0, len(career_history) / 5.0)

    # Notice period score - continuous sigmoid curve instead of step function
    notice = signals.get("notice_period_days", 90)
    features["notice_score"] = round(0.1 + 0.9 / (1.0 + math.exp((notice - 60) / 15)), 4)

    # Salary alignment (continuous range lookup)
    salary_range = signals.get("expected_salary_range_inr_lpa", {})
    sal_mid = (salary_range.get("min", 0) + salary_range.get("max", 0)) / 2.0
    if 20 <= sal_mid <= 65:
        features["salary_alignment_score"] = 1.0
    elif sal_mid > 0:
        features["salary_alignment_score"] = round(0.40 + 0.60 * math.exp(-abs(sal_mid - 42.5) / 25.0), 4)
    else:
        features["salary_alignment_score"] = 0.60

    # ── 5. Education Features ─────────────────────────────────────────────
    features["education_score"] = compute_education_score(education)
    features["certification_count"] = min(1.0, len(certifications) / 5.0)
    recent_certs = sum(1 for c in certifications if c.get("year", 0) >= 2023)
    features["recent_cert_score"] = min(1.0, recent_certs / 3.0)
    
    has_phd = any("ph" in e.get("degree", "").lower() for e in education)
    has_ms = any("m.tech" in e.get("degree", "").lower() or "m.s" in e.get("degree", "").lower() or "m.e" in e.get("degree", "").lower() for e in education)
    features["advanced_degree"] = 1.0 if has_phd else (0.70 if has_ms else 0.0)

    # ── 6. Location Features ─────────────────────────────────────────────
    features["location_score"] = compute_location_score(profile)
    features["willing_to_relocate"] = 1.0 if signals.get("willing_to_relocate") else 0.0
    work_mode = signals.get("preferred_work_mode", "")
    features["work_mode_score"] = 1.0 if work_mode in ("hybrid", "remote") else 0.60

    has_professional_english = any(
        lang.get("language", "").lower() == "english"
        and lang.get("proficiency", "").lower() in ("professional", "native", "full professional", "bilingual")
        for lang in languages
    )
    features["english_proficiency"] = 1.0 if has_professional_english else 0.50

    # ── 7. GitHub / Open Source ──────────────────────────────────────────
    features["github_score"] = compute_github_score(signals)

    # ── 8. Behavioral Features ───────────────────────────────────────────
    behavioral = compute_all_behavioral_scores(signals, profile=profile)
    features.update(behavioral)  # Contains hireability_probability

    # ── 9. Profile Summary Text Signals ──────────────────────────────────
    summary = profile.get("summary", "").lower()
    headline = profile.get("headline", "").lower()

    production_keywords = ["production", "deployed", "shipped", "scale", "real users"]
    prod_mention_count = sum(1 for kw in production_keywords if kw in summary)
    features["production_ml_mentions"] = min(1.0, prod_mention_count / 5.0)

    consulting_keywords = ["consulting", "advisory", "client work"]
    consulting_mentions = sum(1 for kw in consulting_keywords if kw in summary)
    features["consulting_summary_signal"] = min(1.0, consulting_mentions / 3.0)

    projects_text = " ".join(str(j.get("description", "")) for j in career_history).lower()
    project_kws = ["faiss", "elasticsearch", "vector", "ranking", "retrieval", "recommendation", "embedding", "rag", "search"]
    project_hits = sum(1 for kw in project_kws if kw in projects_text)
    features["project_relevance_score"] = min(1.0, project_hits / 5.0)

    headline_kws = ["ml", "machine learning", "ai", "nlp", "search", "ranking", "retrieval", "recommendation"]
    features["headline_relevance"] = min(1.0, sum(1 for kw in headline_kws if kw in headline) / 3.0)

    # ── 10. Career Trajectory Features (Module 6) ─────────────────────────
    career_scores = compute_all_career_scores(career_history)
    features.update(career_scores)

    # ── 11. Semantic Similarity Feature (Module 4) ─────────────────────────
    if semantic_scores is not None:
        features["semantic_similarity_score"] = semantic_scores.get(cid, 0.0)
    else:
        features["semantic_similarity_score"] = 0.0

    # ── 12. Role-Specific Depth scoring (Priority 1) ──────────────────────
    role_depth = compute_role_specific_depth(skills, career_history, profile)
    features.update(role_depth)

    # Average of all 8 depth dimensions (exclude the boolean has_production_at_scale)
    depth_vals = [v for k, v in role_depth.items() if k.endswith("_depth_score")]
    features["role_specific_depth_score"] = round(sum(depth_vals) / max(1, len(depth_vals)), 4)

    # ── 13. Risk Engine Probability (Priority 6) ──────────────────────────
    risk_prob, risk_reason = detect_honeypot(candidate)
    features["risk_probability"] = risk_prob

    # ── 14. Trust Score calculation (Priority 5) ──────────────────────────
    completeness = signals.get("profile_completeness_score", 0.0)
    features["trust_score"] = compute_trust_score(
        signals, completeness, avg_assessment, features["github_score"]
    )

    # ── 15. Bonus Indicators ──────────────────────────────────────────────
    features["open_to_work_flag"] = 1.0 if signals.get("open_to_work_flag") else 0.0
    days_since_active = _days_since(signals.get("last_active_date", ""))
    features["active_recently"] = 1.0 if days_since_active <= 30 else 0.0
    features["low_notice_period"] = 1.0 if signals.get("notice_period_days", 90) < 30 else 0.0
    features["strong_github"] = 1.0 if signals.get("github_activity_score", 0) > 60 else 0.0
    features["high_assessment"] = 1.0 if features.get("avg_assessment_score", 0.0) * 100 > 70 else 0.0
    features["production_at_scale"] = role_depth.get("has_production_at_scale", 0.0)

    # ── 16. Title tier feature ─────────────────────────────────────────────
    features["title_tier"] = get_title_tier(title)
    features["is_tier4_title"] = 1.0 if is_tier4_title(title) else 0.0

    # ── 17. Candidate Intelligence Engine (Block 3) ───────────────────────
    try:
        from redrob_ranker.engines.jd_intelligence_engine import get_jd_intelligence
        jd_intel = get_jd_intelligence()
    except Exception:
        jd_intel = None

    try:
        cand_intel = build_candidate_intelligence(candidate, jd_intel)
        features["engineering_maturity_score"] = cand_intel.get("engineering_maturity_score", 0.40)
        features["leadership_evidence_score"] = cand_intel.get("leadership_evidence_score", 0.0)
        features["project_complexity_score"] = cand_intel.get("project_complexity_score", 0.0)
        features["scale_evidence_score"] = cand_intel.get("scale_evidence_score", 0.0)
        features["business_impact_score"] = cand_intel.get("business_impact_score", 0.0)
        features["narrative_score"] = cand_intel.get("narrative_score", 0.40)
        features["career_coherence_score"] = cand_intel.get("career_coherence_score", 0.40)
        features["research_depth_score"] = cand_intel.get("research_depth_score", 0.0)
        features["transferable_skill_score"] = cand_intel.get("transferable_skill_score", 0.0)
        features["transferability_gain"] = cand_intel.get("transferability_gain", 0.0)
        # Override has_production_at_scale if candidate intelligence detected it
        if cand_intel.get("has_production_at_scale"):
            features["production_at_scale"] = 1.0
    except Exception as e:
        logger.warning(f"CandidateIntelligenceEngine failed for {cid}: {e}")
        features.setdefault("engineering_maturity_score", 0.40)
        features.setdefault("leadership_evidence_score", 0.0)
        features.setdefault("project_complexity_score", 0.0)
        features.setdefault("scale_evidence_score", 0.0)
        features.setdefault("business_impact_score", 0.0)
        features.setdefault("narrative_score", 0.40)
        features.setdefault("career_coherence_score", 0.40)
        features.setdefault("research_depth_score", 0.0)
        features.setdefault("transferable_skill_score", 0.0)
        features.setdefault("transferability_gain", 0.0)

    # ── 18. Company Intelligence Engine (Block 13) ────────────────────────
    try:
        company_intel = compute_company_intelligence(career_history)
        features["company_quality_score"] = company_intel.get("company_quality_score", 0.40)
        features["industry_relevance_score"] = company_intel.get("industry_relevance_score", 0.40)
        features["engineering_exposure_score"] = company_intel.get("engineering_exposure_score", 0.40)
        features["has_big_tech_experience"] = 1.0 if company_intel.get("has_big_tech_experience") else 0.0
        features["has_search_ranking_experience"] = 1.0 if company_intel.get("has_search_ranking_experience") else 0.0
        # Override binary consulting with enriched company intelligence
        if company_intel.get("is_pure_consulting"):
            features["is_pure_consulting"] = 1.0
        if company_intel.get("has_product_company"):
            features["has_product_company"] = 1.0
    except Exception as e:
        logger.warning(f"CompanyIntelligenceEngine failed for {cid}: {e}")
        features.setdefault("company_quality_score", 0.40)
        features.setdefault("industry_relevance_score", 0.40)
        features.setdefault("engineering_exposure_score", 0.40)
        features.setdefault("has_big_tech_experience", 0.0)
        features.setdefault("has_search_ranking_experience", 0.0)

    # ── 19. Skill Graph Coverage (Block 4) ────────────────────────────────
    try:
        if jd_intel:
            skill_names_set = {s.get("name", "").lower().strip() for s in skills}
            jd_mandatory = set(jd_intel.get("mandatory_skills", []))
            jd_preferred = set(jd_intel.get("preferred_skills", []))
            jd_all = jd_mandatory | jd_preferred
            if jd_all:
                coverage = compute_skill_set_coverage(skill_names_set, jd_all)
                features["jd_skill_exact_coverage"] = coverage.get("exact_coverage", 0.0)
                features["jd_skill_soft_coverage"] = coverage.get("soft_coverage", 0.0)
                # Domain coverage
                domain_cov = compute_domain_coverage(
                    skill_names_set,
                    jd_intel.get("domains", []),
                )
                features["jd_domain_coverage"] = domain_cov
            else:
                features["jd_skill_exact_coverage"] = 0.0
                features["jd_skill_soft_coverage"] = 0.0
                features["jd_domain_coverage"] = 0.0
        else:
            features["jd_skill_exact_coverage"] = 0.0
            features["jd_skill_soft_coverage"] = 0.0
            features["jd_domain_coverage"] = 0.0
    except Exception as e:
        logger.warning(f"SkillGraph coverage failed for {cid}: {e}")
        features.setdefault("jd_skill_exact_coverage", 0.0)
        features.setdefault("jd_skill_soft_coverage", 0.0)
        features.setdefault("jd_domain_coverage", 0.0)

    return features
