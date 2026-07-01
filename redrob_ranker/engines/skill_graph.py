"""
skill_graph.py — Block 4: Technology Taxonomy & Skill Graph

A static but rich knowledge graph of technology relationships used for:
  - Transferable skill detection (FAISS experience → vector search → retrieval)
  - Domain similarity scoring (candidate domains vs. JD domains)
  - Competency equivalence recognition (BM25 == TF-IDF family, ColBERT == cross-encoder family)
  - Semantic gap bridging (candidate hasn't used FAISS but has Pinecone/Milvus — same family)

Per plan.md Block 4 Sections 5, 6, 9:
  - Recognize domain proximity relationships
  - Support transferable skill detection
  - Build technology equivalence maps
  - Remain deterministic and explainable
"""

import logging
from typing import Dict, List, Set, Optional, Tuple

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# TECHNOLOGY TAXONOMY GRAPH
# Each node is a canonical technology; edges represent semantic proximity.
# Proximity values: 1.0 = identical, 0.8 = equivalent, 0.6 = related, 0.4 = adjacent
# ─────────────────────────────────────────────────────────────────────────────

SKILL_GRAPH: Dict[str, Dict[str, float]] = {
    # ── Vector Databases / ANN ────────────────────────────────────────────────
    "faiss": {
        "milvus": 0.85, "pinecone": 0.80, "weaviate": 0.80, "qdrant": 0.85,
        "opensearch": 0.65, "elasticsearch": 0.60, "annoy": 0.75, "scann": 0.75,
        "nmslib": 0.75, "vector-database": 1.0, "dense-retrieval": 0.80,
        "ann": 0.90, "hnsw": 0.85,
    },
    "milvus": {
        "faiss": 0.85, "pinecone": 0.85, "weaviate": 0.85, "qdrant": 0.90,
        "vector-database": 1.0, "ann": 0.90, "dense-retrieval": 0.75,
    },
    "pinecone": {
        "faiss": 0.80, "milvus": 0.85, "weaviate": 0.85, "qdrant": 0.85,
        "vector-database": 1.0, "ann": 0.85, "dense-retrieval": 0.75,
    },
    "weaviate": {
        "faiss": 0.80, "milvus": 0.85, "pinecone": 0.85, "qdrant": 0.85,
        "vector-database": 1.0, "ann": 0.85, "dense-retrieval": 0.75,
    },
    "qdrant": {
        "faiss": 0.85, "milvus": 0.90, "pinecone": 0.85, "weaviate": 0.85,
        "vector-database": 1.0, "ann": 0.90,
    },
    "ann": {
        "faiss": 0.90, "milvus": 0.90, "hnsw": 0.90, "annoy": 0.85, "scann": 0.85,
        "vector-database": 0.90,
    },
    "hnsw": {"faiss": 0.85, "ann": 0.90, "vector-database": 0.80},
    "vector-database": {
        "faiss": 1.0, "milvus": 1.0, "pinecone": 1.0, "weaviate": 1.0, "qdrant": 1.0,
        "ann": 0.90, "dense-retrieval": 0.80,
    },

    # ── Search Infrastructure ─────────────────────────────────────────────────
    "elasticsearch": {
        "opensearch": 0.95, "solr": 0.70, "lucene": 0.75,
        "bm25": 0.80, "inverted-index": 0.75, "hybrid-search": 0.85,
        "vector-database": 0.55, "faiss": 0.55,
    },
    "opensearch": {
        "elasticsearch": 0.95, "solr": 0.70, "lucene": 0.75,
        "bm25": 0.80, "hybrid-search": 0.85,
    },
    "solr": {"elasticsearch": 0.70, "opensearch": 0.70, "lucene": 0.85},
    "lucene": {"elasticsearch": 0.75, "opensearch": 0.75, "solr": 0.85},
    "bm25": {
        "elasticsearch": 0.80, "opensearch": 0.80, "tf-idf": 0.75,
        "sparse-retrieval": 0.90, "hybrid-search": 0.85, "inverted-index": 0.80,
    },
    "tf-idf": {"bm25": 0.75, "sparse-retrieval": 0.85, "inverted-index": 0.75},
    "sparse-retrieval": {"bm25": 0.90, "tf-idf": 0.85, "inverted-index": 0.80},
    "hybrid-search": {
        "bm25": 0.85, "dense-retrieval": 0.85, "elasticsearch": 0.80,
        "faiss": 0.75,
    },
    "inverted-index": {"bm25": 0.80, "elasticsearch": 0.75, "lucene": 0.80},

    # ── Dense Retrieval / Embeddings ─────────────────────────────────────────
    "sentence-transformers": {
        "bge": 0.90, "e5": 0.85, "embeddings": 0.95, "bi-encoder": 0.95,
        "dense-retrieval": 0.90, "bert": 0.75, "huggingface": 0.80,
    },
    "bge": {
        "sentence-transformers": 0.90, "e5": 0.90, "embeddings": 0.95,
        "bi-encoder": 0.90, "dense-retrieval": 0.90,
    },
    "e5": {
        "sentence-transformers": 0.85, "bge": 0.90, "embeddings": 0.95,
        "bi-encoder": 0.90, "dense-retrieval": 0.90,
    },
    "embeddings": {
        "sentence-transformers": 0.95, "bge": 0.95, "e5": 0.95, "bi-encoder": 0.90,
        "dense-retrieval": 0.90, "bert": 0.70,
    },
    "bi-encoder": {
        "sentence-transformers": 0.95, "embeddings": 0.90, "dense-retrieval": 0.90,
        "cross-encoder": 0.70, "bge": 0.90,
    },
    "dense-retrieval": {
        "sentence-transformers": 0.90, "bge": 0.90, "bi-encoder": 0.90,
        "faiss": 0.80, "vector-database": 0.80, "hybrid-search": 0.85,
    },

    # ── Ranking / LTR ─────────────────────────────────────────────────────────
    "learning-to-rank": {
        "lambdamart": 0.90, "ranknet": 0.85, "listnet": 0.85, "rankboost": 0.80,
        "ndcg": 0.80, "xgboost": 0.60, "lightgbm": 0.65, "reranking": 0.80,
    },
    "lambdamart": {
        "learning-to-rank": 0.90, "ranknet": 0.80, "xgboost": 0.65, "lightgbm": 0.70,
        "ndcg": 0.75,
    },
    "cross-encoder": {
        "bi-encoder": 0.70, "reranking": 0.90, "learning-to-rank": 0.70,
        "colbert": 0.80, "sentence-transformers": 0.70,
    },
    "reranking": {
        "cross-encoder": 0.90, "learning-to-rank": 0.80, "colbert": 0.80,
        "ranking": 0.85,
    },
    "colbert": {"cross-encoder": 0.80, "reranking": 0.80, "late-interaction": 0.90},
    "ndcg": {
        "mrr": 0.80, "map": 0.75, "learning-to-rank": 0.80,
        "ranking": 0.75, "information-retrieval": 0.70,
    },
    "mrr": {"ndcg": 0.80, "map": 0.80, "ranking": 0.75},
    "map": {"ndcg": 0.75, "mrr": 0.80, "ranking": 0.75},
    "ranking": {
        "learning-to-rank": 0.85, "reranking": 0.85, "ndcg": 0.75,
        "recommendation-systems": 0.60,
    },

    # ── NLP / LLM ─────────────────────────────────────────────────────────────
    "bert": {
        "transformers": 0.90, "huggingface": 0.85, "nlp": 0.80,
        "sentence-transformers": 0.75, "llm": 0.60, "gpt": 0.60,
    },
    "transformers": {
        "bert": 0.90, "huggingface": 0.95, "nlp": 0.80, "llm": 0.75,
        "sentence-transformers": 0.80,
    },
    "huggingface": {
        "transformers": 0.95, "bert": 0.85, "sentence-transformers": 0.80,
        "llm": 0.70, "fine-tuning": 0.80, "lora": 0.75,
    },
    "llm": {
        "bert": 0.60, "gpt": 0.90, "transformers": 0.75, "rag": 0.85,
        "fine-tuning": 0.80, "huggingface": 0.70, "nlp": 0.75,
    },
    "rag": {
        "llm": 0.85, "dense-retrieval": 0.80, "embeddings": 0.75,
        "vector-database": 0.75, "retrieval": 0.85,
    },
    "fine-tuning": {
        "lora": 0.90, "peft": 0.90, "qlora": 0.90, "llm": 0.80,
        "huggingface": 0.80, "bert": 0.70,
    },
    "lora": {"fine-tuning": 0.90, "qlora": 0.95, "peft": 0.95, "llm": 0.75},
    "nlp": {
        "bert": 0.80, "transformers": 0.80, "huggingface": 0.75,
        "llm": 0.75, "embeddings": 0.70, "information-retrieval": 0.65,
    },
    "gpt": {"llm": 0.90, "bert": 0.60, "transformers": 0.75, "fine-tuning": 0.70},

    # ── Recommendation Systems ────────────────────────────────────────────────
    "recommendation-systems": {
        "collaborative-filtering": 0.90, "matrix-factorization": 0.85,
        "ranking": 0.60, "embeddings": 0.65, "recsys": 1.0,
        "two-tower": 0.80,
    },
    "collaborative-filtering": {
        "recommendation-systems": 0.90, "matrix-factorization": 0.85,
        "als": 0.80, "recsys": 0.90,
    },
    "matrix-factorization": {
        "collaborative-filtering": 0.85, "recommendation-systems": 0.85,
        "als": 0.85, "recsys": 0.85,
    },
    "recsys": {
        "recommendation-systems": 1.0, "collaborative-filtering": 0.90,
        "ranking": 0.60,
    },
    "two-tower": {
        "bi-encoder": 0.85, "recommendation-systems": 0.80, "embeddings": 0.75,
        "dense-retrieval": 0.80,
    },

    # ── Production ML / MLOps ─────────────────────────────────────────────────
    "mlops": {
        "kubeflow": 0.85, "mlflow": 0.85, "model-deployment": 0.90,
        "feature-store": 0.75, "ab-testing": 0.70, "kubernetes": 0.65,
        "docker": 0.60,
    },
    "model-deployment": {
        "mlops": 0.90, "serving": 0.90, "triton": 0.80, "torchserve": 0.80,
        "fastapi": 0.65, "kubernetes": 0.70,
    },
    "serving": {
        "model-deployment": 0.90, "triton": 0.85, "torchserve": 0.80,
        "fastapi": 0.70, "latency": 0.75,
    },
    "ab-testing": {
        "mlops": 0.70, "experimentation": 0.90, "statistics": 0.65,
    },
    "feature-store": {"mlops": 0.75, "feast": 0.85, "data-pipeline": 0.65},
    "kubernetes": {
        "docker": 0.85, "mlops": 0.65, "model-deployment": 0.70,
        "infrastructure": 0.80,
    },
    "docker": {"kubernetes": 0.85, "infrastructure": 0.75, "model-deployment": 0.65},

    # ── ML Frameworks ─────────────────────────────────────────────────────────
    "pytorch": {"tensorflow": 0.80, "huggingface": 0.80, "deep-learning": 0.90},
    "tensorflow": {"pytorch": 0.80, "keras": 0.90, "deep-learning": 0.90},
    "xgboost": {"lightgbm": 0.90, "gradient-boosting": 0.90, "learning-to-rank": 0.60},
    "lightgbm": {"xgboost": 0.90, "gradient-boosting": 0.90, "learning-to-rank": 0.65},

    # ── Information Retrieval (high-level concept) ────────────────────────────
    "information-retrieval": {
        "ranking": 0.85, "search": 0.85, "bm25": 0.80, "dense-retrieval": 0.80,
        "hybrid-search": 0.80, "ndcg": 0.70,
    },
    "retrieval": {
        "dense-retrieval": 0.90, "sparse-retrieval": 0.85, "hybrid-search": 0.90,
        "rag": 0.85, "information-retrieval": 0.90, "faiss": 0.75,
    },
    "search": {
        "information-retrieval": 0.85, "elasticsearch": 0.80, "ranking": 0.80,
        "retrieval": 0.85, "bm25": 0.75,
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# DOMAIN CLUSTERS — groups of related technologies forming a domain
# ─────────────────────────────────────────────────────────────────────────────

DOMAIN_CLUSTERS: Dict[str, Set[str]] = {
    "vector_retrieval": {
        "faiss", "milvus", "pinecone", "weaviate", "qdrant", "ann",
        "hnsw", "vector-database", "dense-retrieval", "bi-encoder",
    },
    "search_systems": {
        "elasticsearch", "opensearch", "solr", "lucene", "bm25",
        "tf-idf", "inverted-index", "sparse-retrieval", "hybrid-search",
    },
    "embeddings": {
        "sentence-transformers", "bge", "e5", "embeddings", "bi-encoder",
        "dense-retrieval", "two-tower",
    },
    "ranking_ltr": {
        "learning-to-rank", "lambdamart", "ranknet", "cross-encoder",
        "reranking", "colbert", "ndcg", "mrr", "map", "ranking",
    },
    "nlp_llm": {
        "nlp", "bert", "transformers", "huggingface", "llm", "gpt",
        "rag", "fine-tuning", "lora", "peft",
    },
    "recommendation": {
        "recommendation-systems", "collaborative-filtering",
        "matrix-factorization", "recsys", "two-tower", "als",
    },
    "production_ml": {
        "mlops", "model-deployment", "serving", "triton", "ab-testing",
        "feature-store", "kubernetes", "docker",
    },
    "ml_frameworks": {
        "pytorch", "tensorflow", "huggingface", "xgboost", "lightgbm",
        "scikit-learn",
    },
}


def _normalize_skill(skill: str) -> str:
    """Normalize skill name to canonical form."""
    return skill.lower().strip().replace(" ", "-")


def compute_skill_similarity(skill_a: str, skill_b: str) -> float:
    """
    Compute similarity between two skills using the taxonomy graph.
    Returns 0.0 (unrelated) to 1.0 (identical/equivalent).
    """
    a = _normalize_skill(skill_a)
    b = _normalize_skill(skill_b)

    if a == b:
        return 1.0

    neighbors_a = SKILL_GRAPH.get(a, {})
    if b in neighbors_a:
        return neighbors_a[b]

    neighbors_b = SKILL_GRAPH.get(b, {})
    if a in neighbors_b:
        return neighbors_b[a]

    # 2-hop: a → common → b
    max_2hop = 0.0
    for intermediate, sim_a_inter in neighbors_a.items():
        sim_inter_b = SKILL_GRAPH.get(intermediate, {}).get(b, 0.0)
        if sim_inter_b > 0:
            hop_sim = sim_a_inter * sim_inter_b * 0.8  # Discount for 2-hop
            max_2hop = max(max_2hop, hop_sim)

    return round(max_2hop, 4)


def get_skill_cluster(skill: str) -> Optional[str]:
    """Return the domain cluster name for a skill."""
    norm = _normalize_skill(skill)
    for cluster_name, members in DOMAIN_CLUSTERS.items():
        if norm in members:
            return cluster_name
    return None


def compute_skill_set_coverage(
    candidate_skills: Set[str],
    jd_skills: Set[str],
    soft_match_threshold: float = 0.60,
) -> Dict[str, float]:
    """
    Compute how well a candidate's skill set covers the JD's required skills.
    Uses graph proximity for soft matching (FAISS counts toward vector-database).

    Returns:
        exact_coverage: fraction of JD skills with exact matches
        soft_coverage: fraction of JD skills with semantic matches (>= threshold)
        transferable_matches: skills matched via graph proximity (not exact)
        match_details: list of (jd_skill, candidate_skill, similarity)
    """
    candidate_norm = {_normalize_skill(s) for s in candidate_skills}
    jd_norm = {_normalize_skill(s) for s in jd_skills}

    if not jd_norm:
        return {"exact_coverage": 0.0, "soft_coverage": 0.0, "transferable_count": 0}

    exact_matches = jd_norm & candidate_norm
    soft_matches = []
    transferable_matches = []

    for jd_skill in jd_norm - exact_matches:
        best_sim = 0.0
        best_candidate_skill = None
        for cand_skill in candidate_norm:
            sim = compute_skill_similarity(jd_skill, cand_skill)
            if sim > best_sim:
                best_sim = sim
                best_candidate_skill = cand_skill

        if best_sim >= soft_match_threshold:
            soft_matches.append(jd_skill)
            if best_candidate_skill and best_candidate_skill != jd_skill:
                transferable_matches.append((jd_skill, best_candidate_skill, round(best_sim, 3)))

    all_covered = exact_matches | set(soft_matches)
    soft_coverage = len(all_covered) / len(jd_norm)
    exact_coverage = len(exact_matches) / len(jd_norm)

    return {
        "exact_coverage": round(exact_coverage, 4),
        "soft_coverage": round(soft_coverage, 4),
        "transferable_count": len(transferable_matches),
        "transferable_matches": transferable_matches,
        "exact_matched_skills": sorted(exact_matches),
        "soft_matched_skills": sorted(soft_matches),
    }


def compute_domain_coverage(
    candidate_skills: Set[str],
    jd_domains: List[str],
) -> float:
    """
    Compute how much of the JD's domain space is covered by the candidate's skills.
    A candidate with FAISS+Milvus covers the vector_retrieval domain even without pinecone.
    """
    if not jd_domains:
        return 0.50  # Neutral default

    candidate_norm = {_normalize_skill(s) for s in candidate_skills}
    covered_domains = 0.0

    for domain in jd_domains:
        cluster_name = _get_domain_cluster_name(domain)
        if cluster_name is None:
            continue
        cluster_members = DOMAIN_CLUSTERS.get(cluster_name, set())
        if not cluster_members:
            continue
        # Coverage = fraction of cluster covered by candidate skills (exact or soft)
        covered = sum(
            1 for cm in cluster_members
            if cm in candidate_norm or any(
                compute_skill_similarity(cm, cs) >= 0.65
                for cs in candidate_norm
            )
        )
        domain_coverage = min(1.0, covered / max(1, len(cluster_members)))
        covered_domains += domain_coverage

    return round(covered_domains / max(1, len(jd_domains)), 4)


def _get_domain_cluster_name(domain: str) -> Optional[str]:
    """Map a JD domain string to a cluster name."""
    domain_map = {
        "search_and_ranking": "search_systems",
        "ranking": "ranking_ltr",
        "retrieval": "vector_retrieval",
        "vector_retrieval": "vector_retrieval",
        "embeddings": "embeddings",
        "recommendation": "recommendation",
        "nlp_and_llm": "nlp_llm",
        "production_ml": "production_ml",
        "nlp": "nlp_llm",
        "search": "search_systems",
    }
    return domain_map.get(domain)


def compute_transferability_score(
    candidate_domains: List[str],
    jd_domains: List[str],
) -> float:
    """
    Compute how transferable the candidate's domain experience is to the JD's domains.
    Uses domain cluster proximity.

    A recommendation systems expert is highly transferable to ranking (both in ranking_ltr / recommendation clusters).
    A CV engineer is less transferable to retrieval/ranking.
    """
    if not jd_domains or not candidate_domains:
        return 0.40

    DOMAIN_PROXIMITY: Dict[str, Dict[str, float]] = {
        "search_and_ranking":  {"search_and_ranking": 1.0, "recommendation": 0.75, "nlp_and_llm": 0.65, "production_ml": 0.55},
        "recommendation":      {"recommendation": 1.0, "search_and_ranking": 0.75, "nlp_and_llm": 0.60},
        "nlp_and_llm":         {"nlp_and_llm": 1.0, "search_and_ranking": 0.65, "recommendation": 0.60},
        "production_ml":       {"production_ml": 1.0, "search_and_ranking": 0.55, "recommendation": 0.50},
        "computer_vision":     {"computer_vision": 1.0, "nlp_and_llm": 0.40, "production_ml": 0.50},
        "data_engineering":    {"data_engineering": 1.0, "production_ml": 0.55},
        "research":            {"research": 1.0, "nlp_and_llm": 0.60, "search_and_ranking": 0.55},
        "infrastructure":      {"infrastructure": 1.0, "production_ml": 0.70},
    }

    total_sim = 0.0
    count = 0
    for jd_domain in jd_domains:
        best = 0.0
        for cand_domain in candidate_domains:
            prox_map = DOMAIN_PROXIMITY.get(jd_domain, {})
            sim = prox_map.get(cand_domain, 0.20)
            best = max(best, sim)
        total_sim += best
        count += 1

    return round(total_sim / max(1, count), 4)
