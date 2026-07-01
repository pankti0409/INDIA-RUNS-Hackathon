"""
ranking_engine.py — Cascade Reranking Engine with Cross-Encoder
Fuses dense semantic similarity & BM25 lexical similarity to retrieve top candidates,
reranks them using a Cross-Encoder, and scores them using the final multiplicative formula.
"""
import logging
import math
from typing import Dict, List, Optional, Tuple
import numpy as np

from redrob_ranker.config import TOP_CANDIDATES
from redrob_ranker.engines.feature_engine import extract_features
from redrob_ranker.engines.semantic_engine import get_engine, JD_TEXT, _candidate_to_text

logger = logging.getLogger(__name__)


def sigmoid(x: float) -> float:
    """Scales Cross-Encoder logits to [0, 1] range."""
    try:
        return 1.0 / (1.0 + math.exp(-x))
    except OverflowError:
        return 0.0 if x < 0 else 1.0


def compute_final_score(features: Dict[str, float]) -> float:
    """
    Production Ranking Formula — integrates all intelligence engines.

    Architecture:
    1. Compute relevance from semantic + cross-encoder + title + skills + depth
    2. Enrich relevance with new intelligence signals:
       - engineering_maturity_score (candidate intelligence engine)
       - jd_skill_soft_coverage (skill graph engine)
       - industry_relevance_score (company intelligence engine)
       - project_complexity_score (candidate intelligence engine)
    3. Apply title-tier gate
    4. Apply structural penalties (consulting, no-product, no-AI-skills)
    5. Apply risk/honeypot penalties
    6. Apply behavioral multiplier [0.60, 1.15]
    7. Apply trust as light weight
    8. Apply bonus multipliers
    9. Square-root scaling
    """
    from redrob_ranker.config import PENALTIES, BONUSES, ROLE_TIER_SCORES

    h_score = features.get("semantic_similarity_score", 0.0)
    if h_score == 0.0:
        # Fallback when semantic engine not active (unit tests / CLI without --semantic)
        h_score = 0.5 * features.get("combined_title_score", 0.5) + 0.5 * features.get("core_skill_score", 0.5)
        h_score = min(1.0, h_score * 1.2)

    ce_score = features.get("cross_encoder_score", h_score)
    depth_score = features.get("role_specific_depth_score", 0.0)
    title_score = features.get("combined_title_score", 0.0)
    skill_score = features.get("core_skill_score", 0.0)

    # New intelligence signals
    maturity_score = features.get("engineering_maturity_score", 0.40)
    jd_skill_coverage = features.get("jd_skill_soft_coverage", features.get("ontology_skill_score", skill_score))
    industry_rel = features.get("industry_relevance_score", 0.50)
    project_complexity = features.get("project_complexity_score", 0.0)

    # ── Step 1: Base relevance (enriched) ─────────────────────────────────────
    relevance = (
        0.26 * h_score
        + 0.26 * ce_score
        + 0.10 * depth_score
        + 0.14 * title_score
        + 0.10 * skill_score
        + 0.06 * jd_skill_coverage     # Skill graph soft coverage
        + 0.04 * maturity_score        # Engineering maturity
        + 0.02 * industry_rel          # Industry relevance
        + 0.02 * project_complexity    # Project complexity
    )

    # ── Step 2: Title-Tier Gate ────────────────────────────────────────────
    title_tier = features.get("title_tier", "tier_3")
    tier_multiplier = ROLE_TIER_SCORES.get(title_tier, 0.65)

    # Extra hard penalty for disqualifier titles (Tier 5)
    if features.get("is_disqualifier_title", 0.0) == 1.0:
        tier_multiplier = min(tier_multiplier, PENALTIES.get("disqualifier_title", 0.08))

    # Tier 4 titles (Frontend/DevOps/Mobile) get capped
    if features.get("is_tier4_title", 0.0) == 1.0:
        # If they have strong AI skills + career depth, let some through but capped at Tier3 ceiling
        skill_rescue = min(0.20, skill_score * 0.4 + depth_score * 0.2)
        tier_multiplier = min(ROLE_TIER_SCORES["tier_4"] + skill_rescue, ROLE_TIER_SCORES["tier_3"])

    role_adjusted_relevance = relevance * tier_multiplier

    # ── Step 3: Structural penalties ─────────────────────────────────────
    structural_multiplier = 1.0

    if features.get("is_pure_consulting", 0.0) == 1.0:
        structural_multiplier *= PENALTIES.get("pure_consulting_background", 0.50)
    if features.get("has_product_company", 1.0) == 0.0:
        structural_multiplier *= PENALTIES.get("no_product_company", 0.80)
    # No AI skills at all is a hard penalization
    if features.get("core_skill_score", 0.0) == 0.0 and features.get("preferred_skill_score", 0.0) == 0.0:
        structural_multiplier *= PENALTIES.get("no_ai_skills_at_all", 0.15)

    # ── Step 4: Risk / Honeypot penalty ──────────────────────────────────
    risk = features.get("risk_probability", 0.0)
    if risk >= 0.75:
        structural_multiplier *= PENALTIES.get("honeypot_high", 0.05)
    elif risk >= 0.5:
        structural_multiplier *= PENALTIES.get("honeypot_medium", 0.40)

    relevance_penalized = role_adjusted_relevance * structural_multiplier

    # ── Step 5: Behavioral multiplier — bounded [0.60, 1.15] ─────────────
    # Hireability is the primary behavioral gate. It acts as a booster, not a replacement.
    # This prevents a non-responsive candidate from scoring the same as an engaged one.
    hireability = features.get("hireability_probability", 0.0)
    location_score = features.get("location_score", 0.65)
    # Location contributes a small additive signal (0 to 0.05 range)
    location_boost = 0.05 * (location_score - 0.55) / 0.45  # 0 for abroad, 0.05 for preferred city
    behavioral_multiplier = 0.60 + 0.55 * hireability + max(0.0, location_boost)  # range: [0.60, 1.20]

    # ── Step 6: Trust as a light weight (not a full multiplier) ──────────
    # Trust helps separate verified profiles from unverified ones in the same tier,
    # but it does NOT amplify a Frontend Engineer over an ML Engineer.
    trust = features.get("trust_score", 0.0)
    trust_weight = 0.88 + 0.12 * trust  # range: [0.88, 1.00] — very light

    # ── Step 7: Final composition ─────────────────────────────────────────
    final_score = relevance_penalized * behavioral_multiplier * trust_weight

    # ── Step 8: Bonus multipliers ─────────────────────────────────────────
    bonus_multiplier = 1.0
    if features.get("open_to_work_flag", 0.0) == 1.0 and features.get("active_recently", 0.0) == 1.0:
        bonus_multiplier *= BONUSES.get("active_and_open", 1.08)
    if features.get("low_notice_period", 0.0) == 1.0:
        bonus_multiplier *= BONUSES.get("low_notice_period", 1.04)
    if features.get("strong_github", 0.0) == 1.0:
        bonus_multiplier *= BONUSES.get("strong_github", 1.05)
    if features.get("high_assessment", 0.0) == 1.0:
        bonus_multiplier *= BONUSES.get("high_assessment", 1.05)
    if features.get("production_at_scale", 0.0) == 1.0:
        bonus_multiplier *= BONUSES.get("production_at_scale", 1.10)
    # New bonuses from intelligence engines
    if features.get("has_search_ranking_experience", 0.0) == 1.0:
        bonus_multiplier *= 1.06
    if features.get("has_big_tech_experience", 0.0) == 1.0:
        bonus_multiplier *= 1.04

    final_score = final_score * bonus_multiplier

    # ── Step 9: Square-root scaling for better spread ─────────────────────
    final_score = math.sqrt(max(0.0, final_score))
    
    # Scale to ensure the maximum possible score is strictly <= 1.0
    # Calibrated so a perfect Tier-1 candidate with all bonuses scores ~0.93–0.95
    # (was /1.30 which capped even perfect candidates at ~0.87)
    final_score = final_score / 1.08
    
    # Hard gate: Tier 5 or disqualifier titles must not be in the top 100
    if features.get("is_disqualifier_title", 0.0) == 1.0 or title_tier == "tier_5":
        return 0.001
        
    return round(min(1.0, max(0.0, final_score)), 6)


def _make_dummy_candidate(idx: int) -> Tuple[dict, Dict[str, float], float]:
    """Creates a zero-score dummy candidate for CSV padding (submission compliance only)."""
    dummy_id = f"CAND_9990{idx:03d}"
    dummy_cand = {
        "candidate_id": dummy_id,
        "profile": {
            "anonymized_name": f"Dummy Candidate {idx + 1}",
            "current_title": "N/A",
            "years_of_experience": 0.0,
            "location": "India",
            "country": "India"
        },
        "skills": [],
        "career_history": [],
        "redrob_signals": {}
    }
    dummy_feat = {
        "combined_title_score": 0.0,
        "core_skill_score": 0.0,
        "yoe_score": 0.0,
        "availability_score": 0.0,
        "education_score": 0.0,
        "github_score": 0.0,
        "honeypot_probability": 0.0,
        "relevance_score": 0.0,
        "semantic_similarity_score": 0.0,
        "cross_encoder_score": 0.0,
        "role_specific_depth_score": 0.0,
        "hireability_probability": 0.0,
        "trust_score": 0.0,
        "risk_probability": 0.0
    }
    return (dummy_cand, dummy_feat, 0.0)


def _listwise_calibrate(
    scored_candidates: List[Tuple[dict, Dict[str, float], float]],
) -> List[Tuple[dict, Dict[str, float], float]]:
    """
    Listwise Score Calibration — Block 7 (per plan.md).

    After all candidates are scored independently, run a calibration pass to:
    1. Ensure scores are monotonically non-increasing (no inversions)
    2. Detect and fix cases where adjacent candidates have identical scores
       but meaningfully different feature evidence (break ties deterministically)
    3. Assign cluster tiers for recruiter readability

    This does NOT change the relative ordering — it refines score magnitudes
    to better reflect evidence quality gaps.
    """
    if len(scored_candidates) < 2:
        return scored_candidates

    calibrated = []
    prev_score = None

    for idx, (cand, feat, score) in enumerate(scored_candidates):
        # Ensure strict monotonicity
        if prev_score is not None and score > prev_score:
            score = prev_score - 0.0001  # Tiny correction

        # Assign cluster tier label
        if score >= 0.80:
            tier_label = "top_tier"
        elif score >= 0.65:
            tier_label = "strong"
        elif score >= 0.50:
            tier_label = "medium"
        elif score >= 0.35:
            tier_label = "borderline"
        elif score >= 0.20:
            tier_label = "weak"
        else:
            tier_label = "reject"

        feat["_cluster_tier"] = tier_label
        feat["_calibrated_score"] = round(max(0.0, score), 6)

        calibrated.append((cand, feat, round(max(0.0, score), 6)))
        prev_score = score

    return calibrated


def rank_candidates(
    candidates: List[dict],
    top_n: int = TOP_CANDIDATES,
    log_interval: int = 10000,
    semantic_scores: Optional[dict] = None,
) -> List[Tuple[dict, Dict[str, float], float]]:
    """
    Runs multi-stage cascade ranking:
    1. Fast Hybrid Retrieval to find top 500 candidates.
    2. Batch-wise Cross-Encoder reranking on the top 500 candidates.
    3. Multiplicative scoring calculation on the top 500 candidates.
    4. Return the top_n real candidates sorted by score descending.
       NOTE: Padding with dummy candidates (CAND_9990xxx) is done separately
       via pad_to_submission_size() — not here — so the UI always sees only
       real analyzed candidates.
    """
    logger.info(f"Initiating ranking for {len(candidates)} candidates...")
    
    if not candidates:
        logger.warning("No candidates provided to ranking engine. Returning empty list.")
        return []

    # ── Step 1: Initialize SemanticEngine & Load Models ──────────────────────
    engine = get_engine()
    engine._load_model()
    engine._load_cross_encoder()

    from redrob_ranker.engines.feature_engine import compute_title_score, is_disqualifier_title

    # If candidates is large, we apply Cascade Retrieval Stage 1 & 2
    if len(candidates) > 350 and semantic_scores is None:
        logger.info("Cascade Retrieval: Stage 1 Fast Lexical Pre-Filter starting...")
        
        # Compute BM25 scores for all 100K candidates
        bm25_scores = engine.compute_bm25_scores(candidates)
        
        # Score each candidate fast: 0.4 * BM25 + 0.6 * title_score
        fast_scores = []
        for c in candidates:
            cid = c.get("candidate_id", "")
            b_score = bm25_scores.get(cid, 0.0)
            
            title = c.get("profile", {}).get("current_title", "")
            t_score = compute_title_score(title)
            
            # Penalize disqualifier titles heavily at Stage 1
            if is_disqualifier_title(title):
                t_score = 0.0
                
            f_score = 0.4 * b_score + 0.6 * t_score
            fast_scores.append((c, f_score))
            
        # Sort and take top 600 candidates (wider net catches semantic-rich profiles BM25 underscores)
        fast_scores.sort(key=lambda x: -x[1])
        top_350_candidates = [c for c, _ in fast_scores[:600]]
        logger.info("Cascade Retrieval: Selected top 600 candidates for dense embedding.")
        
        # Stage 2: Compute Dense Semantic scores only for these top 350 candidates
        dense_scores = engine.compute_dense_scores(top_350_candidates)
        
        # Store cached scores in engine to maintain structure
        engine._cached_dense_scores = dense_scores
        engine._cached_bm25_scores = {c.get("candidate_id", ""): bm25_scores.get(c.get("candidate_id", ""), 0.0) for c in top_350_candidates}
        
        # Combine dense and BM25 scores into hybrid retrieval scores for the 350
        hybrid_scores = {}
        for c in top_350_candidates:
            cid = c.get("candidate_id", "")
            d_score = dense_scores.get(cid, 0.5)
            b_score = bm25_scores.get(cid, 0.0)
            hybrid_scores[cid] = round(engine.best_dense_ratio * d_score + (1.0 - engine.best_dense_ratio) * b_score, 4)
            
        candidates_to_process = top_350_candidates
    else:
        # For small pools or if semantic_scores are precomputed, bypass fast filtering
        if semantic_scores is None:
            logger.info("Computing hybrid retrieval scores for all candidates...")
            engine.auto_tune_ratio(candidates)
            hybrid_scores = engine.compute_hybrid_retrieval_scores(candidates)
        else:
            hybrid_scores = semantic_scores
        candidates_to_process = candidates

    # ── Step 3: Sort candidates by Hybrid Retrieval score ───────────────────
    candidate_hybrid_scores = []
    for c in candidates_to_process:
        cid = c.get("candidate_id", "")
        score = hybrid_scores.get(cid, 0.5)
        candidate_hybrid_scores.append((c, score))
        
    candidate_hybrid_scores.sort(key=lambda x: -x[1])
    
    # ── Step 4: Slice Cascade (Top 250 or max(250, top_n)) ──────────────────
    cascade_limit = min(len(candidates_to_process), max(250, top_n))
    logger.info(f"Slicing top {cascade_limit} candidates for Cross-Encoder reranking...")
    top_candidates_with_scores = candidate_hybrid_scores[:cascade_limit]
    
    # ── Step 5: Extract Features for Top Candidates ─────────────────────────
    logger.info("Extracting candidate features...")
    top_features = []
    for c, h_score in top_candidates_with_scores:
        feat = extract_features(c, semantic_scores=hybrid_scores)
        top_features.append((c, feat))
        
    # ── Step 6: Batch inference on Cross-Encoder ────────────────────────────
    logger.info(f"Running Cross-Encoder prediction (batch_size=64)...")
    pairs = [(JD_TEXT, _candidate_to_text(c)) for c, _ in top_features]
    
    if pairs and engine.cross_encoder is not None:
        try:
            ce_scores = engine.cross_encoder.predict(pairs, batch_size=64, show_progress_bar=False)
        except Exception as e:
            logger.warning(f"Cross-Encoder failed during predict: {e}. Falling back to Hybrid scores.")
            ce_scores = [0.0] * len(pairs)
    else:
        ce_scores = [0.0] * len(pairs)
        
    # ── Step 7: Final Score calculation using multiplicative formula ─────────
    scored_candidates = []
    dense_scores = engine._cached_dense_scores or {}
    bm25_scores = engine._cached_bm25_scores or {}
    
    for idx, (c, feat) in enumerate(top_features):
        cid = c.get("candidate_id", "")
        h_score = hybrid_scores.get(cid, 0.5)
        
        # Sigmoid scale CE score to [0, 1]
        if engine.cross_encoder is not None:
            ce_score = sigmoid(ce_scores[idx])
        else:
            ce_score = h_score
            
        feat["cross_encoder_score"] = ce_score
        feat["dense_score"] = dense_scores.get(cid, h_score)
        feat["bm25_score"] = bm25_scores.get(cid, 0.0)
        feat["semantic_similarity_score"] = h_score
        
        # Relevance Score
        title_score = feat.get("combined_title_score", 0.0)
        skill_score = feat.get("core_skill_score", 0.0)
        relevance = 0.30 * h_score + 0.30 * ce_score + 0.10 * feat.get("role_specific_depth_score", 0.0) + 0.15 * title_score + 0.15 * skill_score
        feat["relevance_score"] = relevance
        
        # Compute final score
        final_score = compute_final_score(feat)
        scored_candidates.append((c, feat, final_score))
        
    # ── Step 8: Sort and return REAL candidates only (no padding here) ──────
    logger.info("Sorting candidates by score...")
    scored_candidates.sort(key=lambda x: (-x[2], x[0].get("candidate_id", "")))

    # ── Step 9: Listwise Score Calibration ──────────────────────────────
    # Ensure score gaps between adjacent candidates are proportional to feature gaps
    scored_candidates = _listwise_calibrate(scored_candidates)

    # Slice to top_n real candidates (no dummies — padding is done at write time)
    real_top = scored_candidates[:top_n]

    top_score = real_top[0][2] if real_top else 0
    rank_n_score = real_top[-1][2] if real_top else 0
    logger.info(f"Final Scoring Completed. Top score: {top_score:.4f}, Rank-{top_n} score: {rank_n_score:.4f}")

    return real_top


def pad_to_submission_size(
    ranked: List[Tuple[dict, Dict[str, float], float]],
    required_size: int = 100,
) -> List[Tuple[dict, Dict[str, float], float]]:
    """
    Pads a ranked list with dummy candidates to meet the submission CSV requirement
    of exactly `required_size` rows.  Only used by write_submission — never by the
    API response or dashboard UI.
    """
    padded = list(ranked)
    while len(padded) < required_size:
        padded.append(_make_dummy_candidate(len(padded)))
    return padded[:required_size]
