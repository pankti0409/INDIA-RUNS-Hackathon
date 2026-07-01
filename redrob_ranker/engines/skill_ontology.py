"""
skill_ontology.py — Module 2: Skill Ontology Engine
Builds hierarchical skill mapping.
Rewards semantic relevance and sibling overlaps rather than exact matching.
"""
from typing import Dict, Set

# Hierarchical ontology tree: skill -> set of its ancestor/parent categories
ONTOLOGY_TREE: Dict[str, Set[str]] = {
    # Vector Search & ANN Group
    "faiss": {"ann search", "vector retrieval", "similarity search", "vector search"},
    "hnsw": {"ann search", "vector indexing", "vector search"},
    "ann search": {"vector search", "vector retrieval", "approximate nearest neighbor"},
    "approximate nearest neighbor": {"vector search", "vector retrieval"},
    "vector indexing": {"vector search"},
    "vector search": {"vector retrieval"},
    "dense retrieval": {"vector search", "vector retrieval", "semantic search"},

    # Vector Databases
    "pinecone": {"vector database", "vector search"},
    "milvus": {"vector database", "vector search"},
    "weaviate": {"vector database", "vector search"},
    "qdrant": {"vector database", "vector search"},
    "vector database": {"vector search"},

    # Search Systems (Lexical/Inverted Index)
    "elasticsearch": {"search systems", "retrieval", "inverted index"},
    "opensearch": {"search systems", "retrieval", "inverted index"},
    "solr": {"search systems", "retrieval", "inverted index"},
    "search systems": {"retrieval"},

    # Ranking & Information Retrieval
    "learning to rank": {"ranking systems", "ltr"},
    "ltr": {"ranking systems", "learning to rank"},
    "lambdamart": {"ranking systems", "learning to rank"},
    "neural ranking": {"ranking systems", "learning to rank"},
    "bm25": {"retrieval", "information retrieval"},
    "hybrid search": {"retrieval", "vector search", "search systems"},

    # Recommendation Systems
    "collaborative filtering": {"recommendation systems"},
    "matrix factorization": {"recommendation systems"},
    "recsys": {"recommendation systems"},

    # NLP & Transformers
    "natural language processing": {"nlp"},
    "transformers": {"nlp"},
    "bert": {"nlp", "transformers"},
    "llm": {"nlp", "transformers"},
    "rag": {"nlp", "transformers", "retrieval"},
    "retrieval augmented generation": {"nlp", "transformers", "retrieval"},
    "fine-tuning": {"nlp", "transformers"},
    "lora": {"fine-tuning", "nlp", "transformers"},
}


def _get_ancestors(skill: str) -> Set[str]:
    """Retrieve all ancestors of a skill in the ontology tree."""
    return ONTOLOGY_TREE.get(skill.lower().strip(), set())


def compute_ontology_skill_score(
    candidate_skills_normalized: Set[str],
    required_skills: Set[str],
) -> float:
    """
    Computes semantic overlap between candidate skills and required skills.
    - Direct exact match = 1.0 credit
    - Sibling match (shares any ancestor or parent category) = 0.5 credit
    - Ancestor/Descendant match = 0.5 credit
    Returns a score in [0.0, 1.0].
    """
    if not required_skills:
        return 0.0

    total_credit = 0.0
    matched_set = set()

    # Find direct matches
    direct_matches = candidate_skills_normalized & required_skills
    total_credit += len(direct_matches)
    matched_set.update(direct_matches)

    # Evaluate remaining required skills for sibling or hierarchical overlaps
    unmatched_required = required_skills - matched_set
    for req in unmatched_required:
        req_ancestors = _get_ancestors(req)
        
        for cand_skill in candidate_skills_normalized:
            cand_ancestors = _get_ancestors(cand_skill)
            
            # Check for shared ancestor (sibling) or hierarchical parent-child relation
            if (
                cand_skill in req_ancestors or 
                req in cand_ancestors or 
                bool(req_ancestors & cand_ancestors)
            ):
                total_credit += 0.5
                break  # Sibling match satisfied for this required skill

    # Normalize by total required skills
    return round(min(1.0, total_credit / len(required_skills)), 4)


def get_skill_family(skill_name: str) -> str:
    """Classifies a skill into its coarse category group."""
    skill_lower = skill_name.lower().strip()
    families = {
        "vector_search": {"faiss", "ann search", "hnsw", "milvus", "pinecone", "weaviate", "qdrant", "vector search", "dense retrieval", "vector database"},
        "text_retrieval": {"elasticsearch", "opensearch", "bm25", "information retrieval", "hybrid search", "search systems"},
        "embeddings": {"sentence-transformers", "embeddings", "bge", "e5", "bi-encoder"},
        "nlp": {"nlp", "natural language processing", "transformers", "bert"},
        "ranking": {"learning to rank", "ltr", "lambdamart", "ndcg", "ranking systems", "neural ranking"},
        "rag": {"rag", "retrieval augmented generation"},
        "ml_frameworks": {"pytorch", "tensorflow", "lightgbm", "xgboost", "scikit-learn"},
        "llm": {"llm", "fine-tuning", "lora", "peft"},
        "mlops": {"mlops", "model deployment"},
    }
    for family, members in families.items():
        if skill_lower in members:
            return family
    return "other"
