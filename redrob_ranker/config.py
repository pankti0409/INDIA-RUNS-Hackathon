"""
config.py — Redrob Ranker Configuration
Job Description analysis: Senior AI/ML Engineer (Ranking & Retrieval) at Redrob
Evaluation date: 2026-06-22
"""
from typing import Dict, List, Set

# ─────────────────────────────────────────────────────────────
# JOB DESCRIPTION REQUIREMENTS
# ─────────────────────────────────────────────────────────────

JD_ROLE = "Senior AI/ML Engineer – Ranking & Retrieval"
JD_EXPERIENCE_RANGE = (5, 9)  # years

# Core required skills (must have) — any match = strong positive signal
REQUIRED_SKILLS: Set[str] = {
    # Embeddings / retrieval
    "sentence-transformers", "sentence transformers", "bge", "e5", "embeddings",
    "text embeddings", "dense retrieval", "bi-encoder", "cross-encoder",
    # Vector databases
    "faiss", "elasticsearch", "milvus", "weaviate", "pinecone", "qdrant",
    "opensearch", "vector search", "vector database", "annoy", "scann",
    "hybrid search", "bm25",
    # Ranking / IR
    "learning to rank", "learning-to-rank", "ltr", "ndcg", "mrr", "map",
    "ranking", "information retrieval", "recommendation system", "recsys",
    "collaborative filtering", "neural ranking",
    # ML Production
    "mlops", "model deployment", "feature store", "a/b testing",
    # Python
    "python",
    # NLP
    "nlp", "natural language processing", "transformers", "bert", "llm",
    "large language models", "fine-tuning llms", "fine-tuning", "rag",
    "retrieval augmented generation",
}

# Nice-to-have skills — positive but not critical
PREFERRED_SKILLS: Set[str] = {
    "lora", "qlora", "peft", "fine-tuning", "xgboost", "lightgbm",
    "pytorch", "tensorflow", "huggingface", "hugging face", "open-source",
    "spark", "kafka", "kubernetes", "docker", "fastapi", "redis",
    "data pipeline", "airflow", "dbt", "triton",
}

# Skills that indicate NON-AI profiles (don't penalize just for having them,
# but a profile dominated by these with no AI skills is a mismatch)
NON_AI_SKILLS: Set[str] = {
    "photoshop", "illustrator", "figma", "indesign", "premiere", "after effects",
    "seo", "content writing", "marketing", "sales", "accounting", "excel",
    "powerpoint", "six sigma", "lean", "sap", "crm", "erp",
    "solidworks", "creo", "ansys", "autocad", "cad", "fea",
    "brand design", "graphic design",
}

# ─────────────────────────────────────────────────────────────
# TITLE TAXONOMY — 5-Tier Role Relevance System
# ─────────────────────────────────────────────────────────────

# TIER 1: Direct role matches (Retrieval/Ranking/Search/Recommendation)
# TIER 2: ML/AI Engineer, Applied Scientist, Data Scientist
# TIER 3: Software Engineers with ML/Search context
# TIER 4: Adjacent technical roles (Frontend, DevOps, Mobile, Data Eng)
# TIER 5: Non-technical / wrong domain (disqualifiers)

# Role Tier multipliers applied to relevance score
ROLE_TIER_SCORES: Dict[str, float] = {
    "tier_1": 1.05,   # Retrieval/Ranking/Search/Recommendation Engineer (super-tier boost)
    "tier_2": 0.85,   # ML Engineer, AI Engineer, Applied Scientist, Data Scientist
    "tier_3": 0.65,   # Software Engineer, Backend Engineer with ML signals
    "tier_4": 0.35,   # Frontend, DevOps, Mobile, Data Engineer, Cloud Eng
    "tier_5": 0.08,   # Non-technical, wrong domain entirely
}

# Full title → (tier, base_score) mapping
IDEAL_TITLES: Dict[str, float] = {
    # Tier 1 — Direct role matches
    "retrieval engineer": 1.00,
    "ranking engineer": 1.00,
    "search engineer": 0.98,
    "recommendation engineer": 0.97,
    "recommendation systems engineer": 0.97,
    "information retrieval engineer": 1.00,
    "search ranking engineer": 1.00,
    "relevance engineer": 0.98,
    "vector search engineer": 1.00,
    "semantic search engineer": 0.98,
    # Tier 2 — ML/AI Engineers
    "ml engineer": 0.95,
    "machine learning engineer": 0.95,
    "senior machine learning engineer": 0.95,
    "ai engineer": 0.93,
    "ai/ml engineer": 0.94,
    "nlp engineer": 0.92,
    "research engineer": 0.90,
    "applied scientist": 0.90,
    "applied ml engineer": 0.92,
    "data scientist": 0.82,
    "senior data scientist": 0.84,
    "lead data scientist": 0.84,
    "principal data scientist": 0.86,
    "ml researcher": 0.80,
    "senior ai engineer": 0.93,
    "staff ml engineer": 0.95,
    "principal ml engineer": 0.95,
    "deep learning engineer": 0.88,
    "junior ml engineer": 0.60,
    # Tier 3 — SWE with ML context
    "software engineer": 0.52,
    "backend engineer": 0.50,
    "senior software engineer": 0.55,
    "senior backend engineer": 0.52,
    # Tier 4 — Adjacent technical (penalized)
    "data engineer": 0.38,
    "analytics engineer": 0.38,
    "platform engineer": 0.32,
    "full stack engineer": 0.30,
    "full stack developer": 0.30,
    "frontend engineer": 0.20,
    "frontend developer": 0.20,
    "devops engineer": 0.22,
    "sre": 0.22,
    "site reliability engineer": 0.22,
    "cloud engineer": 0.25,
    "mobile developer": 0.20,
    "mobile engineer": 0.20,
    "ios developer": 0.18,
    "android developer": 0.18,
    "java developer": 0.28,
    ".net developer": 0.22,
    "dotnet developer": 0.22,
    "react developer": 0.18,
    "angular developer": 0.18,
}

# Titles that hard-DISQUALIFY (near-zero scoring, JD explicitly rejects)
DISQUALIFIER_TITLES: Set[str] = {
    "marketing manager", "hr manager", "human resources manager",
    "accountant", "content writer", "civil engineer",
    "mechanical engineer", "customer support", "graphic designer",
    "sales executive", "sales manager", "operations manager",
    "business analyst", "financial analyst",
    "ui/ux designer", "product designer", "qa engineer",
    "quality assurance engineer", "recruiter", "hr executive",
    "procurement manager", "supply chain", "logistics manager",
    "content creator", "brand manager", "digital marketer",
    "seo specialist", "copywriter", "social media manager",
}

# Companies that are pure IT outsourcing/consulting (soft disqualifier for entire career)
CONSULTING_COMPANIES: Set[str] = {
    "tcs", "tata consultancy services", "infosys", "wipro", "accenture",
    "cognizant", "capgemini", "hcl", "hcl technologies", "mphasis",
    "l&t infotech", "l&t technology", "mindtree", "hexaware", "zensar",
    "tech mahindra", "niit technologies", "mastech", "syntel",
    "igate", "patni", "kpit", "cyient", "persistent systems",
}

# ─────────────────────────────────────────────────────────────
# SCORING WEIGHTS
# ─────────────────────────────────────────────────────────────

FEATURE_WEIGHTS: Dict[str, float] = {
    # Role match (most critical per JD)
    "title_score": 0.28,
    # Skill match
    "core_skill_score": 0.22,
    # Experience
    "experience_score": 0.15,
    # Behavioral signals (availability, engagement)
    "behavioral_score": 0.12,
    # Education
    "education_score": 0.07,
    # Assessment validation
    "assessment_score": 0.06,
    # Location
    "location_score": 0.05,
    # GitHub / open-source
    "github_score": 0.05,
}

# Penalty multipliers
PENALTIES: Dict[str, float] = {
    "disqualifier_title": 0.08,        # Title is hard disqualifier (graphic designer etc)
    "tier_4_title": 0.35,              # Tier 4 title (frontend, devops, mobile)
    "pure_consulting_background": 0.50,  # Entire career at Big IT outsourcers
    "honeypot_high": 0.05,             # Very likely honeypot
    "honeypot_medium": 0.40,           # Possible honeypot
    "no_ai_skills_at_all": 0.15,       # Zero AI-relevant skills
    "no_product_company": 0.80,        # Never worked at a product company (mild)
}

# Bonus multipliers — kept small to avoid overriding role signals
BONUSES: Dict[str, float] = {
    "active_and_open": 1.08,           # Open to work + recent activity
    "low_notice_period": 1.04,         # Notice < 30 days
    "strong_github": 1.05,             # github_activity_score > 60
    "high_assessment": 1.05,           # avg assessment > 70
    "production_at_scale": 1.10,       # Production ML at scale signals detected
}

# ─────────────────────────────────────────────────────────────
# BEHAVIORAL SIGNAL THRESHOLDS
# ─────────────────────────────────────────────────────────────

BEHAVIORAL_THRESHOLDS = {
    "recent_activity_days": 30,        # Active within 30 days = good
    "stale_activity_days": 180,        # Last active > 180 days = concern
    "good_response_rate": 0.50,        # > 50% response rate = good
    "poor_response_rate": 0.15,        # < 15% response rate = concern
    "fast_response_hours": 24,         # < 24h avg response = great
    "slow_response_hours": 120,        # > 120h response = concern
    "low_notice_days": 30,             # ≤ 30 days = preferred
    "high_notice_days": 90,            # > 90 days = penalized
    "good_interview_rate": 0.70,       # > 70% completion = reliable
    "min_profile_completeness": 50,    # < 50 = incomplete
}

# ─────────────────────────────────────────────────────────────
# LOCATION PREFERENCES
# ─────────────────────────────────────────────────────────────

PREFERRED_CITIES: Set[str] = {
    "pune", "noida", "hyderabad", "mumbai", "delhi", "bangalore", "bengaluru",
    "gurgaon", "gurugram", "chennai", "kolkata", "ahmedabad", "jaipur",
    "delhi ncr", "ncr",
}

PREFERRED_COUNTRY = "India"

LOCATION_SCORES: Dict[str, float] = {
    "preferred_city": 1.0,
    "india_other": 0.75,
    "abroad": 0.55,
}

# ─────────────────────────────────────────────────────────────
# EDUCATION CONFIG
# ─────────────────────────────────────────────────────────────

EDUCATION_TIER_SCORES: Dict[str, float] = {
    "tier_1": 1.0,
    "tier_2": 0.80,
    "tier_3": 0.60,
    "tier_4": 0.35,
    "unknown": 0.50,
}

DEGREE_SCORES: Dict[str, float] = {
    "phd": 1.0,
    "ph.d": 1.0,
    "m.tech": 0.90,
    "m.e.": 0.85,
    "m.sc": 0.85,
    "ms": 0.85,
    "m.s.": 0.85,
    "mba": 0.70,
    "b.tech": 0.75,
    "be": 0.75,
    "b.e.": 0.75,
    "bsc": 0.65,
    "b.sc": 0.65,
    "b.sc.": 0.65,
    "ba": 0.55,
    "b.a.": 0.55,
}

RELEVANT_FIELDS: Set[str] = {
    "computer science", "cs", "machine learning", "ml",
    "artificial intelligence", "ai", "data science",
    "information technology", "it", "software engineering",
    "electrical engineering", "electronics", "mathematics",
    "statistics", "physics", "computational science",
    "computer engineering", "information systems",
}

# ─────────────────────────────────────────────────────────────
# SKILL NORMALIZATION MAP
# ─────────────────────────────────────────────────────────────

SKILL_NORMALIZE: Dict[str, str] = {
    "faiss": "faiss",
    "sentence-transformers": "sentence-transformers",
    "sentence transformers": "sentence-transformers",
    "bge": "bge",
    "baai/bge": "bge",
    "e5": "e5",
    "microsoft/e5": "e5",
    "pytorch": "pytorch",
    "tensorflow": "tensorflow",
    "huggingface": "huggingface",
    "hugging face": "huggingface",
    "nlp": "nlp",
    "natural language processing": "nlp",
    "fine-tuning llms": "llm-finetuning",
    "fine tuning llms": "llm-finetuning",
    "llm fine-tuning": "llm-finetuning",
    "rag": "rag",
    "retrieval augmented generation": "rag",
    "lora": "lora",
    "qlora": "lora",
    "lightgbm": "lightgbm",
    "light gbm": "lightgbm",
    "xgboost": "xgboost",
    "elasticsearch": "elasticsearch",
    "open search": "opensearch",
    "opensearch": "opensearch",
    "pinecone": "pinecone",
    "weaviate": "weaviate",
    "qdrant": "qdrant",
    "milvus": "milvus",
    "a/b testing": "ab-testing",
    "ab testing": "ab-testing",
}

# ─────────────────────────────────────────────────────────────
# PROFICIENCY SCORES
# ─────────────────────────────────────────────────────────────

PROFICIENCY_SCORES: Dict[str, float] = {
    "expert": 1.0,
    "advanced": 0.80,
    "intermediate": 0.50,
    "beginner": 0.20,
}

# ─────────────────────────────────────────────────────────────
# HONEYPOT DETECTION THRESHOLDS
# ─────────────────────────────────────────────────────────────

HONEYPOT_THRESHOLDS = {
    "max_expert_skills_with_zero_months": 3,  # >3 expert skills with 0 months = suspicious
    "min_skill_duration_for_expert": 12,       # Expert should have >12 months use
    "max_impossible_timeline_months": 3,        # Gap tolerance for timeline errors
    "max_assessment_vs_claim_gap": 30,          # Assessment < claim-40 = suspicious
    "honeypot_flag_threshold": 0.5,             # Score > 0.5 = apply heavy penalty
    "honeypot_elimination_threshold": 0.75,    # Score > 0.75 = near-eliminate
}

# ─────────────────────────────────────────────────────────────
# RUNTIME CONFIG
# ─────────────────────────────────────────────────────────────

MAX_CANDIDATES = 100_000
TOP_CANDIDATES = 100
TOP_N_OUTPUT = TOP_CANDIDATES
CANDIDATE_ID_PATTERN = r"^CAND_[0-9]{7}$"

# Reference date for computing days since last active
REFERENCE_DATE_STR = "2026-06-22"
