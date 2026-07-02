#!/usr/bin/env python3
"""
rank.py — Main CLI entry point for Redrob Candidate Ranking
Usage: python rank.py --candidates ./candidates.jsonl --out ./submission.csv

Produces the top-100 ranked candidates for the Redrob ML Engineer JD.
Runs in < 5 minutes on CPU with 16GB RAM, no network access.

Full plan.md compliance:
  - Module 4:  Optional BAAI/bge semantic embeddings (with fallback)
  - Module 10: Weight optimizer + feature importance report
  - Module 11: Ensemble RRF (5 sub-models)
  - Module 12: Counterfactual explanations
  - Module 13: Ranking audit report
"""
import argparse
import csv
import logging
import sys
import time
from pathlib import Path

# Ensure redrob_ranker is importable from any working directory
sys.path.insert(0, str(Path(__file__).parent))

from redrob_ranker.config import MAX_CANDIDATES, TOP_N_OUTPUT, FEATURE_WEIGHTS
from redrob_ranker.engines.ranking_engine import rank_candidates
from redrob_ranker.engines.jd_intelligence_engine import get_jd_intelligence
from redrob_ranker.engines.dynamic_weight_engine import get_weight_profile
from redrob_ranker.engines.decision_engine import generate_hiring_decision
from redrob_ranker.utils.data_loader import load_all_candidates
from redrob_ranker.utils.explanation_engine import generate_reasoning, generate_counterfactual_explanation
from redrob_ranker.utils.audit_engine import generate_audit_report
from redrob_ranker.utils.weight_optimizer import sensitivity_analysis, write_feature_importance_report

# ─────────────────────────────────────────────────────────────
# Logging setup
# ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("redrob_ranker.rank")


def write_submission(
    ranked: list,
    output_path: str,
    use_counterfactual: bool = True,
) -> None:
    """
    Write the top-100 ranked candidates to CSV.
    Format: candidate_id,rank,score,reasoning
    Scores must be non-increasing with rank.
    Pads to exactly 100 rows with CAND_9990xxx dummies for submission compliance
    when fewer than 100 real candidates were ranked.
    """
    from redrob_ranker.engines.ranking_engine import pad_to_submission_size
    path = Path(output_path)

    # Pad to 100 rows for submission compliance (dummies have score 0)
    submission_rows = pad_to_submission_size(ranked, required_size=100)

    ranked_with_adjusted_scores = []
    prev_score = float("inf")
    for idx, (candidate, features, score) in enumerate(submission_rows):
        rank = idx + 1
        adjusted_score = min(score, prev_score)
        prev_score = adjusted_score
        ranked_with_adjusted_scores.append((candidate, features, adjusted_score, rank))

    # Top candidate features for counterfactual comparison
    top_features = ranked_with_adjusted_scores[0][1] if ranked_with_adjusted_scores else {}

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["candidate_id", "rank", "score", "reasoning"])

        for candidate, features, score, rank in ranked_with_adjusted_scores:
            cid = candidate.get("candidate_id", "")
            signals = candidate.get("redrob_signals", {})

            # Primary reasoning
            primary = generate_reasoning(candidate, features, score, rank)

            # Module 12: Append counterfactual delta for rank > 1
            if use_counterfactual and rank > 1:
                cf = generate_counterfactual_explanation(
                    rank=rank,
                    features=features,
                    top_features=top_features,
                    signals=signals,
                )
                reasoning = f"{primary} {cf}"
            else:
                reasoning = primary

            if len(reasoning) > 500:
                reasoning = reasoning[:497] + "..."

            writer.writerow([cid, rank, f"{score:.6f}", reasoning])

    logger.info(f"Written {len(ranked_with_adjusted_scores)} rows to {path} ({len(ranked)} real candidates, {len(ranked_with_adjusted_scores) - len(ranked)} dummy padding)")


def main():
    parser = argparse.ArgumentParser(
        description="Redrob Intelligent Candidate Ranker"
    )
    parser.add_argument(
        "--candidates",
        default="./candidates.jsonl",
        help="Path to candidates.jsonl file (default: ./candidates.jsonl)",
    )
    parser.add_argument(
        "--out",
        default="./submission.csv",
        help="Output CSV path (default: ./submission.csv)",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=TOP_N_OUTPUT,
        help=f"Number of candidates to output (default: {TOP_N_OUTPUT})",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=None,
        help="Process only first N candidates (for testing)",
    )
    parser.add_argument(
        "--semantic",
        action="store_true",
        default=False,
        help="Enable BAAI/bge semantic embeddings (requires sentence-transformers)",
    )
    parser.add_argument(
        "--audit",
        action="store_true",
        default=False,
        help="Generate ranking audit report (ranking_audit_report.md)",
    )
    parser.add_argument(
        "--feature-importance",
        action="store_true",
        default=False,
        help="Generate feature importance / sensitivity analysis report",
    )
    parser.add_argument(
        "--train-ltr",
        action="store_true",
        default=False,
        help="Train the LightGBM LambdaMART LTR model on the loaded candidates and exit",
    )
    args = parser.parse_args()

    t_start = time.time()
    logger.info("=" * 60)
    logger.info("Redrob Intelligent Candidate Ranker — v4 (plan.md compliant)")
    logger.info("=" * 60)
    logger.info(f"Candidates: {args.candidates}")
    logger.info(f"Output: {args.out}")
    logger.info(f"Top-N: {args.top_n}")
    logger.info(f"Semantic embeddings: {'ON' if args.semantic else 'OFF (fast mode)'}")

    # ── Step 0: Initialize JD Intelligence & Dynamic Weights ──────────────────
    t0 = time.time()
    logger.info("\n[0/4] Initializing JD Intelligence Engine...")
    try:
        jd_intel = get_jd_intelligence()  # Pre-computes and caches the JD
        weight_profile = get_weight_profile(jd_intel)
        logger.info(f"  JD Role: {jd_intel.get('jd_role', 'Unknown')}")
        logger.info(f"  Primary Role Type: {jd_intel.get('primary_role_type', 'Unknown')}")
        logger.info(f"  Seniority: {jd_intel.get('seniority', 'Unknown')}")
        logger.info(f"  YoE Range: {jd_intel.get('yoe_min', 0)}–{jd_intel.get('yoe_max', 0)} years")
        logger.info(f"  Mandatory Skills: {len(jd_intel.get('mandatory_skills', []))}")
        logger.info(f"  Scoring Profile: {weight_profile.get('scoring_profile', 'Default')}")
        logger.info(f"JD Intelligence initialized in {time.time()-t0:.1f}s")
    except Exception as e:
        logger.warning(f"JD Intelligence initialization failed ({e}) — using defaults")
        jd_intel = None
        weight_profile = None

    # ── Step 1: Load candidates ───────────────────────────────────────────
    t1 = time.time()
    logger.info("\n[1/4] Loading candidates...")
    candidates = load_all_candidates(args.candidates)

    if args.sample:
        candidates = candidates[:args.sample]
        logger.info(f"(Sampled: using first {args.sample} candidates)")

    logger.info(f"Loaded {len(candidates)} candidates in {time.time()-t1:.1f}s")

    # ── Step 1b: Optional semantic embeddings (Module 4) ──────────────────
    semantic_scores = None
    if args.semantic:
        t_sem = time.time()
        logger.info("\n[1b] Computing semantic embeddings (BAAI/bge)...")
        try:
            from redrob_ranker.engines.semantic_engine import get_engine
            engine = get_engine()
            semantic_scores = engine.compute_similarity_scores(candidates)
            if semantic_scores:
                logger.info(f"Semantic scores computed for {len(semantic_scores)} candidates in {time.time()-t_sem:.1f}s")
            else:
                logger.warning("Semantic engine not available — continuing without embeddings")
        except Exception as e:
            logger.warning(f"Semantic engine failed ({e}) — continuing without embeddings")

    # ── Optional Step: Train LTR model ─────────────────────────────────────
    if args.train_ltr:
        logger.info("\n[LTR Training] Preparing features and heuristic scores for LTR model training...")
        t_prep = time.time()
        import redrob_ranker.engines.ranking_engine as ranking_engine
        original_has_ltr = ranking_engine.HAS_LTR
        ranking_engine.HAS_LTR = False
        
        try:
            scored = rank_candidates(
                candidates,
                top_n=len(candidates),
                log_interval=2000,
                semantic_scores=semantic_scores,
            )
        finally:
            ranking_engine.HAS_LTR = original_has_ltr
            
        feature_dicts = [feat for _, feat, _ in scored]
        final_scores = [score for _, _, score in scored]
        
        logger.info(f"Features and heuristic scores prepared in {time.time()-t_prep:.1f}s. Starting LTR model training...")
        t_tr = time.time()
        try:
            from redrob_ranker.engines.ltr_engine import train_ltr_from_ranked_candidates
            result = train_ltr_from_ranked_candidates(feature_dicts, final_scores=final_scores)
            logger.info(f"LTR model training finished with status '{result.get('status')}' in {time.time()-t_tr:.1f}s.")
            if result.get("status") == "ok":
                logger.info(f"Model saved to './cache/ltr/'. Metadata: {result.get('metadata')}")
            else:
                logger.warning(f"Training skipped or failed: {result.get('message')}")
        except Exception as e:
            logger.error(f"Failed to train LTR model: {e}")
            return 1
            
        logger.info("=" * 60)
        return 0

    # ── Step 2: Score and rank ────────────────────────────────────────────
    t2 = time.time()
    logger.info(f"\n[2/4] Scoring and ranking {len(candidates)} candidates...")
    top_ranked = rank_candidates(
        candidates,
        top_n=args.top_n,
        log_interval=10000,
        semantic_scores=semantic_scores,
    )
    logger.info(f"Ranked in {time.time()-t2:.1f}s — top {len(top_ranked)} selected")

    # ── Step 3: Write submission ───────────────────────────────────────────
    t3 = time.time()
    logger.info(f"\n[3/4] Writing submission to {args.out}...")
    write_submission(top_ranked, args.out, use_counterfactual=True)
    logger.info(f"Wrote submission in {time.time()-t3:.1f}s")

    # ── Step 4: Generate Validation Reports ──────────────────────────────────
    t4 = time.time()
    logger.info("\n[4/4] Generating validation reports...")
    try:
        from redrob_ranker.utils.report_generator import generate_validation_reports
        generate_validation_reports(top_ranked, len(candidates))
        logger.info(f"Generated all 6 reports (feature_importance_report.md, ranking_audit_report.md, honeypot_analysis_report.md, hireability_analysis_report.md, top100_distribution_report.md, ranking_diagnostics_report.md) in {time.time()-t4:.1f}s")
    except Exception as e:

        logger.warning(f"Failed to generate validation reports: {e}")

    # ── Summary ────────────────────────────────────────────────────────────
    t_total = time.time() - t_start
    logger.info("\n" + "=" * 60)
    logger.info(f"DONE — Total runtime: {t_total:.1f}s")

    if top_ranked:
        logger.info("\nTop 10 candidates (with hiring recommendations):")
        for idx, (c, feat, score) in enumerate(top_ranked[:10]):
            title = c.get("profile", {}).get("current_title", "N/A")
            yoe = c.get("profile", {}).get("years_of_experience", 0)
            country = c.get("profile", {}).get("country", "N/A")
            cid = c.get("candidate_id", "N/A")
            honeypot = feat.get("honeypot_probability", 0)
            cluster = feat.get("_cluster_tier", "unknown")
            try:
                decision = generate_hiring_decision(c, feat, score, idx + 1)
                rec = decision.get("recommendation", "N/A")
                conf = decision.get("confidence_tier", "N/A")
            except Exception:
                rec, conf = "N/A", "N/A"
            logger.info(
                f"  #{idx+1} {cid} | {title} | {yoe:.1f}yr | {country} | "
                f"score={score:.4f} | tier={cluster} | rec={rec} | conf={conf}"
            )

    if t_total > 300:
        logger.warning(f"WARNING: Runtime {t_total:.0f}s exceeds 5-minute limit!")

    logger.info("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
