"""
company_intelligence_engine.py — Block 13: Company & Industry Intelligence Engine

Classifies companies and industries to provide rich context for candidate evaluation.

Per plan.md Block 13:
  - Understand engineering environments, not just company names
  - Model organizational maturity and engineering exposure
  - Capture industry knowledge and domain relevance
  - Measure transferability across company types
  - Remain evidence-driven
  - Avoid prestige bias (never rank Google over a great startup just by name)
"""

import logging
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# BIG TECH / PRODUCT COMPANIES — highest engineering exposure
# ─────────────────────────────────────────────────────────────────────────────

BIG_TECH: Set[str] = {
    "google", "microsoft", "amazon", "meta", "facebook", "apple", "netflix",
    "twitter", "x corp", "x.com", "uber", "airbnb", "linkedin", "salesforce",
    "adobe", "oracle", "ibm", "intel", "nvidia", "qualcomm", "samsung",
    "bytedance", "tiktok", "alibaba", "baidu", "tencent", "spotify",
    "stripe", "square", "block", "shopify", "atlassian", "slack", "zoom",
    "snowflake", "databricks", "palantir", "datadog", "new relic",
    "elastic", "confluent", "mongodb", "redis labs",
    # Indian Big Tech equivalents
    "flipkart", "paytm", "phonepe", "razorpay", "meesho", "nykaa",
    "swiggy", "zomato", "ola", "byju", "dream11", "mmt", "makemytrip",
    "freshworks", "chargebee", "clevertap", "hasura", "setu",
    "udaan", "cred", "zepto", "blinkit", "zerodha", "groww", "kite",
    "mu sigma", "fractal analytics", "tiger analytics",
}

SEARCH_RANKING_COMPANIES: Set[str] = {
    "google", "microsoft", "amazon", "meta", "linkedin", "pinterest",
    "twitter", "uber", "airbnb", "etsy", "ebay", "walmart", "target",
    "redrob", "naukri", "indeed", "glassdoor", "monster", "apna",
    "elastic", "algolia", "coveo", "lucidworks", "singlestore",
    "relevance ai", "marqo",
    # Indian search/recommendation companies
    "flipkart", "swiggy", "zomato", "ola", "meesho", "nykaa", "sharechat",
}

AI_ML_RESEARCH_LABS: Set[str] = {
    "deepmind", "openai", "anthropic", "cohere", "ai21 labs", "mistral",
    "hugging face", "huggingface", "stability ai", "midjourney",
    "nvidia research", "microsoft research", "google research", "google brain",
    "facebook ai research", "fair", "meta ai", "amazon science",
    "allen institute", "ai2", "mit csail", "stanford ai lab", "cmu",
    "iit", "iisc", "iiit", "isro", "drdo",
    "wadhwani ai", "niti aayog ai", "c-dac",
}

CONSULTING_OUTSOURCING: Set[str] = {
    "tcs", "tata consultancy services", "infosys", "wipro", "accenture",
    "cognizant", "capgemini", "hcl", "hcl technologies", "mphasis",
    "l&t infotech", "l&t technology", "mindtree", "hexaware", "zensar",
    "tech mahindra", "niit technologies", "mastech", "syntel",
    "igate", "patni", "kpit", "cyient", "persistent systems",
    "cts", "css corp", "birlasoft", "msspl", "sonata software",
    "infotech enterprises", "quintegra",
}

STARTUPS_SCALEUPS: Set[str] = {
    # These are known for strong ML culture
    "rappi", "grab", "gojek", "tokopedia", "lazada", "bukalapak",
    "clevertap", "moengage", "webengage", "netcore",
    "postman", "hasura", "setu", "sprinklr", "darwinbox",
    "leadsquared", "increff", "locus", "logiNext",
}

# ─────────────────────────────────────────────────────────────────────────────
# INDUSTRY TAXONOMY
# ─────────────────────────────────────────────────────────────────────────────

INDUSTRY_SIGNALS: Dict[str, List[str]] = {
    "search_ranking": [
        "search", "ranking", "retrieval", "information retrieval",
        "query", "relevance", "search engine",
    ],
    "ecommerce_recommendation": [
        "ecommerce", "e-commerce", "marketplace", "retail", "shopping",
        "recommendation", "personalization", "product discovery",
    ],
    "fintech": [
        "fintech", "payments", "banking", "financial", "insurance", "neobank",
        "lending", "credit", "trading", "wealth management",
    ],
    "healthtech": [
        "health", "medical", "clinical", "healthcare", "pharma",
        "biotech", "life sciences", "diagnostics",
    ],
    "edtech": ["edtech", "education", "learning", "e-learning", "lms", "mooc"],
    "logistics": ["logistics", "supply chain", "fleet", "delivery", "routing", "last mile"],
    "saas": ["saas", "software as a service", "b2b software", "enterprise software", "crm"],
    "social_media": ["social", "media", "content", "streaming", "entertainment"],
    "research_lab": ["research", "lab", "institute", "university", "academic"],
    "consulting": ["consulting", "advisory", "outsourcing", "services", "it services"],
}

# ─────────────────────────────────────────────────────────────────────────────
# COMPANY QUALITY SCORES — reflects engineering environment quality
# NOT prestige — evidence of engineering exposure
# ─────────────────────────────────────────────────────────────────────────────

COMPANY_TYPE_SCORES: Dict[str, float] = {
    "big_tech": 1.0,
    "search_ranking_specialist": 1.0,
    "ai_research_lab": 0.95,
    "scaleup_product": 0.85,
    "startup_product": 0.75,
    "mid_product": 0.70,
    "small_product": 0.60,
    "consulting_top_tier": 0.45,
    "consulting_mid": 0.30,
    "outsourcing": 0.20,
    "unknown": 0.50,
}

INDUSTRY_RELEVANCE_SCORES: Dict[str, float] = {
    # JD is for a Ranking/Retrieval Engineer — search-adjacent industries are highest
    "search_ranking": 1.00,
    "ecommerce_recommendation": 0.90,
    "social_media": 0.75,
    "saas": 0.65,
    "fintech": 0.60,
    "logistics": 0.55,
    "edtech": 0.50,
    "healthtech": 0.45,
    "research_lab": 0.80,
    "consulting": 0.25,
    "unknown": 0.50,
}


def _normalize_company_name(name: str) -> str:
    return name.lower().strip()


def classify_company(company_name: str) -> Tuple[str, float]:
    """
    Classify a company into a type and return its quality score.
    Returns (company_type, quality_score).
    """
    norm = _normalize_company_name(company_name)

    if any(bt in norm for bt in BIG_TECH):
        return "big_tech", COMPANY_TYPE_SCORES["big_tech"]
    if any(sr in norm for sr in SEARCH_RANKING_COMPANIES):
        return "search_ranking_specialist", COMPANY_TYPE_SCORES["search_ranking_specialist"]
    if any(rl in norm for rl in AI_ML_RESEARCH_LABS):
        return "ai_research_lab", COMPANY_TYPE_SCORES["ai_research_lab"]
    if any(c in norm for c in CONSULTING_OUTSOURCING):
        return "outsourcing", COMPANY_TYPE_SCORES["outsourcing"]
    if any(s in norm for s in STARTUPS_SCALEUPS):
        return "scaleup_product", COMPANY_TYPE_SCORES["scaleup_product"]

    # Heuristic: small unknown companies are treated as small products
    return "unknown", COMPANY_TYPE_SCORES["unknown"]


def classify_industry(description: str, company_name: str) -> str:
    """Classify the industry of a role based on description and company name."""
    text = (description + " " + company_name).lower()

    for industry, signals in INDUSTRY_SIGNALS.items():
        if any(sig in text for sig in signals):
            return industry

    return "unknown"


def compute_company_intelligence(career_history: List[Dict]) -> Dict:
    """
    Analyze the candidate's entire career from a company quality perspective.

    Returns company intelligence signals including:
      - Overall company quality score (weighted average by tenure)
      - Industry relevance score
      - Engineering environment complexity estimate
      - Whether candidate has product company experience
      - Best company encountered in career
    """
    if not career_history:
        return {
            "company_quality_score": 0.40,
            "industry_relevance_score": 0.40,
            "engineering_exposure_score": 0.40,
            "has_big_tech_experience": False,
            "has_search_ranking_experience": False,
            "has_product_company": False,
            "is_pure_consulting": False,
            "best_company_type": "unknown",
            "dominant_industry": "unknown",
        }

    total_months = 0.0
    weighted_quality = 0.0
    weighted_industry = 0.0

    has_big_tech = False
    has_search_ranking = False
    has_product = False
    is_all_consulting = True
    best_company_type = "unknown"
    best_company_score = 0.0

    industry_month_map: Dict[str, float] = {}

    for job in career_history:
        company = job.get("company", "")
        description = job.get("description", "")
        duration = float(job.get("duration_months", 12))
        total_months += duration

        # Classify company
        company_type, quality_score = classify_company(company)

        # Classify industry
        industry = classify_industry(description, company)

        # Weighted accumulation
        weighted_quality += quality_score * duration
        industry_month_map[industry] = industry_month_map.get(industry, 0.0) + duration

        industry_relevance = INDUSTRY_RELEVANCE_SCORES.get(industry, 0.50)
        weighted_industry += industry_relevance * duration

        # Flags
        if company_type == "big_tech":
            has_big_tech = True
        if company_type == "search_ranking_specialist":
            has_search_ranking = True
        if company_type not in ("outsourcing", "consulting_mid", "consulting_top_tier"):
            has_product = True
            is_all_consulting = False

        if quality_score > best_company_score:
            best_company_score = quality_score
            best_company_type = company_type

    avg_quality = weighted_quality / max(1.0, total_months)
    avg_industry_relevance = weighted_industry / max(1.0, total_months)

    # Dominant industry (most months)
    dominant_industry = max(industry_month_map, key=industry_month_map.get) if industry_month_map else "unknown"

    # Engineering exposure: combination of company quality + industry relevance
    engineering_exposure = (0.60 * avg_quality + 0.40 * avg_industry_relevance)

    return {
        "company_quality_score": round(avg_quality, 4),
        "industry_relevance_score": round(avg_industry_relevance, 4),
        "engineering_exposure_score": round(engineering_exposure, 4),
        "has_big_tech_experience": has_big_tech,
        "has_search_ranking_experience": has_search_ranking,
        "has_product_company": has_product,
        "is_pure_consulting": is_all_consulting,
        "best_company_type": best_company_type,
        "dominant_industry": dominant_industry,
    }
