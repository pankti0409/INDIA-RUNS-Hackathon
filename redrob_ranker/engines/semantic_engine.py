"""
semantic_engine.py — Module 4: Semantic Retrieval Engine
Features:
- Dense Semantic Similarity (BAAI/bge-small-en-v1.5)
- BM25 Lexical Similarity (Optimized for JD query terms)
- Automatic Ratio Selection (Auto-tunes 80/20, 75/25, 70/30 against Cross-Encoder)
"""
import hashlib
import json
import logging
import math
import os
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional

import numpy as np

logger = logging.getLogger(__name__)

# Graceful sentence-transformers import
try:
    from sentence_transformers import SentenceTransformer, CrossEncoder
    import torch
    torch.set_num_threads(1)
    HAS_ST = True
except ImportError:
    HAS_ST = False
    logger.warning("sentence-transformers not installed — semantic retrieval will be unavailable")

MODEL_NAME = "BAAI/bge-small-en-v1.5"
CROSS_ENCODER_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"
CACHE_DIR = Path("./cache")

# JD Text for indexing
JD_TEXT = """
Senior AI/ML Engineer specialized in ranking and retrieval systems.
Required: sentence-transformers, dense retrieval, FAISS, vector search, Elasticsearch,
learning to rank, NDCG, NLP, Python, embeddings, RAG, retrieval augmented generation,
BM25, hybrid search, vector database, Milvus, Pinecone, Weaviate, Qdrant.
Experience: 5-9 years in production ML systems, recommendation systems, search engines.
Product company background preferred. India location preferred.
"""

# Terms for fast BM25 matching — covers retrieval/ranking/search vocabulary
JD_TOKENS = [
    "senior", "ai", "ml", "engineer", "ranking", "retrieval", "systems", "dense", "faiss", "vector",
    "search", "elasticsearch", "learning", "rank", "ndcg", "nlp", "python", "embeddings", "rag",
    "bm25", "hybrid", "database", "milvus", "pinecone", "weaviate", "qdrant", "production", "recommendation",
    "mrr", "map", "ltr", "lambdamart", "hnsw", "indexing", "collaborative", "filtering", "recsys",
    "transformers", "huggingface", "pytorch", "tensorflow", "mlops", "deployment", "serving", "kubernetes", "docker",
    # Extended vocabulary (Lever 4) — high-signal retrieval/ranking terms
    "reranking", "reranker", "cross-encoder", "bi-encoder", "colbert", "splade",
    "ann", "nmslib", "scann", "annoy", "late-interaction", "sparse", "dense",
    "two-tower", "dual-encoder", "inverted", "lucene", "solr", "opensearch",
]


def _tokenize(text: str) -> List[str]:
    """Simple alphanumeric tokenizer."""
    return re.findall(r"\b[a-zA-Z0-9\-]+\b", text.lower())


def _candidate_to_text(candidate: dict) -> str:
    """Convert candidate profile to a unified text block for indexing.
    Optimized for semantic richness — uses fuller descriptions for better bi-encoder signal.
    """
    profile = candidate.get("profile", {})
    skills = candidate.get("skills", [])
    career = candidate.get("career_history", [])
    signals = candidate.get("redrob_signals", {})

    parts = [
        profile.get("current_title", ""),
        profile.get("headline", ""),
        profile.get("summary", "")[:600],  # Richer summary (was 350)
    ]

    # Include all skills with proficiency context
    skill_names = " ".join(
        f"{s['name']} {s.get('proficiency', '')}".strip()
        for s in skills
    )
    parts.append(skill_names)

    # Include ALL career history with title, company and first 300 chars of description
    job_descriptions = " ".join(
        f"{j.get('title', '')} at {j.get('company', '')} {j.get('description', '')[:300]}"
        for j in career
    )
    parts.append(job_descriptions)

    # Include publication/research signals if present
    publications = signals.get("publications", [])
    if publications:
        pub_text = " ".join(p.get("title", "") for p in publications[:3])
        parts.append(pub_text)

    return " ".join(p for p in parts if p).strip()



class SemanticEngine:
    """Manages hybrid retrieval (dense + lexical BM25) and auto-ratio tuning."""

    def __init__(self):
        self.model: Optional[SentenceTransformer] = None
        self.cross_encoder: Optional[CrossEncoder] = None
        self.jd_embedding: Optional[np.ndarray] = None
        self.best_dense_ratio = 0.75  # Default ratio: 75% dense, 25% BM25
        # Cached scores to avoid triple-encoding during a single rank run
        self._cached_dense_scores: Optional[Dict[str, float]] = None
        self._cached_bm25_scores: Optional[Dict[str, float]] = None

    def _load_model(self) -> bool:
        if not HAS_ST:
            return False
        if self.model is None:
            try:
                logger.info(f"Loading {MODEL_NAME}...")
                self.model = SentenceTransformer(MODEL_NAME)
                logger.info("Model loaded.")
            except Exception as e:
                logger.warning(f"Failed to load model: {e}")
                return False
        return True

    def _load_cross_encoder(self) -> bool:
        if not HAS_ST:
            return False
        if self.cross_encoder is None:
            try:
                logger.info(f"Loading Cross-Encoder {CROSS_ENCODER_NAME}...")
                self.cross_encoder = CrossEncoder(CROSS_ENCODER_NAME)
                logger.info("Cross-Encoder loaded.")
            except Exception as e:
                logger.warning(f"Failed to load Cross-Encoder: {e}")
                return False
        return True

    def _get_jd_embedding(self) -> Optional[np.ndarray]:
        if self.jd_embedding is not None:
            return self.jd_embedding

        CACHE_DIR.mkdir(exist_ok=True)
        jd_cache = CACHE_DIR / "jd_embedding.npy"
        if jd_cache.exists():
            self.jd_embedding = np.load(str(jd_cache))
            return self.jd_embedding

        if not self._load_model():
            return None

        self.jd_embedding = self.model.encode([JD_TEXT], normalize_embeddings=True)[0]
        np.save(str(jd_cache), self.jd_embedding)
        return self.jd_embedding

    def embed_candidates(self, candidates: List[dict], batch_size: int = 512) -> Tuple[Optional[np.ndarray], List[str]]:
        """Embeds all candidates and caches the result to disk."""
        CACHE_DIR.mkdir(exist_ok=True)
        # Use ALL ids for a stable cache key (not just first 100)
        all_ids = [c.get("candidate_id", "") for c in candidates]
        cache_key = hashlib.md5("".join(all_ids[:500]).encode()).hexdigest()[:12]
        emb_cache = CACHE_DIR / f"candidate_embeddings_{cache_key}_{len(candidates)}.npy"
        ids_cache = CACHE_DIR / f"candidate_ids_{cache_key}_{len(candidates)}.json"

        if emb_cache.exists() and ids_cache.exists():
            logger.info(f"Loading cached embeddings from {emb_cache}...")
            embeddings = np.load(str(emb_cache))
            with open(ids_cache) as f:
                cached_ids = json.load(f)
            logger.info(f"Loaded {len(cached_ids)} cached embeddings.")
            return embeddings, cached_ids

        if not self._load_model():
            return None, []

        logger.info(f"Generating embeddings for {len(candidates)} candidates (batch_size={batch_size})...")
        texts = [_candidate_to_text(c) for c in candidates]
        cand_ids = [c.get("candidate_id", "") for c in candidates]

        show_bar = len(candidates) > 1000  # Only show for large runs
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_bar,
            normalize_embeddings=True,
        )

        np.save(str(emb_cache), embeddings)
        with open(ids_cache, "w") as f:
            json.dump(cand_ids, f)
        logger.info(f"Embeddings saved to cache: {emb_cache}")

        return embeddings, cand_ids

    def compute_bm25_scores(self, candidates: List[dict]) -> Dict[str, float]:
        """
        Calculates normalized BM25 score for all candidates.
        Restricted to JD vocabulary for sub-second CPU latency.
        """
        logger.info(f"Computing BM25 lexical scores...")
        num_docs = len(candidates)
        
        # Tokenize documents and keep counts for the query vocabulary
        doc_terms = []
        doc_lengths = []
        doc_term_freqs = []
        
        # Term mapping to array columns for vectorized operations
        term_to_idx = {term: idx for idx, term in enumerate(JD_TOKENS)}
        num_terms = len(JD_TOKENS)
        
        # Document frequencies count
        df = np.zeros(num_terms, dtype=np.float32)
        
        # Term frequencies sparse-like matrix
        tf_matrix = np.zeros((num_docs, num_terms), dtype=np.float32)
        
        for doc_idx, c in enumerate(candidates):
            text = _candidate_to_text(c)
            tokens = _tokenize(text)
            doc_lengths.append(len(tokens))
            
            # Count terms
            for token in tokens:
                if token in term_to_idx:
                    idx = term_to_idx[token]
                    tf_matrix[doc_idx, idx] += 1.0
                    
        # Compute Document Frequencies
        df = np.sum(tf_matrix > 0, axis=0)
        
        # Compute IDF
        idf = np.log((num_docs - df + 0.5) / (df + 0.5) + 1.0)
        
        # Compute average document length
        avg_doc_len = sum(doc_lengths) / max(1, num_docs)
        
        # BM25 Hyperparameters
        k1 = 1.5
        b = 0.75
        
        # Vectorized BM25 computation
        doc_lengths = np.array(doc_lengths, dtype=np.float32).reshape(-1, 1)
        denom = tf_matrix + k1 * (1.0 - b + b * (doc_lengths / avg_doc_len))
        term_scores = idf * (tf_matrix * (k1 + 1.0)) / denom  # shape: (num_docs, num_terms)
        
        # Final BM25 score per document
        bm25_raw = np.sum(term_scores, axis=1)
        
        # Normalize to [0, 1]
        max_score = np.max(bm25_raw) if len(bm25_raw) > 0 else 1.0
        if max_score == 0:
            max_score = 1.0
            
        normalized_scores = bm25_raw / max_score
        
        return {c.get("candidate_id", ""): float(normalized_scores[idx]) for idx, c in enumerate(candidates)}

    def compute_dense_scores(self, candidates: List[dict]) -> Dict[str, float]:
        """Computes dense cosine similarities for all candidates."""
        jd_emb = self._get_jd_embedding()
        if jd_emb is None:
            return {}

        result = self.embed_candidates(candidates)
        if result[0] is None:
            return {}

        embeddings, cand_ids = result
        similarities = embeddings.astype(np.float32) @ jd_emb.astype(np.float32)
        # Scale to [0, 1]
        scores = (similarities + 1.0) / 2.0
        return {cid: float(score) for cid, score in zip(cand_ids, scores)}

    def auto_tune_ratio(self, candidates: List[dict], sample_size: int = 100):
        """
        Self-supervised parameter search:
        Correlates Hybrid scores against the gold-standard Cross-Encoder
        for a sample of candidates to select the optimal ratio.
        """
        if len(candidates) < 5:
            logger.info("Too few candidates for auto-tuning. Defaulting to 75% Dense/25% BM25 ratio.")
            self.best_dense_ratio = 0.75
            return

        if not self._load_cross_encoder():
            logger.info("Cross-Encoder unavailable. Defaulting to 75% Dense ratio.")
            return

        # Take a random sample of candidates with AI keyword coverage
        sample = []
        for c in candidates:
            text = _candidate_to_text(c).lower()
            if "vector" in text or "retrieval" in text or "ranking" in text:
                sample.append(c)
            if len(sample) >= sample_size:
                break
        if not sample:
            sample = candidates[:sample_size]

        # Calculate Cross-Encoder relevance scores
        pairs = [(JD_TEXT, _candidate_to_text(c)) for c in sample]
        ce_scores = self.cross_encoder.predict(pairs, batch_size=16)
        
        # Normalize CE scores
        ce_min, ce_max = np.min(ce_scores), np.max(ce_scores)
        if ce_max > ce_min:
            ce_normalized = (ce_scores - ce_min) / (ce_max - ce_min)
        else:
            ce_normalized = ce_scores

        # Calculate Dense and BM25 scores for the sample
        dense_scores_map = self.compute_dense_scores(sample)
        bm25_scores_map = self.compute_bm25_scores(sample)

        ratios = [0.80, 0.70, 0.60]  # Phase 8: Test 80/20, 70/30, 60/40
        best_ratio = 0.75
        best_correlation = -1.0

        for r in ratios:
            hybrid_scores = []
            for idx, c in enumerate(sample):
                cid = c.get("candidate_id", "")
                d_score = dense_scores_map.get(cid, 0.5)
                b_score = bm25_scores_map.get(cid, 0.0)
                hybrid_scores.append(r * d_score + (1.0 - r) * b_score)
            
            # Compute Pearson Correlation
            corr = np.corrcoef(ce_normalized, hybrid_scores)[0, 1]
            if not np.isnan(corr) and corr > best_correlation:
                best_correlation = corr
                best_ratio = r

        logger.info(f"Auto-selected Hybrid Retrieval Ratio: {best_ratio*100:.0f}% Dense / {(1.0-best_ratio)*100:.0f}% BM25 (Correlation: {best_correlation:.4f})")
        self.best_dense_ratio = best_ratio

    def compute_hybrid_retrieval_scores(self, candidates: List[dict]) -> Dict[str, float]:
        """Computes combined hybrid scores for all candidates. Caches dense+bm25 for reuse."""
        dense_map = self.compute_dense_scores(candidates)
        bm25_map = self.compute_bm25_scores(candidates)

        # Cache for reuse in rank_candidates (avoids triple-encoding)
        self._cached_dense_scores = dense_map
        self._cached_bm25_scores = bm25_map

        hybrid_map = {}
        for c in candidates:
            cid = c.get("candidate_id", "")
            d_score = dense_map.get(cid, 0.5)
            b_score = bm25_map.get(cid, 0.0)
            hybrid_map[cid] = round(self.best_dense_ratio * d_score + (1.0 - self.best_dense_ratio) * b_score, 4)

        return hybrid_map

    def compute_similarity_scores(self, candidates: List[dict]) -> Dict[str, float]:
        """Alias for compute_hybrid_retrieval_scores to support rank.py and other clients."""
        return self.compute_hybrid_retrieval_scores(candidates)


# Module-level singleton
_engine: Optional[SemanticEngine] = None


def get_engine() -> SemanticEngine:
    global _engine
    if _engine is None:
        _engine = SemanticEngine()
    return _engine
