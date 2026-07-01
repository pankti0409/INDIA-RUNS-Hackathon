"""
candidate_intelligence_engine.py — Block 3: Candidate Intelligence Engine

Transforms raw candidate profile into a structured, semantically-rich intelligence
representation consumed by the feature engine and decision engine.

Per plan.md Block 3:
  - Understand candidates beyond keyword matching
  - Infer competency depth from context, not just listed skills
  - Detect engineering maturity (Prototype Builder → Architect)
  - Recognize transferable skills across domains
  - Understand project complexity and production readiness
  - Analyze career narrative and growth arc
  - Understand leadership beyond titles
  - Extract behavioral signals
"""

import logging
import re
from typing import Dict, List, Optional, Tuple, Set

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# ENGINEERING MATURITY LEVELS — per plan.md Block 8 Section 8
# ─────────────────────────────────────────────────────────────────────────────

MATURITY_SIGNALS = {
    "prototype_builder": [
        "built a poc", "proof of concept", "demo", "side project", "personal project",
        "tutorial", "hackathon", "experimented", "tried", "explored",
    ],
    "production_engineer": [
        "production", "deployed", "shipped", "live", "serving", "launched",
        "maintained", "supported", "monitored", "on-call", "incident",
    ],
    "system_designer": [
        "designed", "architected system", "end-to-end", "scalable", "distributed",
        "microservices", "system design", "infrastructure", "platform",
    ],
    "technical_leader": [
        "led", "led a team", "ownership", "drove", "spearheaded", "initiated",
        "mentored", "technical lead", "tech lead", "principal engineer",
        "staff engineer", "cross-functional", "aligned", "defined technical",
    ],
    "architect": [
        "architect", "chief architect", "designed the overall", "defined the strategy",
        "org-wide", "company-wide", "principal architect", "VP", "CTO",
        "engineering strategy", "technical strategy",
    ],
}

MATURITY_SCORES = {
    "prototype_builder": 0.20,
    "production_engineer": 0.50,
    "system_designer": 0.70,
    "technical_leader": 0.85,
    "architect": 1.00,
}

# ─────────────────────────────────────────────────────────────────────────────
# LEADERSHIP EVIDENCE SIGNALS
# ─────────────────────────────────────────────────────────────────────────────

LEADERSHIP_SIGNALS = [
    "mentored", "mentoring", "coached",
    "led a team", "leading a team", "team lead", "tech lead", "technical lead",
    "managed engineers", "managed a team",
    "owned", "ownership", "end-to-end ownership",
    "drove adoption", "drove alignment",
    "principal", "staff engineer",
    "architecture decision", "designed the architecture",
    "cross-functional", "cross team", "cross-team",
    "strategic planning", "technical roadmap", "product roadmap",
    "hired", "hiring", "built the team",
    "presented to leadership", "executive presentation",
    "defined technical standards",
]

# ─────────────────────────────────────────────────────────────────────────────
# TRANSFERABLE SKILL DOMAIN MAP
# Maps experience domains → skills they make transferable to
# ─────────────────────────────────────────────────────────────────────────────

TRANSFERABLE_MAP: Dict[str, List[str]] = {
    # Recommendation system experience → ranking and retrieval
    "recommendation-systems": ["ranking", "retrieval", "embeddings", "vector-database", "dense-retrieval"],
    "collaborative-filtering": ["ranking", "embeddings", "matrix-factorization"],
    "recsys": ["ranking", "retrieval", "embeddings"],

    # NLP experience → retrieval and embeddings
    "nlp": ["embeddings", "dense-retrieval", "information-retrieval", "rag"],
    "bert": ["embeddings", "dense-retrieval", "sentence-transformers"],
    "llm": ["rag", "embeddings", "retrieval", "dense-retrieval"],
    "rag": ["retrieval", "embeddings", "vector-database", "dense-retrieval"],
    "transformers": ["embeddings", "dense-retrieval", "nlp"],

    # Search infrastructure → ranking and retrieval
    "elasticsearch": ["search", "retrieval", "bm25", "hybrid-search", "information-retrieval"],
    "opensearch": ["search", "retrieval", "bm25", "hybrid-search"],
    "solr": ["search", "retrieval", "information-retrieval", "bm25"],

    # Vector DBs are interchangeable
    "faiss": ["vector-database", "ann", "dense-retrieval", "milvus", "pinecone", "qdrant"],
    "milvus": ["vector-database", "ann", "faiss", "pinecone", "weaviate", "qdrant"],
    "pinecone": ["vector-database", "ann", "faiss", "milvus", "qdrant"],

    # Production ML → MLOps and deployment
    "mlops": ["model-deployment", "serving", "kubernetes", "feature-store"],
    "kubeflow": ["mlops", "model-deployment", "kubernetes"],
    "mlflow": ["mlops", "model-deployment", "experimentation"],

    # Data pipelines → ML infrastructure
    "spark": ["data-pipeline", "mlops", "distributed-systems"],
    "kafka": ["data-pipeline", "distributed-systems", "streaming"],

    # Frameworks
    "pytorch": ["deep-learning", "embeddings", "transformers", "bert"],
    "tensorflow": ["deep-learning", "embeddings", "model-deployment"],
    "xgboost": ["learning-to-rank", "gradient-boosting", "lightgbm"],
    "lightgbm": ["learning-to-rank", "gradient-boosting", "xgboost"],
}

# ─────────────────────────────────────────────────────────────────────────────
# PROJECT COMPLEXITY SIGNALS
# ─────────────────────────────────────────────────────────────────────────────

SCALE_SIGNALS = [
    "million", "billion", "qps", "queries per second", "rps", "requests per second",
    "100m", "1m users", "10m users", "latency", "throughput", "p99", "p95",
    "large scale", "at scale", "production scale", "tb", "gb dataset",
    "petabyte", "real-time", "low latency", "high throughput",
]

BUSINESS_IMPACT_SIGNALS = [
    "revenue", "cost reduction", "saved", "improved by", "increased by",
    "reduced latency", "ndcg improvement", "mrr improvement", "click-through",
    "conversion rate", "retention", "customer satisfaction", "engagement",
    "business metric", "kpi", "roi",
]

ARCHITECTURE_SIGNALS = [
    "designed", "architected", "built end-to-end", "from scratch", "greenfield",
    "led the architecture", "system design", "infrastructure design",
    "defined the technical", "technical direction",
]

ORIGINALITY_SIGNALS = [
    "novel", "invented", "created", "pioneered", "first", "new approach",
    "innovative", "original", "state of the art", "sota", "research",
    "paper", "publication", "patent",
]


# ─────────────────────────────────────────────────────────────────────────────
# CORE INTELLIGENCE FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def classify_engineering_maturity(
    career_history: List[Dict],
    profile: Dict,
) -> Tuple[str, float]:
    """
    Classify the candidate's engineering maturity level.
    Returns (level_name, score in [0, 1]).
    Evaluated based on the highest maturity signals found across the entire career.
    """
    full_text = " ".join([
        profile.get("summary", ""),
        profile.get("headline", ""),
        " ".join(
            j.get("title", "") + " " + j.get("description", "")
            for j in career_history
        ),
    ]).lower()

    # Evaluate from highest to lowest maturity
    for level in ["architect", "technical_leader", "system_designer", "production_engineer", "prototype_builder"]:
        signals = MATURITY_SIGNALS[level]
        if any(sig in full_text for sig in signals):
            return level, MATURITY_SCORES[level]

    return "prototype_builder", MATURITY_SCORES["prototype_builder"]


def extract_leadership_evidence(
    career_history: List[Dict],
    profile: Dict,
) -> Dict:
    """
    Extract structured leadership evidence from career descriptions.
    Goes beyond title — looks for ownership, mentoring, architecture, and cross-team signals.
    """
    full_text = " ".join([
        profile.get("summary", ""),
        profile.get("headline", ""),
        " ".join(
            j.get("title", "") + " " + j.get("description", "")
            for j in career_history
        ),
    ]).lower()

    found_signals = [sig for sig in LEADERSHIP_SIGNALS if sig in full_text]

    leadership_categories = {
        "mentoring": any(s in full_text for s in ["mentored", "mentoring", "coached", "trained engineers"]),
        "ownership": any(s in full_text for s in ["owned", "ownership", "end-to-end", "led ", "leading ", "spearheaded", "drove"]),
        "architecture": any(s in full_text for s in ["architected", "architecture decision", "designed the", "technical direction", "system design", "infrastructure design"]),
        "cross_functional": any(s in full_text for s in ["cross-functional", "cross team", "aligned", "collaborated across"]),
        "hiring": any(s in full_text for s in ["hired", "hiring", "built the team", "grew the team"]),
        "strategic": any(s in full_text for s in ["roadmap", "strategy", "strategic", "executive"]),
        "direct_reports": any(s in full_text for s in ["managed", "managing", "reported to", "reports to"]),
    }

    # Title-based bonus
    for job in career_history:
        title = job.get("title", "").lower()
        if any(kw in title for kw in ["lead", "principal", "staff", "head", "director", "vp"]):
            leadership_categories["title_leadership"] = True
            break
    else:
        leadership_categories["title_leadership"] = False

    evidence_count = sum(1 for v in leadership_categories.values() if v)
    leadership_score = min(1.0, evidence_count / 5.0)

    return {
        "leadership_score": round(leadership_score, 4),
        "leadership_categories": leadership_categories,
        "leadership_signal_count": len(found_signals),
    }


def detect_transferable_skills(
    candidate_skills: List[Dict],
    jd_mandatory_skills: List[str],
    jd_preferred_skills: List[str],
) -> Dict:
    """
    Detect skills the candidate has that are transferable to JD requirements.
    Uses the TRANSFERABLE_MAP and skill_graph for semantic proximity.

    A candidate with recommendation system experience can do ranking.
    A candidate with NLP/BERT experience can do embedding/retrieval.
    """
    from redrob_ranker.engines.skill_graph import compute_skill_set_coverage

    candidate_skill_names = {s.get("name", "").lower().strip() for s in candidate_skills}

    # Build set of all skills the candidate is adjacent to (via transferable map)
    expanded_candidate_skills: Set[str] = set(candidate_skill_names)
    for cskill in list(candidate_skill_names):
        for adjacent in TRANSFERABLE_MAP.get(cskill, []):
            expanded_candidate_skills.add(adjacent)

    jd_all_skills = set(jd_mandatory_skills + jd_preferred_skills)

    # Compute coverage with expanded skills
    coverage = compute_skill_set_coverage(expanded_candidate_skills, jd_all_skills)
    direct_coverage = compute_skill_set_coverage(candidate_skill_names, jd_all_skills)

    # What's the gain from transferability?
    transferability_gain = max(0.0, coverage["soft_coverage"] - direct_coverage["soft_coverage"])

    return {
        "transferable_skill_score": round(coverage["soft_coverage"], 4),
        "direct_skill_coverage": round(direct_coverage["soft_coverage"], 4),
        "transferability_gain": round(transferability_gain, 4),
        "transferable_matches": coverage.get("transferable_matches", []),
        "has_meaningful_transferability": transferability_gain > 0.05,
    }


def assess_project_complexity(career_history: List[Dict], profile: Dict) -> Dict:
    """
    Assess the complexity and production-readiness of the candidate's projects.
    """
    combined_text = " ".join([
        profile.get("summary", ""),
        " ".join(
            j.get("description", "")
            for j in career_history
        ),
    ]).lower()

    has_scale = sum(1 for sig in SCALE_SIGNALS if sig in combined_text)
    has_business_impact = sum(1 for sig in BUSINESS_IMPACT_SIGNALS if sig in combined_text)
    has_architecture = sum(1 for sig in ARCHITECTURE_SIGNALS if sig in combined_text)
    has_originality = sum(1 for sig in ORIGINALITY_SIGNALS if sig in combined_text)

    # Normalize each dimension
    scale_score = min(1.0, has_scale / 3.0)
    impact_score = min(1.0, has_business_impact / 3.0)
    architecture_score = min(1.0, has_architecture / 2.0)
    originality_score = min(1.0, has_originality / 2.0)

    # Composite project complexity score
    complexity_score = (
        0.35 * scale_score
        + 0.30 * impact_score
        + 0.25 * architecture_score
        + 0.10 * originality_score
    )

    # Detect if ANY project was truly production at scale
    has_production_at_scale = (
        any(ps in combined_text for ps in ["production", "deployed", "shipped", "live"])
        and has_scale >= 1
    )

    return {
        "project_complexity_score": round(complexity_score, 4),
        "scale_evidence_score": round(scale_score, 4),
        "business_impact_score": round(impact_score, 4),
        "architecture_complexity_score": round(architecture_score, 4),
        "research_originality_score": round(originality_score, 4),
        "has_production_at_scale": has_production_at_scale,
    }


def build_career_narrative(career_history: List[Dict]) -> Dict:
    """
    Build a structured career narrative:
    - Is the career coherent and progressive?
    - Is there a clear growth arc?
    - Are there strategic domain transitions or random job-hopping?
    """
    if not career_history:
        return {"narrative_score": 0.30, "is_coherent": False, "is_progressive": False}

    from redrob_ranker.engines.career_engine import compute_all_career_scores
    career_scores = compute_all_career_scores(career_history)

    # Check for domain coherence: most jobs should be in related domains
    ai_keywords = {"ml", "machine learning", "ai", "nlp", "search", "ranking",
                   "recommendation", "retrieval", "data science", "deep learning"}
    ai_job_count = sum(
        1 for j in career_history
        if any(kw in j.get("title", "").lower() for kw in ai_keywords)
    )
    coherence_score = min(1.0, ai_job_count / max(1, len(career_history)))

    # Check progression: are roles getting more senior over time?
    is_progressive = career_scores.get("promotion_velocity", 0) > 0.2

    # Stability check
    avg_tenure = career_scores.get("avg_tenure_score", 0.5)

    narrative_score = (
        0.40 * coherence_score
        + 0.35 * career_scores.get("career_growth_score", 0.0)
        + 0.25 * avg_tenure
    )

    return {
        "narrative_score": round(narrative_score, 4),
        "is_coherent": coherence_score > 0.5,
        "is_progressive": is_progressive,
        "coherence_score": round(coherence_score, 4),
        "progression_score": round(career_scores.get("promotion_velocity", 0), 4),
        "stability_score": round(avg_tenure, 4),
    }


def extract_research_signals(candidate: Dict) -> Dict:
    """Extract research depth signals from the candidate profile."""
    signals = candidate.get("redrob_signals", {})
    profile = candidate.get("profile", {})
    education = candidate.get("education", [])

    # Publications
    publications = signals.get("publications", [])
    pub_count = len(publications) if isinstance(publications, list) else 0

    # Patent count
    patents = signals.get("patents", [])
    patent_count = len(patents) if isinstance(patents, list) else 0

    # Academic signals
    has_phd = any("ph" in e.get("degree", "").lower() for e in education)
    has_ms = any(
        any(deg in e.get("degree", "").lower() for deg in ["m.tech", "m.s", "ms ", "mtech", "m.e"])
        for e in education
    )

    # Conference / paper mentions in career text
    career_text = " ".join(
        j.get("description", "") for j in candidate.get("career_history", [])
    ).lower()
    summary_text = profile.get("summary", "").lower()
    research_text = career_text + " " + summary_text

    research_keywords = ["paper", "publication", "arxiv", "conference", "icml", "neurips",
                         "acl", "emnlp", "sigir", "www ", "kdd", "iclr", "cvpr",
                         "journal", "research paper", "published", "cited"]
    research_mentions = sum(1 for kw in research_keywords if kw in research_text)

    research_score = min(1.0, (
        (0.4 if has_phd else 0.2 if has_ms else 0.0)
        + min(0.30, pub_count * 0.10)
        + min(0.15, patent_count * 0.07)
        + min(0.15, research_mentions * 0.05)
    ))

    return {
        "research_depth_score": round(research_score, 4),
        "publication_count": pub_count,
        "patent_count": patent_count,
        "has_phd": has_phd,
        "has_ms": has_ms,
        "research_mention_count": research_mentions,
    }


def build_candidate_intelligence(
    candidate: Dict,
    jd_intelligence: Optional[Dict] = None,
) -> Dict:
    """
    Main entry point: Build complete CandidateIntelligence from raw candidate dict.

    Args:
        candidate: Raw candidate profile dict
        jd_intelligence: Optional JD intelligence for JD-relative scoring

    Returns:
        CandidateIntelligence dict with all structured signals
    """
    profile = candidate.get("profile", {})
    career_history = candidate.get("career_history", [])
    skills = candidate.get("skills", [])

    # 1. Engineering maturity
    maturity_level, maturity_score = classify_engineering_maturity(career_history, profile)

    # 2. Leadership evidence
    leadership = extract_leadership_evidence(career_history, profile)

    # 3. Project complexity
    project = assess_project_complexity(career_history, profile)

    # 4. Career narrative
    narrative = build_career_narrative(career_history)

    # 5. Research signals
    research = extract_research_signals(candidate)

    # 6. Transferable skills (requires JD intelligence)
    transferable: Dict = {
        "transferable_skill_score": 0.0,
        "direct_skill_coverage": 0.0,
        "transferability_gain": 0.0,
        "transferable_matches": [],
        "has_meaningful_transferability": False,
    }
    if jd_intelligence:
        try:
            transferable = detect_transferable_skills(
                skills,
                jd_intelligence.get("mandatory_skills", []),
                jd_intelligence.get("preferred_skills", []),
            )
        except Exception as e:
            logger.warning(f"Transferable skill detection failed: {e}")

    return {
        "candidate_id": candidate.get("candidate_id", ""),
        # Engineering maturity
        "engineering_maturity_level": maturity_level,
        "engineering_maturity_score": maturity_score,
        # Leadership
        "leadership_evidence_score": leadership["leadership_score"],
        "leadership_categories": leadership["leadership_categories"],
        "leadership_signal_count": leadership["leadership_signal_count"],
        # Project complexity
        "project_complexity_score": project["project_complexity_score"],
        "scale_evidence_score": project["scale_evidence_score"],
        "business_impact_score": project["business_impact_score"],
        "architecture_complexity_score": project["architecture_complexity_score"],
        "has_production_at_scale": project["has_production_at_scale"],
        # Career narrative
        "narrative_score": narrative["narrative_score"],
        "is_coherent_career": narrative["is_coherent"],
        "is_progressive_career": narrative["is_progressive"],
        "career_coherence_score": narrative["coherence_score"],
        # Research depth
        "research_depth_score": research["research_depth_score"],
        "publication_count": research["publication_count"],
        "has_phd": research["has_phd"],
        # Transferable skills
        "transferable_skill_score": transferable["transferable_skill_score"],
        "direct_skill_coverage": transferable["direct_skill_coverage"],
        "transferability_gain": transferable["transferability_gain"],
        "has_meaningful_transferability": transferable["has_meaningful_transferability"],
    }
