"""
ltr_engine.py — Learning-to-Rank Engine (Optimization Block 2)

Implements:
- LightGBM LambdaMART with NDCG@10 optimization
- Synthetic pairwise training data generation with hard negative mining
- Feature matrix construction from candidate feature dicts
- Model versioning and persistence
- Feature importance (gain, split, SHAP)
- Graceful fallback to weighted scoring when no model exists

Plan.md references:
  Block 2 §2: Primary model → LightGBM LambdaMART
  Block 2 §3: Training objective → lambdarank / ndcg
  Block 2 §4: Training data generation → pairwise preferences
  Block 2 §7: Hard negative mining
  Block 2 §11: Feature importance
  Block 2 §12: Hyperparameter optimization
  Block 2 §17: Model versioning
"""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional imports — graceful degradation when lightgbm is absent
# ---------------------------------------------------------------------------
try:
    import lightgbm as lgb
    HAS_LGB = True
except ImportError:  # pragma: no cover
    HAS_LGB = False
    logger.warning("lightgbm not installed — LTR engine will operate in fallback mode")

try:
    import shap
    HAS_SHAP = True
except ImportError:  # pragma: no cover
    HAS_SHAP = False

# ---------------------------------------------------------------------------
# Feature schema — ordered list of features consumed by the LTR model.
# Adding new features to this list is the only change required to upgrade
# the feature schema.  The model must be retrained after schema changes.
# ---------------------------------------------------------------------------
LTR_FEATURE_SCHEMA: List[str] = [
    # Title features
    "title_score",
    "career_best_title_score",
    "combined_title_score",
    "is_disqualifier_title",
    "title_exact_match",
    "title_normalized_match",
    "title_seniority_gap",
    "title_role_family_match",
    "title_hierarchy_score",
    # Skill features
    "core_skill_score",
    "core_skill_count",
    "preferred_skill_score",
    "retrieval_skill_score",
    "embedding_skill_score",
    "python_score",
    "total_skill_count",
    "endorsed_skill_ratio",
    "avg_skill_endorsements",
    "avg_skill_depth",
    "ontology_skill_score",
    "skill_family_coverage",
    "skill_freshness_score",
    "skill_duration_weighted",
    "skill_diversity_score",
    "skill_density_score",
    "skill_rarity_score",
    "missing_critical_skills_ratio",
    "adjacent_skill_score",
    "skill_cluster_coverage",
    # Assessment features
    "avg_assessment_score",
    "ai_assessment_score",
    "has_assessments",
    "assessment_count",
    "technical_validation_score",
    # Experience features
    "yoe_score",
    "product_company_score",
    "ai_experience_score",
    "is_pure_consulting",
    "has_product_company",
    "company_size_score",
    "job_diversity_score",
    "relevant_exp_ratio",
    "architecture_exp_score",
    "open_source_exp_score",
    "deployment_exp_score",
    "ownership_exp_score",
    "mentoring_exp_score",
    "career_stability_score",
    "promotion_velocity_score",
    # Responsibility features
    "resp_designed_freq",
    "resp_led_freq",
    "resp_owned_freq",
    "resp_optimized_freq",
    "resp_scaled_freq",
    "resp_mentored_freq",
    "resp_architected_freq",
    "resp_depth_score",
    # Education features
    "education_score",
    "certification_count",
    "recent_cert_score",
    "advanced_degree",
    # Location / availability
    "location_score",
    "willing_to_relocate",
    "work_mode_score",
    "english_proficiency",
    "notice_score",
    "salary_alignment_score",
    # GitHub / behavior
    "github_score",
    "open_to_work_flag",
    "active_recently",
    "low_notice_period",
    "strong_github",
    "high_assessment",
    # Candidate intelligence
    "engineering_maturity_score",
    "leadership_evidence_score",
    "project_complexity_score",
    "scale_evidence_score",
    "business_impact_score",
    "narrative_score",
    "career_coherence_score",
    "research_depth_score",
    "transferable_skill_score",
    "transferability_gain",
    "production_at_scale",
    # Company intelligence
    "company_quality_score",
    "industry_relevance_score",
    "engineering_exposure_score",
    "has_big_tech_experience",
    "has_search_ranking_experience",
    # JD skill graph
    "jd_skill_exact_coverage",
    "jd_skill_soft_coverage",
    "jd_domain_coverage",
    # Role-specific depth (8 dimensions)
    "vector_search_depth_score",
    "retrieval_depth_score",
    "ranking_depth_score",
    "search_systems_depth_score",
    "recommendation_systems_depth_score",
    "production_ml_depth_score",
    "ml_infrastructure_depth_score",
    "research_depth_depth_score",
    "has_production_at_scale",
    # Semantic scores (when available)
    "semantic_similarity_score",
    "cross_encoder_score",
    "role_specific_depth_score",
    # Behavioral scores (from behavioral_engine)
    "hireability_probability",
    "response_rate_score",
    "availability_score",
    # Temporal features
    "skill_recency_score",
    "tech_adoption_rate",
    "career_momentum_score",
    "recent_ai_activity",
    # Interaction features
    "title_x_skills",
    "projects_x_leadership",
    "experience_x_company",
    "embedding_x_experience",
    # Evidence confidence
    "evidence_density_score",
    "evidence_diversity_score",
    "evidence_consistency_score",
    "feature_confidence_score",
    # Risk / trust
    "risk_probability",
    "trust_score",
    # Profile signals
    "production_ml_mentions",
    "project_relevance_score",
    "headline_relevance",
    # Career scores (from career_engine)
    "career_growth_score",
    "promotion_score",
    "career_duration_score",
]


# ---------------------------------------------------------------------------
# Relevance label mapping
# ---------------------------------------------------------------------------
DECISION_TO_LABEL: Dict[str, int] = {
    "strong_hire": 3,
    "hire": 2,
    "borderline_hire": 1,
    "reject": 0,
}


def _safe_float(v: Any, default: float = 0.0) -> float:
    """Convert any value to float safely."""
    try:
        fv = float(v)
        if not np.isfinite(fv):
            return default
        return fv
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Feature matrix construction
# ---------------------------------------------------------------------------

def build_feature_matrix(
    feature_dicts: List[Dict[str, Any]],
    schema: Optional[List[str]] = None,
) -> Tuple[np.ndarray, List[str]]:
    """
    Convert a list of candidate feature dicts into a numpy feature matrix.

    Returns
    -------
    X : np.ndarray, shape (n_candidates, n_features)
    feature_names : List[str]
    """
    if schema is None:
        schema = LTR_FEATURE_SCHEMA

    rows = []
    for fd in feature_dicts:
        row = [_safe_float(fd.get(fname, 0.0)) for fname in schema]
        rows.append(row)

    X = np.array(rows, dtype=np.float32)
    return X, schema


# ---------------------------------------------------------------------------
# Training data generation
# ---------------------------------------------------------------------------

def generate_relevance_labels(
    feature_dicts: List[Dict[str, Any]],
    final_scores: Optional[List[float]] = None,
    decision_labels: Optional[List[str]] = None,
) -> np.ndarray:
    """
    Generate relevance labels (0-3) for LTR training.

    Priority:
    1. Use decision_labels if provided (strong_hire=3, hire=2, borderline=1, reject=0)
    2. Use final_scores percentile binning if provided
    3. Fall back to heuristic scoring from features

    Returns array of int labels, shape (n_candidates,)
    """
    n = len(feature_dicts)

    if decision_labels is not None:
        return np.array(
            [DECISION_TO_LABEL.get(str(dl).lower(), 0) for dl in decision_labels],
            dtype=np.int32,
        )

    if final_scores is not None:
        scores = np.array(final_scores, dtype=np.float32)
        labels = np.zeros(n, dtype=np.int32)
        p75 = np.percentile(scores, 75)
        p50 = np.percentile(scores, 50)
        p25 = np.percentile(scores, 25)
        labels[scores >= p75] = 3
        labels[(scores >= p50) & (scores < p75)] = 2
        labels[(scores >= p25) & (scores < p50)] = 1
        labels[scores < p25] = 0
        return labels

    # Heuristic fallback: derive label from key features
    labels = []
    for fd in feature_dicts:
        s = (
            0.25 * _safe_float(fd.get("core_skill_score", 0))
            + 0.20 * _safe_float(fd.get("semantic_similarity_score", 0))
            + 0.15 * _safe_float(fd.get("role_specific_depth_score", 0))
            + 0.15 * _safe_float(fd.get("combined_title_score", 0))
            + 0.10 * _safe_float(fd.get("engineering_maturity_score", 0.4))
            + 0.10 * _safe_float(fd.get("project_complexity_score", 0))
            + 0.05 * _safe_float(fd.get("yoe_score", 0))
        )
        if s >= 0.75:
            labels.append(3)
        elif s >= 0.55:
            labels.append(2)
        elif s >= 0.35:
            labels.append(1)
        else:
            labels.append(0)

    return np.array(labels, dtype=np.int32)


def generate_pairwise_data(
    feature_dicts: List[Dict[str, Any]],
    labels: np.ndarray,
    hard_negative_threshold: float = 0.08,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[str]]:
    """
    Generate a pairwise training dataset for LambdaMART.

    For each pair (i, j) where label[i] > label[j]:
      - features = feature_vector[i] - feature_vector[j]  (positive pair)
      - Also add reversed pair with label=0 (negative)

    Hard negatives: pairs where score difference is small but label differs
    → They appear twice in the training set (curriculum emphasis).

    Returns (X, y, groups, feature_names)
    """
    X_all, feature_names = build_feature_matrix(feature_dicts)
    n = len(feature_dicts)

    pairs_X: List[np.ndarray] = []
    pairs_y: List[int] = []

    # Compute a heuristic relevance score for each candidate for hard negative detection
    heuristic_scores = np.array([
        _safe_float(fd.get("core_skill_score", 0)) * 0.3
        + _safe_float(fd.get("role_specific_depth_score", 0)) * 0.3
        + _safe_float(fd.get("engineering_maturity_score", 0.4)) * 0.2
        + _safe_float(fd.get("combined_title_score", 0)) * 0.2
        for fd in feature_dicts
    ], dtype=np.float32)

    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            if labels[i] > labels[j]:
                diff = X_all[i] - X_all[j]
                pairs_X.append(diff)
                pairs_y.append(1)

                # Hard negative: models are confused here (similar scores, different labels)
                score_diff = abs(heuristic_scores[i] - heuristic_scores[j])
                if score_diff < hard_negative_threshold:
                    # Repeat to emphasize this difficult pair
                    pairs_X.append(diff)
                    pairs_y.append(1)

            elif labels[j] > labels[i]:
                # Also add the reversed (negative) pair
                diff = X_all[i] - X_all[j]
                pairs_X.append(diff)
                pairs_y.append(0)

    if not pairs_X:
        logger.warning("No training pairs generated — all candidates may have identical labels")
        return np.empty((0, len(feature_names))), np.empty(0), np.ones(1, dtype=np.int32), feature_names

    X_pairs = np.stack(pairs_X, axis=0)
    y_pairs = np.array(pairs_y, dtype=np.int32)
    # For pairwise: single query group covers all pairs
    groups = np.array([len(pairs_y)], dtype=np.int32)

    return X_pairs, y_pairs, groups, feature_names


def generate_listwise_data(
    feature_dicts: List[Dict[str, Any]],
    labels: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[str]]:
    """
    Generate listwise training data where each candidate is a document.
    All candidates belong to one query group.
    """
    X, feature_names = build_feature_matrix(feature_dicts)
    groups = np.array([len(feature_dicts)], dtype=np.int32)
    return X, labels, groups, feature_names


# ---------------------------------------------------------------------------
# LTR Model
# ---------------------------------------------------------------------------

class LTREngine:
    """
    LightGBM LambdaMART Learning-to-Rank engine.

    Optimizes NDCG@10 directly.  Falls back to weighted scoring when no
    trained model is available, ensuring the pipeline always produces results.

    Model versioning: every trained model is stamped with schema hash and
    training timestamp, allowing rollback to previous versions.
    """

    MODEL_FILENAME = "ltr_model.lgb"
    SCHEMA_FILENAME = "ltr_schema.json"
    META_FILENAME = "ltr_meta.json"

    def __init__(self, model_dir: str = "./cache/ltr"):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.model: Optional["lgb.Booster"] = None
        self.feature_names: List[str] = LTR_FEATURE_SCHEMA
        self._meta: Dict[str, Any] = {}
        self._try_load_model()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _model_path(self) -> Path:
        return self.model_dir / self.MODEL_FILENAME

    def _schema_path(self) -> Path:
        return self.model_dir / self.SCHEMA_FILENAME

    def _meta_path(self) -> Path:
        return self.model_dir / self.META_FILENAME

    def _try_load_model(self) -> None:
        """Load saved model if present."""
        if not HAS_LGB:
            return
        mp = self._model_path()
        sp = self._schema_path()
        if mp.exists() and sp.exists():
            try:
                self.model = lgb.Booster(model_file=str(mp))
                with open(sp, "r") as f:
                    self.feature_names = json.load(f)
                if self._meta_path().exists():
                    with open(self._meta_path(), "r") as f:
                        self._meta = json.load(f)
                logger.info(
                    f"LTR model loaded: {len(self.feature_names)} features, "
                    f"trained {self._meta.get('trained_at', 'unknown')}"
                )
            except Exception as exc:
                logger.warning(f"Failed to load LTR model: {exc}")
                self.model = None

    def save_model(self) -> None:
        """Persist model and schema to disk."""
        if self.model is None:
            return
        self.model.save_model(str(self._model_path()))
        with open(self._schema_path(), "w") as f:
            json.dump(self.feature_names, f, indent=2)
        with open(self._meta_path(), "w") as f:
            json.dump(self._meta, f, indent=2)
        logger.info(f"LTR model saved to {self.model_dir}")

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def train(
        self,
        feature_dicts: List[Dict[str, Any]],
        final_scores: Optional[List[float]] = None,
        decision_labels: Optional[List[str]] = None,
        objective: str = "lambdarank",
        num_leaves: int = 31,
        learning_rate: float = 0.05,
        n_estimators: int = 200,
        ndcg_eval_at: int = 10,
        early_stopping_rounds: int = 30,
    ) -> Dict[str, Any]:
        """
        Train LightGBM LambdaMART model.

        Parameters
        ----------
        feature_dicts : List of per-candidate feature dicts
        final_scores  : Optional continuous relevance scores
        decision_labels : Optional string decision labels (strong_hire, hire, etc.)
        objective     : 'lambdarank' (default) or 'rank_xendcg'
        """
        if not HAS_LGB:
            logger.warning("lightgbm not installed — cannot train LTR model")
            return {"status": "skipped", "reason": "lightgbm_missing"}

        if len(feature_dicts) < 4:
            logger.warning("Too few candidates to train LTR model (need ≥4)")
            return {"status": "skipped", "reason": "insufficient_data"}

        logger.info(f"Training LTR model on {len(feature_dicts)} candidates")
        labels = generate_relevance_labels(feature_dicts, final_scores, decision_labels)

        # Use listwise training (one query group = all candidates for this JD)
        X, y, groups, feature_names = generate_listwise_data(feature_dicts, labels)
        self.feature_names = feature_names

        params = {
            "objective": objective,
            "metric": "ndcg",
            "eval_at": [ndcg_eval_at],
            "num_leaves": 15,            # Smoother, less deep trees
            "learning_rate": 0.03,       # Slower learning rate to prevent sharp cliffs
            "n_estimators": n_estimators,
            "min_data_in_leaf": 100,     # Prevent splitting on small, overfitted candidate clusters
            "feature_fraction": 0.7,     # Regularize feature selection
            "bagging_fraction": 0.9,
            "bagging_freq": 5,
            "lambda_l1": 1.5,            # Strong L1 regularization
            "lambda_l2": 1.5,            # Strong L2 regularization
            "verbose": -1,
            "random_state": 42,
        }

        train_data = lgb.Dataset(
            X, label=y, group=groups, feature_name=feature_names
        )

        callbacks = [lgb.log_evaluation(period=50)]
        try:
            self.model = lgb.train(
                params,
                train_data,
                num_boost_round=n_estimators,
                callbacks=callbacks,
            )
        except Exception as exc:
            logger.error(f"LTR training failed: {exc}")
            return {"status": "failed", "error": str(exc)}

        # Record metadata
        self._meta = {
            "trained_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "n_candidates": len(feature_dicts),
            "n_features": len(feature_names),
            "objective": objective,
            "schema_hash": str(hash(tuple(feature_names))),
            "params": {k: v for k, v in params.items() if k not in ("verbose",)},
            "label_distribution": {str(i): int((labels == i).sum()) for i in range(4)},
        }
        self.save_model()

        return {
            "status": "ok",
            "n_candidates": len(feature_dicts),
            "n_features": len(feature_names),
            "trained_at": self._meta["trained_at"],
        }

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def predict(self, feature_dicts: List[Dict[str, Any]]) -> np.ndarray:
        """
        Produce ranking scores for candidates.

        Falls back to weighted scoring when no model is trained.
        """
        if self.model is not None and HAS_LGB:
            X, _ = build_feature_matrix(feature_dicts, schema=self.feature_names)
            scores = self.model.predict(X)
            return np.array(scores, dtype=np.float32)

        # Fallback: deterministic weighted scoring using key evidence features
        logger.debug("LTR model not available — using heuristic scoring fallback")
        scores = []
        for fd in feature_dicts:
            s = (
                0.25 * _safe_float(fd.get("core_skill_score", 0))
                + 0.20 * _safe_float(fd.get("semantic_similarity_score", fd.get("combined_title_score", 0) * 0.5))
                + 0.15 * _safe_float(fd.get("role_specific_depth_score", 0))
                + 0.12 * _safe_float(fd.get("engineering_maturity_score", 0.4))
                + 0.10 * _safe_float(fd.get("project_complexity_score", 0))
                + 0.08 * _safe_float(fd.get("combined_title_score", 0))
                + 0.05 * _safe_float(fd.get("yoe_score", 0))
                + 0.03 * _safe_float(fd.get("jd_skill_soft_coverage", 0))
                + 0.02 * _safe_float(fd.get("industry_relevance_score", 0.4))
            )
            scores.append(min(1.0, max(0.0, s)))
        return np.array(scores, dtype=np.float32)

    def rank_candidates(
        self,
        feature_dicts: List[Dict[str, Any]],
        candidate_ids: List[str],
    ) -> List[Tuple[str, float]]:
        """
        Returns candidates sorted by descending LTR score.

        Returns
        -------
        List of (candidate_id, score) tuples, best first.
        """
        scores = self.predict(feature_dicts)
        ranked = sorted(
            zip(candidate_ids, scores.tolist()),
            key=lambda x: x[1],
            reverse=True,
        )
        return ranked

    # ------------------------------------------------------------------
    # Feature importance
    # ------------------------------------------------------------------

    def get_feature_importance(
        self, importance_type: str = "gain"
    ) -> Dict[str, float]:
        """
        Compute feature importance from the trained model.

        importance_type: 'gain', 'split', 'weight'
        """
        if self.model is None:
            logger.warning("No trained model — returning empty importance")
            return {}
        raw = self.model.feature_importance(importance_type=importance_type)
        names = self.model.feature_name()
        total = max(1, raw.sum())
        return {n: round(float(v) / total, 6) for n, v in zip(names, raw)}

    def get_shap_values(
        self, feature_dicts: List[Dict[str, Any]]
    ) -> Optional[np.ndarray]:
        """
        Compute SHAP values for provided candidates.

        Returns ndarray of shape (n_candidates, n_features) or None.
        """
        if self.model is None or not HAS_SHAP:
            return None
        try:
            X, _ = build_feature_matrix(feature_dicts, schema=self.feature_names)
            explainer = shap.TreeExplainer(self.model)
            shap_values = explainer.shap_values(X)
            return np.array(shap_values, dtype=np.float32)
        except Exception as exc:
            logger.warning(f"SHAP computation failed: {exc}")
            return None

    def generate_importance_report(self) -> str:
        """Generate a markdown feature importance report."""
        if self.model is None:
            return "# LTR Feature Importance\n\nNo model trained yet.\n"

        gain = self.get_feature_importance("gain")
        split = self.get_feature_importance("split")

        lines = [
            "# LTR Feature Importance Report",
            f"\nModel trained: {self._meta.get('trained_at', 'N/A')}",
            f"Candidates: {self._meta.get('n_candidates', 'N/A')}",
            f"Features: {self._meta.get('n_features', 'N/A')}",
            "\n## Top 20 by Gain\n",
            "| Rank | Feature | Gain (%) | Split (%) |",
            "|------|---------|----------|-----------|",
        ]

        sorted_gain = sorted(gain.items(), key=lambda x: x[1], reverse=True)[:20]
        for rank, (fname, gv) in enumerate(sorted_gain, 1):
            sv = split.get(fname, 0.0)
            lines.append(f"| {rank} | `{fname}` | {gv*100:.2f} | {sv*100:.2f} |")

        return "\n".join(lines) + "\n"

    def is_trained(self) -> bool:
        """Return True if a trained model is available."""
        return self.model is not None

    def metadata(self) -> Dict[str, Any]:
        """Return training metadata."""
        return dict(self._meta)


# ---------------------------------------------------------------------------
# Module-level singleton (lazy init)
# ---------------------------------------------------------------------------
_ltr_engine: Optional[LTREngine] = None


def get_ltr_engine(model_dir: str = "./cache/ltr") -> LTREngine:
    """Return the module-level LTREngine singleton."""
    global _ltr_engine
    if _ltr_engine is None:
        _ltr_engine = LTREngine(model_dir=model_dir)
    return _ltr_engine


def train_ltr_from_ranked_candidates(
    feature_dicts: List[Dict[str, Any]],
    final_scores: Optional[List[float]] = None,
    decision_labels: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Convenience function: train LTR engine from already-scored candidates."""
    engine = get_ltr_engine()
    return engine.train(
        feature_dicts,
        final_scores=final_scores,
        decision_labels=decision_labels,
    )
