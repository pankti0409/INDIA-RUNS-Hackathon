"""
audit_engine.py — Module 13: Ranking Audit Engine
Generates distribution reports, bias analysis, and feature contribution summaries.
"""
import json
import logging
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


def _bucket_score(score: float) -> str:
    if score >= 0.90: return "90-100%"
    if score >= 0.80: return "80-90%"
    if score >= 0.70: return "70-80%"
    if score >= 0.60: return "60-70%"
    return "<60%"


def _bucket_yoe(yoe: float) -> str:
    if yoe < 2:  return "0-2yr"
    if yoe < 4:  return "2-4yr"
    if yoe < 6:  return "4-6yr"
    if yoe < 9:  return "6-9yr"
    if yoe < 12: return "9-12yr"
    return "12yr+"


def generate_audit_report(
    top_ranked: List[Tuple[dict, dict, float]],
    output_path: str = "./ranking_audit_report.md",
) -> str:
    """
    Generate a comprehensive audit report for the top-100 ranking.
    Returns the report as a string and writes it to disk.
    """
    lines = ["# Ranking Audit Report\n"]
    lines.append(f"**Candidates analysed:** {len(top_ranked)}\n")

    # ── Score Distribution ────────────────────────────────────────────────
    score_buckets = Counter(_bucket_score(score) for _, _, score in top_ranked)
    lines.append("## Score Distribution\n")
    lines.append("| Score Band | Count |")
    lines.append("|-----------|-------|")
    for band in ["90-100%", "80-90%", "70-80%", "60-70%", "<60%"]:
        lines.append(f"| {band} | {score_buckets.get(band, 0)} |")
    lines.append("")

    # ── Title Distribution ────────────────────────────────────────────────
    title_counts: Counter = Counter()
    for cand, _, _ in top_ranked:
        title = cand.get("profile", {}).get("current_title", "Unknown")
        # Simplify to category
        tl = title.lower()
        if "ml engineer" in tl or "machine learning engineer" in tl:
            title_counts["ML Engineer"] += 1
        elif "ai engineer" in tl or "ai/ml" in tl:
            title_counts["AI Engineer"] += 1
        elif "nlp engineer" in tl:
            title_counts["NLP Engineer"] += 1
        elif "search engineer" in tl or "ranking engineer" in tl:
            title_counts["Search/Ranking Engineer"] += 1
        elif "data scientist" in tl:
            title_counts["Data Scientist"] += 1
        elif "applied scientist" in tl:
            title_counts["Applied Scientist"] += 1
        elif "recommendation" in tl:
            title_counts["Recommendation Engineer"] += 1
        else:
            title_counts[title[:30]] += 1

    lines.append("## Title Distribution\n")
    lines.append("| Title Category | Count |")
    lines.append("|----------------|-------|")
    for title, count in title_counts.most_common(15):
        lines.append(f"| {title} | {count} |")
    lines.append("")

    # ── Experience Distribution ────────────────────────────────────────────
    yoe_buckets: Counter = Counter()
    for cand, _, _ in top_ranked:
        yoe = cand.get("profile", {}).get("years_of_experience", 0)
        yoe_buckets[_bucket_yoe(yoe)] += 1

    lines.append("## Experience Distribution\n")
    lines.append("| YoE Bucket | Count |")
    lines.append("|------------|-------|")
    for band in ["0-2yr", "2-4yr", "4-6yr", "6-9yr", "9-12yr", "12yr+"]:
        lines.append(f"| {band} | {yoe_buckets.get(band, 0)} |")
    lines.append("")

    # ── Location Distribution ─────────────────────────────────────────────
    country_counts: Counter = Counter()
    for cand, _, _ in top_ranked:
        country = cand.get("profile", {}).get("country", "Unknown")
        country_counts[country] += 1

    lines.append("## Location Distribution\n")
    lines.append("| Country | Count |")
    lines.append("|---------|-------|")
    for country, count in country_counts.most_common(10):
        lines.append(f"| {country} | {count} |")
    lines.append("")

    # ── Honeypot Analysis ─────────────────────────────────────────────────
    honeypot_counts = Counter()
    for _, feat, _ in top_ranked:
        hp = feat.get("honeypot_probability", 0)
        if hp >= 0.5:
            honeypot_counts["high (≥0.5)"] += 1
        elif hp >= 0.25:
            honeypot_counts["medium (0.25-0.5)"] += 1
        else:
            honeypot_counts["clean (<0.25)"] += 1

    lines.append("## Honeypot Analysis\n")
    lines.append("| Risk Level | Count |")
    lines.append("|------------|-------|")
    for level in ["clean (<0.25)", "medium (0.25-0.5)", "high (≥0.5)"]:
        lines.append(f"| {level} | {honeypot_counts.get(level, 0)} |")
    lines.append("")

    # ── Behavioral Availability ───────────────────────────────────────────
    open_to_work = sum(
        1 for cand, _, _ in top_ranked
        if cand.get("redrob_signals", {}).get("open_to_work_flag", False)
    )
    avg_notice = sum(
        cand.get("redrob_signals", {}).get("notice_period_days", 90)
        for cand, _, _ in top_ranked
    ) / max(1, len(top_ranked))

    avg_response = sum(
        cand.get("redrob_signals", {}).get("recruiter_response_rate", 0)
        for cand, _, _ in top_ranked
    ) / max(1, len(top_ranked))

    lines.append("## Behavioral Signals — Top 100 Summary\n")
    lines.append(f"- **Open to Work:** {open_to_work}/100 ({open_to_work}%)")
    lines.append(f"- **Avg Notice Period:** {avg_notice:.0f} days")
    lines.append(f"- **Avg Recruiter Response Rate:** {avg_response:.0%}")
    lines.append("")

    # ── Feature Contribution (avg per ranked candidate) ───────────────────
    feature_keys = [
        "title_score", "core_skill_score", "yoe_score", "product_company_score",
        "ai_experience_score", "availability_score", "engagement_score",
        "responsiveness_score", "education_score", "github_score",
        "ai_assessment_score", "career_growth_score", "ontology_skill_score",
        "semantic_similarity_score", "hireability_score", "promotion_velocity",
    ]

    lines.append("## Feature Contribution (Top-100 Averages)\n")
    lines.append("| Feature | Avg Score |")
    lines.append("|---------|-----------|")
    for key in feature_keys:
        vals = [feat.get(key, 0) for _, feat, _ in top_ranked if key in feat]
        if vals:
            avg = sum(vals) / len(vals)
            lines.append(f"| {key} | {avg:.3f} |")
    lines.append("")

    # ── Company Type Distribution ─────────────────────────────────────────
    product_count = sum(
        1 for _, feat, _ in top_ranked
        if feat.get("has_product_company", 0) > 0.5
    )
    consulting_count = sum(
        1 for _, feat, _ in top_ranked
        if feat.get("is_pure_consulting", 0) > 0.5
    )
    lines.append("## Company Background\n")
    lines.append(f"- **Product company experience:** {product_count}/100")
    lines.append(f"- **Pure consulting background:** {consulting_count}/100")
    lines.append("")

    lines.append("---")
    lines.append("*Generated automatically by Ranking Audit Engine*")

    report = "\n".join(lines)
    Path(output_path).write_text(report, encoding="utf-8")
    logger.info(f"Audit report written to {output_path}")
    return report
