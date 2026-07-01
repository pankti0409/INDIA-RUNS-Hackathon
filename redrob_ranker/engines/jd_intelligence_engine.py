"""
jd_intelligence_engine.py — Block 2: Job Description Intelligence Engine

Converts any Job Description into a structured intelligence object that drives
ALL downstream ranking behavior: retrieval strategy, feature weights, competency
hierarchy, scoring profiles, and explanation generation.

Design principles (per plan.md Block 2):
  - Understand the role before matching candidates
  - Extract structured intent, not keywords
  - Generate competency hierarchy dynamically
  - Support adaptive retrieval strategy
  - Remain deterministic
"""

import logging
import re
from typing import Dict, List, Set, Tuple, Optional

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# PRIORITY SIGNAL PHRASES — determines mandatory vs. preferred requirements
# ─────────────────────────────────────────────────────────────────────────────

MANDATORY_PHRASES = {
    "must have", "required", "mandatory", "essential", "non-negotiable",
    "critical", "strongly required", "minimum qualifications", "you must",
    "requirement:", "requirements:", "must be", "must demonstrate",
}

PREFERRED_PHRASES = {
    "preferred", "desired", "expected", "good to have", "nice to have",
    "bonus", "optional", "helpful", "plus", "advantage", "ideally",
    "preferred skills", "good if", "familiarity with", "exposure to",
}

# ─────────────────────────────────────────────────────────────────────────────
# ROLE TYPE CLASSIFIER
# ─────────────────────────────────────────────────────────────────────────────

ROLE_SIGNALS: Dict[str, List[str]] = {
    "retrieval_ranking": [
        "retrieval", "ranking", "search engineer", "relevance", "information retrieval",
        "learning to rank", "ltr", "ndcg", "mrr", "bm25", "hybrid search",
        "vector search", "semantic search", "elasticsearch", "faiss", "reranking",
    ],
    "recommendation": [
        "recommendation", "recommender", "collaborative filtering", "recsys",
        "matrix factorization", "personalization",
    ],
    "ml_engineer": [
        "machine learning engineer", "ml engineer", "applied ml", "applied scientist",
        "mlops", "model deployment", "feature store", "production ml",
    ],
    "research_scientist": [
        "research scientist", "research engineer", "phd", "publications",
        "novel algorithm", "scientific contribution", "arxiv",
    ],
    "nlp_engineer": [
        "nlp", "natural language processing", "bert", "llm", "large language model",
        "fine-tuning", "rag", "retrieval augmented generation", "transformers",
    ],
    "data_scientist": [
        "data scientist", "analytics", "statistical modeling", "a/b testing",
        "hypothesis testing", "experimentation",
    ],
    "backend_engineer": [
        "backend engineer", "software engineer", "distributed systems",
        "microservices", "api design", "system design",
    ],
    "platform_infra": [
        "platform engineer", "infrastructure", "kubernetes", "devops", "sre",
        "cloud architect", "site reliability",
    ],
    "engineering_manager": [
        "engineering manager", "tech lead", "team lead", "people manager",
        "hiring", "mentoring", "headcount",
    ],
}

# ─────────────────────────────────────────────────────────────────────────────
# SENIORITY CLASSIFIER
# ─────────────────────────────────────────────────────────────────────────────

SENIORITY_SIGNALS: Dict[str, List[str]] = {
    "intern":     ["intern", "internship", "student"],
    "junior":     ["junior", "entry level", "entry-level", "fresher", "0-2 years", "1-2 years"],
    "mid":        ["mid level", "mid-level", "2-4 years", "2-5 years", "3-5 years"],
    "senior":     ["senior", "sr.", "5+ years", "5-8 years", "5-9 years", "experienced"],
    "staff":      ["staff engineer", "staff ml", "staff scientist"],
    "principal":  ["principal", "7+ years", "8+ years", "10+ years"],
    "architect":  ["architect", "solutions architect", "technical architect"],
    "manager":    ["manager", "director", "head of", "vp of", "lead engineer"],
}

# ─────────────────────────────────────────────────────────────────────────────
# DOMAIN CLASSIFIER
# ─────────────────────────────────────────────────────────────────────────────

DOMAIN_SIGNALS: Dict[str, List[str]] = {
    "search_and_ranking":  ["search", "ranking", "retrieval", "relevance", "ndcg"],
    "recommendation":      ["recommendation", "recsys", "collaborative filtering", "personalization"],
    "nlp_and_llm":         ["nlp", "llm", "bert", "transformer", "language model", "rag"],
    "computer_vision":     ["computer vision", "image", "video", "cnn", "object detection"],
    "production_ml":       ["mlops", "serving", "deployment", "inference", "latency", "throughput"],
    "infrastructure":      ["kubernetes", "docker", "cloud", "aws", "gcp", "azure"],
    "data_engineering":    ["data pipeline", "spark", "kafka", "airflow", "etl", "data lake"],
    "research":            ["research", "publication", "paper", "phd", "novel", "algorithm"],
}

# ─────────────────────────────────────────────────────────────────────────────
# SKILL TAXONOMY — maps raw skill mentions to canonical names
# ─────────────────────────────────────────────────────────────────────────────

SKILL_ALIASES: Dict[str, str] = {
    "sentence transformers": "sentence-transformers",
    "sentence-transformer": "sentence-transformers",
    "faiss": "faiss",
    "elastic search": "elasticsearch",
    "open search": "opensearch",
    "learning to rank": "learning-to-rank",
    "ltr": "learning-to-rank",
    "large language model": "llm",
    "large language models": "llm",
    "retrieval augmented generation": "rag",
    "hugging face": "huggingface",
    "pytorch": "pytorch",
    "tensorflow": "tensorflow",
    "bert": "bert",
    "gpt": "gpt",
    "vector database": "vector-database",
    "vector db": "vector-database",
    "approximate nearest neighbor": "ann",
    "a/b testing": "ab-testing",
    "ab testing": "ab-testing",
    "natural language processing": "nlp",
    "recommendation system": "recommendation-systems",
    "recommender system": "recommendation-systems",
    "collaborative filtering": "collaborative-filtering",
    "knowledge graph": "knowledge-graph",
    "cross encoder": "cross-encoder",
    "bi encoder": "bi-encoder",
    "dense retrieval": "dense-retrieval",
    "sparse retrieval": "sparse-retrieval",
}

# ─────────────────────────────────────────────────────────────────────────────
# COMPETENCY GROUPS — semantic clusters of related technologies
# ─────────────────────────────────────────────────────────────────────────────

COMPETENCY_GROUPS: Dict[str, Set[str]] = {
    "vector_retrieval": {
        "faiss", "milvus", "pinecone", "weaviate", "qdrant", "opensearch",
        "vector-database", "ann", "hnsw", "dense-retrieval", "bi-encoder",
    },
    "ranking_systems": {
        "learning-to-rank", "lambdamart", "ranknet", "ndcg", "mrr", "map",
        "cross-encoder", "reranking", "bm25", "hybrid-search",
    },
    "embeddings": {
        "sentence-transformers", "bert", "e5", "bge", "embeddings",
        "bi-encoder", "dense-retrieval", "text-embeddings",
    },
    "search_infrastructure": {
        "elasticsearch", "opensearch", "solr", "lucene", "inverted-index",
        "sparse-retrieval",
    },
    "nlp_and_llm": {
        "nlp", "llm", "bert", "gpt", "transformers", "huggingface",
        "rag", "fine-tuning", "lora", "peft",
    },
    "production_ml": {
        "mlops", "model-deployment", "serving", "triton", "torchserve",
        "ab-testing", "feature-store", "kubeflow", "mlflow",
    },
    "recommendation": {
        "recommendation-systems", "collaborative-filtering", "matrix-factorization",
        "recsys", "als", "neural-collaborative-filtering",
    },
    "infrastructure": {
        "kubernetes", "docker", "aws", "gcp", "azure", "terraform",
        "ci-cd", "fastapi", "redis", "kafka", "spark",
    },
}


def _normalize_text(text: str) -> str:
    return text.lower().strip()


def _normalize_skill(skill: str) -> str:
    norm = _normalize_text(skill)
    return SKILL_ALIASES.get(norm, norm)


def _extract_experience_range(jd_text: str) -> Tuple[int, int]:
    """Extract years of experience range from JD text."""
    text_lower = jd_text.lower()
    patterns = [
        r"(\d+)\s*[-–to]+\s*(\d+)\s*years?",
        r"(\d+)\+\s*years?",
        r"minimum\s+(\d+)\s+years?",
        r"at least\s+(\d+)\s+years?",
        r"(\d+)\s+years?\s+of\s+experience",
    ]
    ranges = []
    for pat in patterns:
        for m in re.finditer(pat, text_lower):
            groups = [int(g) for g in m.groups() if g is not None]
            if len(groups) == 2:
                ranges.append((groups[0], groups[1]))
            elif len(groups) == 1:
                ranges.append((groups[0], groups[0] + 4))

    if ranges:
        min_y = min(r[0] for r in ranges)
        max_y = max(r[1] for r in ranges)
        return min_y, max_y
    return 5, 9  # sensible default


def _extract_skills_from_text(jd_text: str) -> Tuple[Set[str], Set[str]]:
    """
    Extract mandatory and preferred skills from JD text.
    Uses paragraph-level context to determine priority.
    """
    mandatory: Set[str] = set()
    preferred: Set[str] = set()

    # Split into paragraphs/sections
    paragraphs = re.split(r"\n{2,}|\n(?=[A-Z])", jd_text)

    for para in paragraphs:
        para_lower = para.lower()
        is_mandatory = any(phrase in para_lower for phrase in MANDATORY_PHRASES)
        is_preferred = any(phrase in para_lower for phrase in PREFERRED_PHRASES)

        # Extract skill-like tokens: known skills + compound phrases
        skill_patterns = list(SKILL_ALIASES.keys()) + [
            "python", "pytorch", "tensorflow", "faiss", "elasticsearch", "opensearch",
            "milvus", "pinecone", "weaviate", "qdrant", "bm25", "ndcg", "mrr",
            "bert", "llm", "rag", "nlp", "embeddings", "kubernetes", "docker",
            "fastapi", "redis", "spark", "kafka", "mlops", "huggingface",
            "lightgbm", "xgboost", "scikit-learn", "numpy", "pandas", "sql",
            "c++", "java", "scala", "rust", "go",
        ]

        found = set()
        for pattern in skill_patterns:
            if pattern in para_lower:
                found.add(_normalize_skill(pattern))

        if is_mandatory and not is_preferred:
            mandatory.update(found)
        elif is_preferred and not is_mandatory:
            preferred.update(found)
        else:
            # No explicit priority signals — context-based heuristic
            # Bullet points in a "Requirements" section = mandatory
            if any(word in para_lower for word in ["requirement", "qualification", "must"]):
                mandatory.update(found)
            else:
                preferred.update(found)

    return mandatory, preferred


def _classify_role_types(jd_text: str) -> List[str]:
    """Identify which role types are present in the JD."""
    text_lower = jd_text.lower()
    detected = []
    for role_type, signals in ROLE_SIGNALS.items():
        matches = sum(1 for s in signals if s in text_lower)
        if matches >= 2:  # Require at least 2 signals for a confident classification
            detected.append((role_type, matches))

    detected.sort(key=lambda x: -x[1])
    return [r[0] for r in detected[:3]]  # Top 3 role types


def _classify_seniority(jd_text: str) -> str:
    """Identify seniority level from JD text."""
    text_lower = jd_text.lower()
    for level, signals in SENIORITY_SIGNALS.items():
        if any(s in text_lower for s in signals):
            return level
    return "senior"  # Default


def _classify_domains(jd_text: str) -> List[str]:
    """Identify primary domains from JD text."""
    text_lower = jd_text.lower()
    detected = []
    for domain, signals in DOMAIN_SIGNALS.items():
        matches = sum(1 for s in signals if s in text_lower)
        if matches >= 1:
            detected.append((domain, matches))
    detected.sort(key=lambda x: -x[1])
    return [d[0] for d in detected[:4]]


def _build_competency_hierarchy(role_types: List[str], mandatory_skills: Set[str]) -> List[Dict]:
    """
    Construct a ranked competency hierarchy based on role type and mandatory skills.
    Returns ordered list from most to least important.
    """
    hierarchy = []

    # Role-based competency ordering
    role_competency_map: Dict[str, List[str]] = {
        "retrieval_ranking": [
            "ranking_systems", "vector_retrieval", "embeddings",
            "search_infrastructure", "nlp_and_llm", "production_ml",
        ],
        "recommendation": [
            "recommendation", "vector_retrieval", "embeddings",
            "ranking_systems", "production_ml",
        ],
        "ml_engineer": [
            "production_ml", "embeddings", "nlp_and_llm",
            "vector_retrieval", "ranking_systems", "infrastructure",
        ],
        "research_scientist": [
            "embeddings", "nlp_and_llm", "ranking_systems",
            "vector_retrieval", "recommendation",
        ],
        "nlp_engineer": [
            "nlp_and_llm", "embeddings", "vector_retrieval",
            "production_ml", "ranking_systems",
        ],
        "backend_engineer": [
            "infrastructure", "production_ml", "search_infrastructure",
            "vector_retrieval",
        ],
        "platform_infra": [
            "infrastructure", "production_ml",
        ],
    }

    seen = set()
    for role_type in role_types:
        if role_type in role_competency_map:
            for comp in role_competency_map[role_type]:
                if comp not in seen:
                    seen.add(comp)
                    group_skills = COMPETENCY_GROUPS.get(comp, set())
                    mandatory_overlap = group_skills & mandatory_skills
                    hierarchy.append({
                        "competency": comp,
                        "importance": "mandatory" if mandatory_overlap else "preferred",
                        "mandatory_skills": sorted(mandatory_overlap),
                        "all_skills": sorted(group_skills),
                    })

    return hierarchy


def _generate_retrieval_strategy(role_types: List[str], domains: List[str]) -> Dict[str, float]:
    """
    Generate adaptive retrieval weights per plan.md Block 6 Section 17.
    Different role types require different retrieval emphasis.
    """
    # Default balanced strategy
    strategy = {
        "semantic_weight": 0.75,
        "lexical_weight": 0.25,
        "competency_weight": 0.60,
        "career_weight": 0.50,
        "leadership_weight": 0.30,
        "project_weight": 0.50,
        "research_weight": 0.20,
        "production_weight": 0.50,
    }

    for role_type in role_types:
        if role_type == "retrieval_ranking":
            strategy["semantic_weight"] = 0.80
            strategy["competency_weight"] = 0.80
            strategy["production_weight"] = 0.70
        elif role_type == "research_scientist":
            strategy["research_weight"] = 0.90
            strategy["semantic_weight"] = 0.70
            strategy["competency_weight"] = 0.70
            strategy["production_weight"] = 0.30
        elif role_type == "engineering_manager":
            strategy["leadership_weight"] = 0.90
            strategy["career_weight"] = 0.80
            strategy["production_weight"] = 0.40
        elif role_type == "ml_engineer":
            strategy["production_weight"] = 0.80
            strategy["competency_weight"] = 0.70
        elif role_type == "nlp_engineer":
            strategy["semantic_weight"] = 0.80
            strategy["competency_weight"] = 0.70

    # Clamp all to [0, 1]
    return {k: min(1.0, max(0.0, v)) for k, v in strategy.items()}


def parse_jd(jd_text: str, jd_role: Optional[str] = None) -> Dict:
    """
    Full JD Intelligence parsing pipeline.

    Args:
        jd_text: Raw job description text
        jd_role: Optional role title override

    Returns:
        Structured JDIntelligence dict consumed by all downstream engines
    """
    if not jd_text or not jd_text.strip():
        logger.warning("Empty JD text provided — using defaults")
        return _default_jd_intelligence()

    logger.info("Parsing Job Description...")

    # 1. Experience range
    yoe_min, yoe_max = _extract_experience_range(jd_text)
    logger.info(f"  Experience range: {yoe_min}-{yoe_max} years")

    # 2. Skill extraction
    mandatory_skills, preferred_skills = _extract_skills_from_text(jd_text)
    logger.info(f"  Mandatory skills: {len(mandatory_skills)}, Preferred: {len(preferred_skills)}")

    # 3. Role classification
    role_types = _classify_role_types(jd_text)
    if not role_types:
        role_types = ["ml_engineer"]  # Safe default
    primary_role = role_types[0]
    logger.info(f"  Role types: {role_types}")

    # 4. Seniority
    seniority = _classify_seniority(jd_text)
    logger.info(f"  Seniority: {seniority}")

    # 5. Domain classification
    domains = _classify_domains(jd_text)
    logger.info(f"  Domains: {domains}")

    # 6. Competency hierarchy
    competency_hierarchy = _build_competency_hierarchy(role_types, mandatory_skills)

    # 7. Adaptive retrieval strategy
    retrieval_strategy = _generate_retrieval_strategy(role_types, domains)

    # 8. Location preference extraction
    text_lower = jd_text.lower()
    location_required = (
        "india" in text_lower
        or "bangalore" in text_lower
        or "hyderabad" in text_lower
        or "remote" not in text_lower
    )

    # 9. Leadership required?
    leadership_required = any(
        phrase in text_lower
        for phrase in ["mentor", "lead a team", "manage", "lead engineers", "architect", "own the"]
    )

    # 10. Research required?
    research_required = any(
        phrase in text_lower
        for phrase in ["phd", "publication", "research paper", "novel algorithm", "state of the art"]
    )

    intelligence = {
        "jd_text": jd_text,
        "jd_role": jd_role or primary_role,
        "primary_role_type": primary_role,
        "all_role_types": role_types,
        "seniority": seniority,
        "domains": domains,
        "yoe_min": yoe_min,
        "yoe_max": yoe_max,
        "mandatory_skills": sorted(mandatory_skills),
        "preferred_skills": sorted(preferred_skills),
        "competency_hierarchy": competency_hierarchy,
        "retrieval_strategy": retrieval_strategy,
        "location_required": location_required,
        "leadership_required": leadership_required,
        "research_required": research_required,
        "product_company_preferred": "product company" in text_lower or "startup" in text_lower,
    }

    logger.info("JD Intelligence parsing complete.")
    return intelligence


def _default_jd_intelligence() -> Dict:
    """Sensible defaults for the Redrob Senior ML/Retrieval Engineer JD."""
    return parse_jd(DEFAULT_REDROB_JD, jd_role="Senior AI/ML Engineer – Ranking & Retrieval")


# ─────────────────────────────────────────────────────────────────────────────
# DEFAULT JD: Redrob Senior AI/ML Engineer (Ranking & Retrieval)
# Used as the hardcoded JD when no dynamic JD text is provided.
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_REDROB_JD = """
Senior AI/ML Engineer – Ranking & Retrieval

We are looking for a Senior AI/ML Engineer with deep expertise in ranking and retrieval systems
to join our core search and recommendation team.

Required Skills (Must Have):
- Sentence Transformers, BGE, E5, or similar dense embedding models
- FAISS, Milvus, Weaviate, Pinecone, or Qdrant for vector search
- Elasticsearch or OpenSearch for hybrid search
- BM25 and hybrid retrieval architectures
- Learning to Rank (LTR), NDCG, MRR, MAP metrics
- Production ML: model deployment, serving, monitoring, A/B testing
- Python (expert level)
- NLP, transformers, BERT, LLM familiarity
- RAG (Retrieval Augmented Generation)

Preferred Skills (Nice to Have):
- LoRA, QLoRA, PEFT for LLM fine-tuning
- LightGBM, XGBoost for gradient boosting ranking
- PyTorch, TensorFlow, HuggingFace
- Kubernetes, Docker, FastAPI
- Spark, Kafka for data pipelines
- Triton inference server

Responsibilities:
- Design and own end-to-end retrieval and ranking pipelines
- Build and deploy dense retrieval systems using bi-encoders and cross-encoders
- Improve search quality using learning-to-rank techniques
- Mentor junior engineers and drive technical decisions
- Collaborate with product teams to deliver measurable search quality improvements
- Optimize for latency, throughput, and recall at scale

Requirements:
- 5-9 years of experience in ML/AI engineering
- Demonstrated production experience with ranking or retrieval systems
- Strong understanding of semantic search, vector databases, and re-ranking
- Experience with large-scale distributed ML systems
- Product company background preferred
- India location preferred (Bangalore, Hyderabad, Pune, or remote)
"""


# ─────────────────────────────────────────────────────────────────────────────
# SINGLETON — pre-compute JD intelligence at module load time
# ─────────────────────────────────────────────────────────────────────────────

_jd_intelligence: Optional[Dict] = None


def get_jd_intelligence(jd_text: Optional[str] = None) -> Dict:
    """
    Returns the cached JD intelligence object.
    If jd_text is provided, re-parses and returns fresh intelligence.
    Otherwise returns the pre-computed default (Redrob JD).
    """
    global _jd_intelligence
    if jd_text is not None:
        return parse_jd(jd_text)
    if _jd_intelligence is None:
        _jd_intelligence = _default_jd_intelligence()
    return _jd_intelligence
