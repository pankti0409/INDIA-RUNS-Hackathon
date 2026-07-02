"""
reranking_engine.py — Block 8: Cooperative Comparative Reranking Engine

Performs deep recruiter-style comparative reranking on the top finalists from
the candidate pool, prioritizing validated evidence, technical depth, and
ownership quality to optimize the final shortlist ordering.
"""

import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)


class DeepRerankingEngine:
    """Cooperative comparative reranking engine for top-N finalists."""
    def __init__(self, rerank_limit: int = 100):
        self.rerank_limit = rerank_limit

    def rerank(
        self, 
        scored_candidates: List[Tuple[Dict[str, Any], Dict[str, Any], float]]
    ) -> List[Tuple[Dict[str, Any], Dict[str, Any], float]]:
        """
        Reranks only the top-N candidates using deep comparative reasoning.
        Non-top-N candidates retain their original order.
        """
        if len(scored_candidates) <= 1:
            return scored_candidates

        # Slice top candidates to rerank
        limit = min(len(scored_candidates), self.rerank_limit)
        to_rerank = scored_candidates[:limit]
        remaining = scored_candidates[limit:]

        logger.info(f"Running deep comparative reranking on top {limit} candidates...")

        # Compute comparative quality index for each finalist
        reranked_finalists = []
        for c, feat, original_score in to_rerank:
            # Multi-dimensional comparative markers
            tech_depth = float(feat.get("core_skill_score", 0.5)) + float(feat.get("role_specific_depth_score", 0.5))
            scale_complexity = float(feat.get("scale_evidence_score", 0.0)) + float(feat.get("project_complexity_score", 0.0))
            ownership = float(feat.get("leadership_evidence_score", 0.0)) + float(feat.get("production_at_scale", 0.0)) * 0.5
            stability = float(feat.get("career_growth_score", 0.5)) + float(feat.get("career_stability_score", 0.5))
            
            # Combine into a robust comparative metric
            comparative_quality = 0.35 * tech_depth + 0.30 * scale_complexity + 0.20 * ownership + 0.15 * stability
            
            # Blend original model score (70%) with comparative quality (30%)
            blended_rerank_score = 0.70 * original_score + 0.30 * comparative_quality
            feat["comparative_quality_score"] = round(comparative_quality, 4)
            feat["rerank_blended_score"] = round(blended_rerank_score, 6)
            
            reranked_finalists.append((c, feat, blended_rerank_score))

        # Sort the top-N finalists by the new blended rerank score
        reranked_finalists.sort(key=lambda x: (-x[2], x[0].get("candidate_id", "")))

        # Re-attach the comparative explanations between adjacent ranked finalists
        for idx in range(len(reranked_finalists)):
            c, feat, score = reranked_finalists[idx]
            feat["final_rank"] = idx + 1
            
            if idx == 0:
                feat["comparative_reason"] = "Ranked #1: Demonstrates maximum overall technical capability, scale fit, and leadership alignment."
            else:
                # Compare to the candidate immediately above
                prev_c, prev_feat, prev_score = reranked_finalists[idx - 1]
                diffs = []
                
                # Check skill difference
                s_diff = float(prev_feat.get("core_skill_score", 0.5)) - float(feat.get("core_skill_score", 0.5))
                if s_diff > 0.05:
                    diffs.append(f"retrieval/AI skill depth lower by {int(s_diff * 100)}%")
                    
                # Check experience difference
                exp_diff = float(prev_feat.get("yoe_score", 0.5)) - float(feat.get("yoe_score", 0.5))
                if exp_diff > 0.05:
                    diffs.append(f"years of experience fit lower by {int(exp_diff * 100)}%")
                    
                # Check notice period difference
                n_diff = float(prev_feat.get("notice_score", 0.5)) - float(feat.get("notice_score", 0.5))
                if n_diff > 0.05:
                    diffs.append(f"notice period lower by {int(n_diff * 100)}%")
                    
                # Check career growth difference
                g_diff = float(prev_feat.get("career_growth_score", 0.5)) - float(feat.get("career_growth_score", 0.5))
                if g_diff > 0.05:
                    diffs.append(f"career growth lower by {int(g_diff * 100)}%")
                    
                if diffs:
                    feat["comparative_reason"] = f"Ranked #{idx+1} vs #{idx}: " + "; ".join(diffs) + "."
                else:
                    feat["comparative_reason"] = f"Ranked #{idx+1} vs #{idx}: Marginal differences in experience and technical specialization."

        # Recombine the reranked finalists with the rest of the pool
        return reranked_finalists + remaining


# Module level singleton
_reranking_engine: DeepRerankingEngine = None

def get_reranking_engine() -> DeepRerankingEngine:
    global _reranking_engine
    if _reranking_engine is None:
        _reranking_engine = DeepRerankingEngine()
    return _reranking_engine
