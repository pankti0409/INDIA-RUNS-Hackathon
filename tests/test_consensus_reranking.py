import pytest
from redrob_ranker.engines.consensus_engine import get_consensus_engine
from redrob_ranker.engines.reranking_engine import get_reranking_engine

def test_consensus_engine_agents_present():
    engine = get_consensus_engine()
    assert len(engine.agents) == 12
    # Verify name matching
    agent_names = [a.name for a in engine.agents]
    assert "Recruiter Agent" in agent_names
    assert "Technical Skills Agent" in agent_names
    assert "Experience Agent" in agent_names
    assert "Project Agent" in agent_names
    assert "Risk Agent" in agent_names

def test_consensus_evaluation_success():
    engine = get_consensus_engine()
    
    # Standard candidate features
    features = {
        "title_score": 0.9,
        "notice_score": 0.8,
        "work_mode_score": 0.9,
        "core_skill_score": 0.8,
        "preferred_skill_score": 0.7,
        "avg_assessment_score": 0.8,
        "has_assessments": 1.0,
        "yoe_score": 0.8,
        "relevant_exp_ratio": 0.8,
        "career_stability_score": 0.9,
        "project_complexity_score": 0.7,
        "scale_evidence_score": 0.8,
        "resp_depth_score": 0.8,
        "leadership_evidence_score": 0.7,
        "resp_owned_freq": 1.0,
        "resp_mentored_freq": 1.0,
        "research_depth_score": 0.6,
        "advanced_degree": 1.0,
        "hireability_probability": 0.8,
        "active_recently": 0.9,
        "response_rate_score": 0.8,
        "company_quality_score": 0.8,
        "industry_relevance_score": 0.8,
        "has_big_tech_experience": 1.0,
        "semantic_similarity_score": 0.8,
        "cross_encoder_score": 0.8,
        "career_growth_score": 0.8,
        "career_coherence_score": 0.8,
        "promotion_velocity_score": 0.8,
        "risk_probability": 0.05,
        "trust_score": 0.9,
        "evidence_consistency_score": 0.8
    }
    
    res = engine.synthesize(features)
    assert res["overall_consensus_score"] > 0.6
    assert res["overall_consensus_confidence"] > 0.6
    assert res["technical_consensus"] > 0.6
    assert "consensus_explanation" in res
    assert len(res["conflicts"]) == 0

def test_consensus_risk_conflict():
    engine = get_consensus_engine()
    
    # High risk candidate (e.g. potential honeypot)
    features = {
        "title_score": 0.9,
        "notice_score": 0.8,
        "work_mode_score": 0.9,
        "core_skill_score": 0.8,
        "preferred_skill_score": 0.7,
        "avg_assessment_score": 0.8,
        "has_assessments": 1.0,
        "yoe_score": 0.8,
        "relevant_exp_ratio": 0.8,
        "career_stability_score": 0.9,
        "risk_probability": 0.85, # High risk
        "trust_score": 0.3, # Low trust
        "evidence_consistency_score": 0.4
    }
    
    res = engine.synthesize(features)
    # Consensus score should be heavily degraded due to high risk
    assert res["overall_consensus_score"] < 0.40
    assert any("Risk Agent flagged high risk" in c for c in res["conflicts"])

def test_reranking_engine_swapping():
    engine = get_reranking_engine()
    
    # Candidate pool
    cand1 = {"candidate_id": "CAND_001", "profile": {"anonymized_name": "A"}}
    feat1 = {
        "core_skill_score": 0.9,
        "role_specific_depth_score": 0.9,
        "scale_evidence_score": 0.8,
        "project_complexity_score": 0.9,
        "leadership_evidence_score": 0.8,
        "career_growth_score": 0.8,
        "career_stability_score": 0.8,
        "yoe_score": 0.8
    }
    
    cand2 = {"candidate_id": "CAND_002", "profile": {"anonymized_name": "B"}}
    feat2 = {
        "core_skill_score": 0.4,
        "role_specific_depth_score": 0.3,
        "scale_evidence_score": 0.2,
        "project_complexity_score": 0.2,
        "leadership_evidence_score": 0.2,
        "career_growth_score": 0.4,
        "career_stability_score": 0.4,
        "yoe_score": 0.4
    }
    
    scored_candidates = [
        (cand2, feat2, 0.70), # CAND_002 starts ranked #1 heuristically
        (cand1, feat1, 0.65)  # CAND_001 starts ranked #2 heuristically
    ]
    
    reranked = engine.rerank(scored_candidates)
    
    # CAND_001 should swap to rank #1 because of superior comparative technical/project features
    assert reranked[0][0]["candidate_id"] == "CAND_001"
    assert reranked[0][1]["final_rank"] == 1
    assert "comparative_reason" in reranked[1][1]
    assert "CAND_001" in reranked[0][0]["candidate_id"]
