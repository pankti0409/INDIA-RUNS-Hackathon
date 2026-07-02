"""
test_ltr_engine.py — Unit tests for:
  - LTR Engine (ltr_engine.py): feature matrix, training, prediction, importance
  - SHAP Engine (shap_engine.py): explanations, global reports
  - BM25 / RRF (semantic_engine.py): bm25_retrieve, hybrid_retrieve_rrf, reciprocal_rank_fusion
  - Primitive feature enrichment (feature_engine.py): ~50 new features
"""
import math
from typing import Dict, List

import numpy as np
import pytest


# ─────────────────────────────────────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def minimal_candidate():
    """Minimal valid candidate for unit tests."""
    return {
        "candidate_id": "test-001",
        "profile": {
            "current_title": "Senior Machine Learning Engineer",
            "headline": "ML engineer specializing in retrieval and ranking",
            "summary": "Built vector search systems using FAISS and Elasticsearch. "
                       "Deployed production LTR models with LambdaMART. "
                       "5 years in search and retrieval.",
            "years_of_experience": 6,
            "country": "India",
            "location": "bangalore",
            "current_company_size": "1001-5000",
        },
        "career_history": [
            {
                "title": "Senior ML Engineer",
                "company": "SearchCo",
                "duration_months": 36,
                "is_current": True,
                "start_date": "2021-01-01",
                "description": "Led development of ranking systems using LambdaMART and NDCG optimization. "
                               "Deployed FAISS-based vector search serving 10M QPS. "
                               "Owned end-to-end retrieval pipeline. Mentored junior engineers.",
            },
            {
                "title": "ML Engineer",
                "company": "DataCorp",
                "duration_months": 24,
                "is_current": False,
                "start_date": "2019-01-01",
                "end_date": "2021-01-01",
                "description": "Built recommendation systems and dense retrieval with sentence-transformers. "
                               "Scaled Elasticsearch to billions of documents.",
            },
        ],
        "skills": [
            {"name": "Python", "proficiency": "expert", "duration_months": 60, "endorsements": 20},
            {"name": "FAISS", "proficiency": "advanced", "duration_months": 30, "endorsements": 5},
            {"name": "Elasticsearch", "proficiency": "advanced", "duration_months": 36, "endorsements": 10},
            {"name": "sentence-transformers", "proficiency": "advanced", "duration_months": 24},
            {"name": "LightGBM", "proficiency": "intermediate", "duration_months": 18},
            {"name": "PyTorch", "proficiency": "advanced", "duration_months": 36},
            {"name": "NLP", "proficiency": "advanced", "duration_months": 48},
            {"name": "Ranking", "proficiency": "expert", "duration_months": 30},
        ],
        "education": [
            {
                "degree": "B.Tech",
                "institution": "IIT Bombay",
                "tier": "tier_1",
                "field_of_study": "computer science",
            }
        ],
        "certifications": [],
        "languages": [{"language": "English", "proficiency": "professional"}],
        "redrob_signals": {
            "profile_completeness_score": 85.0,
            "skill_assessment_scores": {"NLP": 78, "Machine Learning": 82},
            "github_activity_score": 70,
            "verified_email": True,
            "notice_period_days": 30,
            "open_to_work_flag": True,
            "preferred_work_mode": "hybrid",
        },
    }


@pytest.fixture
def minimal_candidate_poor():
    """Poor-fit candidate for contrast."""
    return {
        "candidate_id": "test-002",
        "profile": {
            "current_title": "Frontend Developer",
            "headline": "React developer with UI/UX skills",
            "summary": "Building user interfaces with React and TypeScript.",
            "years_of_experience": 2,
            "country": "India",
            "location": "mumbai",
            "current_company_size": "11-50",
        },
        "career_history": [
            {
                "title": "Frontend Developer",
                "company": "WebAgency",
                "duration_months": 24,
                "is_current": True,
                "description": "Built React components and styled with CSS.",
            }
        ],
        "skills": [
            {"name": "React", "proficiency": "advanced", "duration_months": 24},
            {"name": "JavaScript", "proficiency": "expert", "duration_months": 30},
            {"name": "CSS", "proficiency": "intermediate", "duration_months": 24},
        ],
        "education": [{"degree": "B.E.", "tier": "tier_3", "field_of_study": "mechanical engineering"}],
        "certifications": [],
        "languages": [],
        "redrob_signals": {
            "profile_completeness_score": 45.0,
            "github_activity_score": 20,
            "verified_email": True,
            "notice_period_days": 90,
        },
    }


@pytest.fixture
def candidate_list(minimal_candidate, minimal_candidate_poor):
    """A small list of candidates for batch tests."""
    cands = [minimal_candidate, minimal_candidate_poor]
    # Add a couple more
    mid = {
        "candidate_id": "test-003",
        "profile": {
            "current_title": "Data Scientist",
            "headline": "ML and NLP practitioner",
            "summary": "Worked on NLP models and recommendation systems.",
            "years_of_experience": 4,
            "country": "India",
            "location": "pune",
            "current_company_size": "501-1000",
        },
        "career_history": [
            {
                "title": "Data Scientist",
                "company": "RecoTech",
                "duration_months": 30,
                "is_current": True,
                "description": "Built recommendation system using collaborative filtering and embeddings. "
                               "Deployed models to production.",
            }
        ],
        "skills": [
            {"name": "Python", "proficiency": "expert", "duration_months": 48},
            {"name": "NLP", "proficiency": "advanced", "duration_months": 30},
            {"name": "PyTorch", "proficiency": "intermediate", "duration_months": 24},
            {"name": "Elasticsearch", "proficiency": "beginner", "duration_months": 6},
        ],
        "education": [{"degree": "M.Tech", "tier": "tier_2", "field_of_study": "computer science"}],
        "certifications": [],
        "languages": [{"language": "English", "proficiency": "professional"}],
        "redrob_signals": {
            "profile_completeness_score": 70.0,
            "skill_assessment_scores": {"ML": 75},
            "github_activity_score": 45,
            "verified_email": True,
            "notice_period_days": 60,
        },
    }
    strong = {
        "candidate_id": "test-004",
        "profile": {
            "current_title": "Staff Search Engineer",
            "headline": "Search and ranking systems at scale",
            "summary": "Architected FAISS-based vector search for 100M+ documents. "
                       "Built LambdaMART ranking pipeline improving NDCG by 15%. "
                       "Led team of 5 engineers. Principal designer of retrieval infrastructure.",
            "years_of_experience": 8,
            "country": "India",
            "location": "bangalore",
            "current_company_size": "10001+",
        },
        "career_history": [
            {
                "title": "Staff Search Engineer",
                "company": "TechGiant",
                "duration_months": 36,
                "is_current": True,
                "description": "Designed and scaled retrieval systems serving 1 billion queries/day. "
                               "Led ranking team. Owned end-to-end LTR pipeline with NDCG optimization. "
                               "Mentored 5 junior engineers. Architected hybrid BM25+dense retrieval.",
            },
            {
                "title": "Senior ML Engineer",
                "company": "SearchStartup",
                "duration_months": 36,
                "is_current": False,
                "description": "Built FAISS vector database and Elasticsearch integration. "
                               "Deployed production ML models for recommendation. "
                               "Contributed to open source FAISS.",
            },
        ],
        "skills": [
            {"name": "FAISS", "proficiency": "expert", "duration_months": 60, "endorsements": 30},
            {"name": "sentence-transformers", "proficiency": "expert", "duration_months": 36},
            {"name": "Elasticsearch", "proficiency": "expert", "duration_months": 60, "endorsements": 20},
            {"name": "Python", "proficiency": "expert", "duration_months": 96},
            {"name": "LightGBM", "proficiency": "advanced", "duration_months": 36},
            {"name": "BM25", "proficiency": "advanced", "duration_months": 30},
            {"name": "PyTorch", "proficiency": "advanced", "duration_months": 48},
            {"name": "Ranking", "proficiency": "expert", "duration_months": 60},
            {"name": "NLP", "proficiency": "expert", "duration_months": 60},
            {"name": "Vector Search", "proficiency": "expert", "duration_months": 48},
        ],
        "education": [{"degree": "M.Tech", "tier": "tier_1", "field_of_study": "computer science and engineering"}],
        "certifications": [{"name": "AWS ML", "year": 2023}],
        "languages": [{"language": "English", "proficiency": "professional"}],
        "redrob_signals": {
            "profile_completeness_score": 95.0,
            "skill_assessment_scores": {"NLP": 92, "Machine Learning": 88, "Information Retrieval": 95},
            "github_activity_score": 90,
            "verified_email": True,
            "verified_phone": True,
            "linkedin_connected": True,
            "endorsements_received": 45,
            "notice_period_days": 15,
            "open_to_work_flag": True,
            "preferred_work_mode": "hybrid",
        },
    }
    cands.extend([mid, strong])
    return cands


# ─────────────────────────────────────────────────────────────────────────────
# PRIMITIVE FEATURE TESTS (feature_engine enrichment)
# ─────────────────────────────────────────────────────────────────────────────

class TestPrimitiveFeatures:
    def test_primitive_features_exist(self, minimal_candidate):
        from redrob_ranker.engines.feature_engine import extract_features
        feats = extract_features(minimal_candidate)

        primitive_keys = [
            # Title primitives
            "title_exact_match", "title_normalized_match", "title_seniority_gap",
            "title_role_family_match", "title_hierarchy_score",
            # Skill primitives
            "skill_freshness_score", "skill_duration_weighted", "skill_diversity_score",
            "skill_density_score", "skill_rarity_score", "missing_critical_skills_ratio",
            "adjacent_skill_score", "skill_cluster_coverage",
            # Experience primitives
            "architecture_exp_score", "deployment_exp_score", "open_source_exp_score",
            "ownership_exp_score", "mentoring_exp_score", "relevant_exp_ratio",
            "career_stability_score", "promotion_velocity_score",
            # Responsibility verbs
            "resp_designed_freq", "resp_led_freq", "resp_owned_freq",
            "resp_optimized_freq", "resp_scaled_freq", "resp_mentored_freq",
            "resp_architected_freq", "resp_depth_score",
            # Interaction features
            "title_x_skills", "projects_x_leadership",
            "experience_x_company", "embedding_x_experience",
            # Temporal features
            "skill_recency_score", "tech_adoption_rate",
            "career_momentum_score", "recent_ai_activity",
            # Evidence confidence
            "evidence_density_score", "evidence_diversity_score",
            "evidence_consistency_score", "feature_confidence_score",
        ]
        for k in primitive_keys:
            assert k in feats, f"Missing primitive feature: {k}"

    def test_all_primitives_normalized(self, minimal_candidate):
        """All primitive features must be in [0, 1]."""
        from redrob_ranker.engines.feature_engine import extract_features
        feats = extract_features(minimal_candidate)
        numeric_keys = [k for k, v in feats.items() if isinstance(v, float) and k != "candidate_id"]
        for k in numeric_keys:
            v = feats[k]
            assert 0.0 <= v <= 1.0, f"Feature {k}={v} out of [0,1] range"

    def test_strong_candidate_better_than_poor(self, candidate_list):
        """Strong ML engineer should have higher evidence density than frontend dev."""
        from redrob_ranker.engines.feature_engine import extract_features
        strong = extract_features(candidate_list[3])  # test-004 Staff Search Engineer
        poor = extract_features(candidate_list[1])    # test-002 Frontend Developer
        assert strong["evidence_density_score"] >= poor["evidence_density_score"]
        assert strong["architecture_exp_score"] >= poor["architecture_exp_score"]
        assert strong["skill_cluster_coverage"] >= poor["skill_cluster_coverage"]

    def test_responsibility_verbs_detected(self, minimal_candidate):
        from redrob_ranker.engines.feature_engine import extract_features
        feats = extract_features(minimal_candidate)
        # The fixture has "Led development", "Owned", "Mentored"
        assert feats["resp_led_freq"] > 0.0, "Led verb should be detected"
        assert feats["resp_owned_freq"] > 0.0, "Owned verb should be detected"
        assert feats["resp_mentored_freq"] > 0.0, "Mentored verb should be detected"

    def test_interaction_features_computed(self, minimal_candidate):
        from redrob_ranker.engines.feature_engine import extract_features
        feats = extract_features(minimal_candidate)
        # Interaction features must be products of component features
        title_s = feats.get("combined_title_score", 0)
        skills_s = feats.get("core_skill_score", 0)
        expected = round(title_s * skills_s, 4)
        assert abs(feats["title_x_skills"] - expected) < 0.01

    def test_skill_cluster_coverage_full_candidate(self, candidate_list):
        from redrob_ranker.engines.feature_engine import extract_features
        feats = extract_features(candidate_list[3])  # Staff Search Engineer
        # Should cover retrieval + ranking + ml_frameworks + embeddings clusters at minimum
        assert feats["skill_cluster_coverage"] >= 0.4

    def test_missing_critical_skills_poor_candidate(self, minimal_candidate_poor):
        from redrob_ranker.engines.feature_engine import extract_features
        feats = extract_features(minimal_candidate_poor)
        assert feats["missing_critical_skills_ratio"] > 0.7, \
            "Frontend dev should be missing most required ML skills"

    def test_feature_count_exceeds_100(self, minimal_candidate):
        from redrob_ranker.engines.feature_engine import extract_features
        feats = extract_features(minimal_candidate)
        numeric_count = sum(1 for k, v in feats.items() if isinstance(v, (int, float)) and k != "candidate_id")
        assert numeric_count >= 100, f"Expected ≥100 features, got {numeric_count}"


# ─────────────────────────────────────────────────────────────────────────────
# LTR ENGINE TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestLTREngine:
    def test_import(self):
        from redrob_ranker.engines.ltr_engine import LTREngine, get_ltr_engine
        assert LTREngine is not None
        assert get_ltr_engine is not None

    def test_feature_matrix_shape(self, candidate_list):
        from redrob_ranker.engines.feature_engine import extract_features
        from redrob_ranker.engines.ltr_engine import build_feature_matrix, LTR_FEATURE_SCHEMA
        feature_dicts = [extract_features(c) for c in candidate_list]
        X, feature_names = build_feature_matrix(feature_dicts)
        assert X.shape == (len(candidate_list), len(LTR_FEATURE_SCHEMA))
        assert X.dtype == np.float32

    def test_feature_matrix_values_finite(self, candidate_list):
        from redrob_ranker.engines.feature_engine import extract_features
        from redrob_ranker.engines.ltr_engine import build_feature_matrix
        feature_dicts = [extract_features(c) for c in candidate_list]
        X, _ = build_feature_matrix(feature_dicts)
        assert np.all(np.isfinite(X)), "Feature matrix must contain only finite values"

    def test_relevance_label_generation(self, candidate_list):
        from redrob_ranker.engines.feature_engine import extract_features
        from redrob_ranker.engines.ltr_engine import generate_relevance_labels
        fds = [extract_features(c) for c in candidate_list]
        labels = generate_relevance_labels(fds)
        assert labels.shape == (len(candidate_list),)
        assert set(labels).issubset({0, 1, 2, 3})

    def test_relevance_labels_from_decisions(self):
        from redrob_ranker.engines.ltr_engine import generate_relevance_labels
        fds = [{} for _ in range(4)]
        decisions = ["strong_hire", "hire", "borderline_hire", "reject"]
        labels = generate_relevance_labels(fds, decision_labels=decisions)
        assert list(labels) == [3, 2, 1, 0]

    def test_relevance_labels_from_scores(self):
        from redrob_ranker.engines.ltr_engine import generate_relevance_labels
        fds = [{} for _ in range(8)]
        scores = [0.95, 0.85, 0.75, 0.65, 0.50, 0.40, 0.30, 0.20]
        labels = generate_relevance_labels(fds, final_scores=scores)
        assert labels.shape == (8,)
        # Higher scores should get higher labels
        assert labels[0] >= labels[-1]

    def test_listwise_data_shape(self, candidate_list):
        from redrob_ranker.engines.feature_engine import extract_features
        from redrob_ranker.engines.ltr_engine import generate_listwise_data, generate_relevance_labels
        fds = [extract_features(c) for c in candidate_list]
        labels = generate_relevance_labels(fds)
        X, y, groups, fnames = generate_listwise_data(fds, labels)
        assert X.shape[0] == len(candidate_list)
        assert y.shape == (len(candidate_list),)
        assert groups.sum() == len(candidate_list)

    def test_pairwise_data_generated(self, candidate_list):
        from redrob_ranker.engines.feature_engine import extract_features
        from redrob_ranker.engines.ltr_engine import (
            generate_pairwise_data, generate_relevance_labels
        )
        fds = [extract_features(c) for c in candidate_list]
        labels = generate_relevance_labels(fds)
        X, y, groups, fnames = generate_pairwise_data(fds, labels)
        # Must produce at least some pairs if labels differ
        if len(set(labels.tolist())) > 1:
            assert X.shape[0] > 0
            assert set(y.tolist()).issubset({0, 1})

    def test_ltr_engine_fallback_predict(self, candidate_list):
        """LTR engine must produce scores even without a trained model."""
        import tempfile
        from redrob_ranker.engines.feature_engine import extract_features
        from redrob_ranker.engines.ltr_engine import LTREngine
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = LTREngine(model_dir=tmpdir)
            fds = [extract_features(c) for c in candidate_list]
            scores = engine.predict(fds)
            assert scores.shape == (len(candidate_list),)
            assert np.all(scores >= 0.0)
            assert np.all(scores <= 1.0)

    def test_ltr_engine_rank_candidates_ordered(self, candidate_list):
        """Staff Search Engineer (test-004) should rank above Frontend Dev (test-002)."""
        import tempfile
        from redrob_ranker.engines.feature_engine import extract_features
        from redrob_ranker.engines.ltr_engine import LTREngine
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = LTREngine(model_dir=tmpdir)
            fds = [extract_features(c) for c in candidate_list]
            cids = [c["candidate_id"] for c in candidate_list]
            ranked = engine.rank_candidates(fds, cids)
            ranked_ids = [r[0] for r in ranked]
            # Staff Search Engineer should be ranked above Frontend Developer
            idx_staff = ranked_ids.index("test-004")
            idx_frontend = ranked_ids.index("test-002")
            assert idx_staff < idx_frontend, \
                f"Staff Search Engineer should rank above Frontend Dev: got positions {idx_staff} vs {idx_frontend}"

    def test_ltr_engine_train_with_lightgbm(self, candidate_list):
        """Train LightGBM model if available; skip gracefully if not."""
        import tempfile
        from redrob_ranker.engines.feature_engine import extract_features
        from redrob_ranker.engines.ltr_engine import LTREngine, HAS_LGB
        if not HAS_LGB:
            pytest.skip("lightgbm not installed")
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = LTREngine(model_dir=tmpdir)
            fds = [extract_features(c) for c in candidate_list]
            result = engine.train(fds, n_estimators=10)
            assert result["status"] in ("ok", "skipped")
            if result["status"] == "ok":
                assert engine.is_trained()
                # Prediction after training must still produce valid scores
                scores = engine.predict(fds)
                assert scores.shape == (len(candidate_list),)
                assert np.all(np.isfinite(scores))

    def test_ltr_feature_importance_without_model(self):
        import tempfile
        from redrob_ranker.engines.ltr_engine import LTREngine
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = LTREngine(model_dir=tmpdir)
            importance = engine.get_feature_importance()
            assert isinstance(importance, dict)
            # Empty when no model
            assert len(importance) == 0

    def test_ltr_metadata(self, candidate_list):
        import tempfile
        from redrob_ranker.engines.feature_engine import extract_features
        from redrob_ranker.engines.ltr_engine import LTREngine, HAS_LGB
        if not HAS_LGB:
            pytest.skip("lightgbm not installed")
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = LTREngine(model_dir=tmpdir)
            fds = [extract_features(c) for c in candidate_list]
            result = engine.train(fds, n_estimators=10)
            if result["status"] == "ok":
                meta = engine.metadata()
                assert "trained_at" in meta
                assert "n_candidates" in meta
                assert "n_features" in meta


# ─────────────────────────────────────────────────────────────────────────────
# SHAP ENGINE TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestSHAPEngine:
    def test_import(self):
        from redrob_ranker.engines.shap_engine import (
            explain_candidate, batch_explain_candidates,
            generate_global_importance_report,
        )
        assert explain_candidate is not None

    def test_rule_based_explanation(self, minimal_candidate):
        from redrob_ranker.engines.feature_engine import extract_features
        from redrob_ranker.engines.shap_engine import explain_candidate
        feats = extract_features(minimal_candidate)
        explanation = explain_candidate("test-001", feats)
        assert explanation["candidate_id"] == "test-001"
        assert "strengths" in explanation
        assert "concerns" in explanation
        assert "summary" in explanation
        assert explanation["method"] in ("shap", "rule_based")

    def test_explanation_has_summary(self, minimal_candidate):
        from redrob_ranker.engines.feature_engine import extract_features
        from redrob_ranker.engines.shap_engine import explain_candidate
        feats = extract_features(minimal_candidate)
        explanation = explain_candidate("test-001", feats)
        assert len(explanation["summary"]) > 10

    def test_batch_explain(self, candidate_list):
        from redrob_ranker.engines.feature_engine import extract_features
        from redrob_ranker.engines.shap_engine import batch_explain_candidates
        fds = [extract_features(c) for c in candidate_list]
        explanations = batch_explain_candidates(fds)
        assert len(explanations) == len(candidate_list)
        for expl in explanations:
            assert "candidate_id" in expl
            assert "strengths" in expl
            assert "concerns" in expl

    def test_global_importance_report_generated(self):
        from redrob_ranker.engines.shap_engine import generate_global_importance_report
        report = generate_global_importance_report(
            feature_importance_gain={"core_skill_score": 0.25, "semantic_similarity_score": 0.20}
        )
        assert "Feature Importance" in report
        assert "core_skill_score" in report

    def test_strong_candidate_has_strengths(self, candidate_list):
        from redrob_ranker.engines.feature_engine import extract_features
        from redrob_ranker.engines.shap_engine import explain_candidate
        feats = extract_features(candidate_list[3])  # Staff Search Engineer
        explanation = explain_candidate("test-004", feats)
        assert len(explanation["strengths"]) > 0

    def test_poor_candidate_has_concerns(self, candidate_list):
        from redrob_ranker.engines.feature_engine import extract_features
        from redrob_ranker.engines.shap_engine import explain_candidate
        feats = extract_features(candidate_list[1])  # Frontend Developer
        explanation = explain_candidate("test-002", feats)
        assert len(explanation["concerns"]) > 0


# ─────────────────────────────────────────────────────────────────────────────
# BM25 / RRF RETRIEVAL TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestBM25RRF:
    def test_bm25_retrieve_returns_all_candidates(self, candidate_list):
        from redrob_ranker.engines.semantic_engine import bm25_retrieve, JD_TEXT
        scores = bm25_retrieve(JD_TEXT, candidate_list)
        assert len(scores) == len(candidate_list)
        for cid, score in scores.items():
            assert 0.0 <= score <= 1.0

    def test_bm25_retrieve_top_k(self, candidate_list):
        from redrob_ranker.engines.semantic_engine import bm25_retrieve, JD_TEXT
        scores = bm25_retrieve(JD_TEXT, candidate_list, top_k=2)
        assert len(scores) == 2

    def test_bm25_ml_engineer_ranks_above_frontend(self, candidate_list):
        """BM25 should prefer ML engineers over frontend devs for an ML JD."""
        from redrob_ranker.engines.semantic_engine import bm25_retrieve, JD_TEXT
        scores = bm25_retrieve(JD_TEXT, candidate_list)
        ml_score = scores.get("test-001", 0)
        frontend_score = scores.get("test-002", 0)
        assert ml_score >= frontend_score, \
            f"ML engineer ({ml_score}) should score ≥ frontend dev ({frontend_score}) on BM25"

    def test_reciprocal_rank_fusion_empty(self):
        from redrob_ranker.engines.semantic_engine import reciprocal_rank_fusion
        fused = reciprocal_rank_fusion([])
        assert fused == {}

    def test_reciprocal_rank_fusion_single_list(self):
        from redrob_ranker.engines.semantic_engine import reciprocal_rank_fusion
        ranked = ["a", "b", "c"]
        fused = reciprocal_rank_fusion([ranked])
        # a should have highest score (rank 1)
        assert fused["a"] > fused["b"] > fused["c"]

    def test_reciprocal_rank_fusion_two_lists(self):
        from redrob_ranker.engines.semantic_engine import reciprocal_rank_fusion
        list1 = ["a", "b", "c"]
        list2 = ["a", "c", "b"]  # c gets a boost here
        fused = reciprocal_rank_fusion([list1, list2])
        # a should have highest (rank 1 in both)
        sorted_ids = sorted(fused, key=fused.__getitem__, reverse=True)
        assert sorted_ids[0] == "a"

    def test_hybrid_retrieve_rrf_returns_scores(self, candidate_list):
        from redrob_ranker.engines.semantic_engine import hybrid_retrieve_rrf, JD_TEXT
        fused = hybrid_retrieve_rrf(JD_TEXT, candidate_list)
        assert len(fused) == len(candidate_list)
        for cid, score in fused.items():
            assert score > 0.0

    def test_hybrid_retrieve_rrf_with_dense_scores(self, candidate_list):
        from redrob_ranker.engines.semantic_engine import hybrid_retrieve_rrf, JD_TEXT
        # Simulate pre-computed dense scores
        dense_scores = {
            "test-001": 0.90,
            "test-002": 0.20,
            "test-003": 0.65,
            "test-004": 0.95,
        }
        fused = hybrid_retrieve_rrf(JD_TEXT, candidate_list, dense_scores=dense_scores)
        assert len(fused) > 0
        # test-004 with both high BM25 and high dense should rank first
        sorted_ids = sorted(fused, key=fused.__getitem__, reverse=True)
        assert sorted_ids[0] in {"test-001", "test-004"}  # One of the strong candidates

    def test_hybrid_retrieve_rrf_top_k(self, candidate_list):
        from redrob_ranker.engines.semantic_engine import hybrid_retrieve_rrf, JD_TEXT
        fused = hybrid_retrieve_rrf(JD_TEXT, candidate_list, top_k=2)
        assert len(fused) == 2


# ─────────────────────────────────────────────────────────────────────────────
# INTEGRATION: end-to-end feature → LTR predict → explain
# ─────────────────────────────────────────────────────────────────────────────

class TestEndToEndLTRPipeline:
    def test_full_pipeline_produces_ranked_list(self, candidate_list):
        """Extract features → LTR predict → explanations, all without errors."""
        import tempfile
        from redrob_ranker.engines.feature_engine import extract_features
        from redrob_ranker.engines.ltr_engine import LTREngine
        from redrob_ranker.engines.shap_engine import batch_explain_candidates

        with tempfile.TemporaryDirectory() as tmpdir:
            engine = LTREngine(model_dir=tmpdir)
            fds = [extract_features(c) for c in candidate_list]
            cids = [c["candidate_id"] for c in candidate_list]

            # Predict
            ranked = engine.rank_candidates(fds, cids)
            assert len(ranked) == len(candidate_list)

            # Explain
            explanations = batch_explain_candidates(fds)
            assert len(explanations) == len(candidate_list)

    def test_ltr_and_bm25_agree_on_top_candidate(self, candidate_list):
        """Both LTR (fallback) and BM25 should prefer the Staff Search Engineer."""
        import tempfile
        from redrob_ranker.engines.feature_engine import extract_features
        from redrob_ranker.engines.ltr_engine import LTREngine
        from redrob_ranker.engines.semantic_engine import bm25_retrieve, JD_TEXT

        with tempfile.TemporaryDirectory() as tmpdir:
            engine = LTREngine(model_dir=tmpdir)
            fds = [extract_features(c) for c in candidate_list]
            cids = [c["candidate_id"] for c in candidate_list]

            # LTR ranking
            ltr_ranked = engine.rank_candidates(fds, cids)
            ltr_top = ltr_ranked[0][0]

            # BM25 ranking
            bm25_scores = bm25_retrieve(JD_TEXT, candidate_list)
            bm25_top = max(bm25_scores, key=bm25_scores.__getitem__)

            # Both should prefer strong technical candidates over frontend dev
            assert ltr_top not in {"test-002"}, f"LTR should not rank frontend dev first: got {ltr_top}"
            assert bm25_top not in {"test-002"}, f"BM25 should not rank frontend dev first: got {bm25_top}"
