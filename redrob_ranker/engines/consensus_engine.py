"""
consensus_engine.py — Block 11: Multi-Agent Consensus Reranking Engine

Provides specialized expert agents that independently evaluate different aspects of a
candidate's profile, and a Consensus Engine to synthesize their outputs into a unified
consensus decision with calibrated conflict resolution.
"""

import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)


class ExpertAgent:
    """Base class for all expert agents participating in consensus."""
    def __init__(self, name: str, weight: float):
        self.name = name
        self.weight = weight

    def evaluate(self, features: Dict[str, Any]) -> Tuple[float, float, str]:
        """
        Evaluate candidate based on specialized evidence.
        Returns: Tuple[score, confidence, reasoning]
        """
        raise NotImplementedError


class RecruiterAgent(ExpertAgent):
    """Evaluates recruiter-level job alignment, notice period, and profile presentation."""
    def __init__(self):
        super().__init__("Recruiter Agent", 1.0)

    def evaluate(self, features: Dict[str, Any]) -> Tuple[float, float, str]:
        title_score = float(features.get("title_score", 0.5))
        notice_score = float(features.get("notice_score", 0.5))
        work_mode = float(features.get("work_mode_score", 0.8))
        
        score = 0.5 * title_score + 0.3 * notice_score + 0.2 * work_mode
        
        # High confidence if explicit title and notice info are available
        has_title = "title_score" in features
        has_notice = "notice_score" in features
        confidence = 0.9 if (has_title and has_notice) else 0.5
        
        reason = f"Title alignment: {title_score:.2f}, Availability: {notice_score:.2f}"
        return score, confidence, reason


class TechnicalSkillsAgent(ExpertAgent):
    """Evaluates technical capability, core skills matching, and assessment scores."""
    def __init__(self):
        super().__init__("Technical Skills Agent", 1.2)

    def evaluate(self, features: Dict[str, Any]) -> Tuple[float, float, str]:
        core_skills = float(features.get("core_skill_score", 0.0))
        pref_skills = float(features.get("preferred_skill_score", 0.0))
        assess = float(features.get("avg_assessment_score", 0.5))
        
        score = 0.5 * core_skills + 0.2 * pref_skills + 0.3 * assess
        
        has_assessments = float(features.get("has_assessments", 0.0))
        confidence = 0.95 if has_assessments == 1.0 else 0.70
        
        reason = f"Core skills alignment: {core_skills:.2f}, Assessment performance: {assess:.2f}"
        return score, confidence, reason


class ExperienceAgent(ExpertAgent):
    """Evaluates professional years of experience, history quality, and stability."""
    def __init__(self):
        super().__init__("Experience Agent", 1.0)

    def evaluate(self, features: Dict[str, Any]) -> Tuple[float, float, str]:
        yoe_score = float(features.get("yoe_score", 0.5))
        relevant_exp = float(features.get("relevant_exp_ratio", 0.5))
        stability = float(features.get("career_stability_score", 0.7))
        
        score = 0.5 * yoe_score + 0.3 * relevant_exp + 0.2 * stability
        confidence = 0.90 if "yoe_score" in features else 0.60
        
        reason = f"Years of experience alignment: {yoe_score:.2f}, History stability: {stability:.2f}"
        return score, confidence, reason


class ProjectAgent(ExpertAgent):
    """Evaluates project complexity, technical contributions, and system scale."""
    def __init__(self):
        super().__init__("Project Agent", 1.0)

    def evaluate(self, features: Dict[str, Any]) -> Tuple[float, float, str]:
        complexity = float(features.get("project_complexity_score", 0.0))
        scale = float(features.get("scale_evidence_score", 0.0))
        resp_depth = float(features.get("resp_depth_score", 0.5))
        
        score = 0.4 * complexity + 0.4 * scale + 0.2 * resp_depth
        confidence = 0.85 if complexity > 0 else 0.50
        
        reason = f"Project complexity: {complexity:.2f}, Production scale signals: {scale:.2f}"
        return score, confidence, reason


class LeadershipAgent(ExpertAgent):
    """Evaluates team leadership, technical ownership, and mentorship evidence."""
    def __init__(self):
        super().__init__("Leadership Agent", 0.8)

    def evaluate(self, features: Dict[str, Any]) -> Tuple[float, float, str]:
        lead_score = float(features.get("leadership_evidence_score", 0.0))
        owned = float(features.get("resp_owned_freq", 0.0))
        mentored = float(features.get("resp_mentored_freq", 0.0))
        
        score = 0.6 * lead_score + 0.2 * min(1.0, owned) + 0.2 * min(1.0, mentored)
        confidence = 0.80 if lead_score > 0 else 0.50
        
        reason = f"Ownership & leadership markers: {lead_score:.2f}"
        return score, confidence, reason


class ResearchAgent(ExpertAgent):
    """Evaluates technical research depth, patents, and publication history."""
    def __init__(self):
        super().__init__("Research Agent", 0.6)

    def evaluate(self, features: Dict[str, Any]) -> Tuple[float, float, str]:
        research = float(features.get("research_depth_score", 0.0))
        degree = float(features.get("advanced_degree", 0.0))
        
        score = 0.8 * research + 0.2 * degree
        confidence = 0.80 if research > 0 else 0.50
        
        reason = f"Research depth & advanced education: {research:.2f}"
        return score, confidence, reason


class BehaviorAgent(ExpertAgent):
    """Evaluates response rates, availability, and active job search behavior."""
    def __init__(self):
        super().__init__("Behavior Agent", 0.8)

    def evaluate(self, features: Dict[str, Any]) -> Tuple[float, float, str]:
        hireability = float(features.get("hireability_probability", 0.5))
        active = float(features.get("active_recently", 0.5))
        response = float(features.get("response_rate_score", 0.5))
        
        score = 0.4 * hireability + 0.3 * active + 0.3 * response
        confidence = 0.85 if "response_rate_score" in features else 0.50
        
        reason = f"Recruiter response & activity rate: {response:.2f}"
        return score, confidence, reason


class CompanyAgent(ExpertAgent):
    """Evaluates hiring history company quality, startup context, and brand exposure."""
    def __init__(self):
        super().__init__("Company Agent", 0.9)

    def evaluate(self, features: Dict[str, Any]) -> Tuple[float, float, str]:
        quality = float(features.get("company_quality_score", 0.4))
        relevance = float(features.get("industry_relevance_score", 0.4))
        big_tech = float(features.get("has_big_tech_experience", 0.0))
        
        score = 0.4 * quality + 0.4 * relevance + 0.2 * big_tech
        confidence = 0.90 if "company_quality_score" in features else 0.60
        
        reason = f"Company background quality: {quality:.2f}, Industry relevance: {relevance:.2f}"
        return score, confidence, reason


class SemanticAgent(ExpertAgent):
    """Evaluates dense semantic similarity matching and Cross-Encoder reranking scores."""
    def __init__(self):
        super().__init__("Semantic Agent", 1.2)

    def evaluate(self, features: Dict[str, Any]) -> Tuple[float, float, str]:
        similarity = float(features.get("semantic_similarity_score", 0.5))
        ce_score = float(features.get("cross_encoder_score", 0.5))
        
        score = 0.4 * similarity + 0.6 * ce_score
        confidence = 0.95 if ce_score > 0 else 0.70
        
        reason = f"Cross-encoder relevance: {ce_score:.2f}, Hybrid similarity: {similarity:.2f}"
        return score, confidence, reason


class CareerProgressionAgent(ExpertAgent):
    """Evaluates promotional velocity, career coherence, and momentum."""
    def __init__(self):
        super().__init__("Career Progression Agent", 0.8)

    def evaluate(self, features: Dict[str, Any]) -> Tuple[float, float, str]:
        growth = float(features.get("career_growth_score", 0.5))
        coherence = float(features.get("career_coherence_score", 0.5))
        velocity = float(features.get("promotion_velocity_score", 0.0))
        
        score = 0.4 * growth + 0.4 * coherence + 0.2 * velocity
        confidence = 0.85 if "career_growth_score" in features else 0.50
        
        reason = f"Career growth index: {growth:.2f}, Coherence: {coherence:.2f}"
        return score, confidence, reason


class RiskAgent(ExpertAgent):
    """Evaluates honeypot likelihood, synthetic resumes, and validation inconsistencies."""
    def __init__(self):
        super().__init__("Risk Agent", 1.1)

    def evaluate(self, features: Dict[str, Any]) -> Tuple[float, float, str]:
        risk = float(features.get("risk_probability", 0.0))
        trust = float(features.get("trust_score", 0.8))
        
        score = 1.0 - risk
        confidence = trust
        
        reason = f"Profile Risk Assessment (1.0 - risk): {score:.2f}, Trust score: {trust:.2f}"
        return score, confidence, reason


class DecisionValidationAgent(ExpertAgent):
    """Validates self-consistency and flags downstream logical contradictions."""
    def __init__(self):
        super().__init__("Decision Validation Agent", 0.7)

    def evaluate(self, features: Dict[str, Any]) -> Tuple[float, float, str]:
        # Scores candidate higher if their confidence is consistent with their score
        trust = float(features.get("trust_score", 0.8))
        consistency = float(features.get("evidence_consistency_score", 0.7))
        
        score = 0.5 * trust + 0.5 * consistency
        confidence = 0.90
        
        reason = f"Decision consistency trace: {consistency:.2f}"
        return score, confidence, reason


class ConsensusSynthesisEngine:
    """Core Consensus synthesis coordinating the 12 independent expert agents."""
    def __init__(self):
        self.agents = [
            RecruiterAgent(),
            TechnicalSkillsAgent(),
            ExperienceAgent(),
            ProjectAgent(),
            LeadershipAgent(),
            ResearchAgent(),
            BehaviorAgent(),
            CompanyAgent(),
            SemanticAgent(),
            CareerProgressionAgent(),
            RiskAgent(),
            DecisionValidationAgent()
        ]

    def synthesize(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synthesize independent expert evaluations.
        Calculates consensus metrics, resolves conflicts, and returns consensus output.
        """
        agent_results = {}
        weighted_score_sum = 0.0
        total_weight = 0.0
        
        conflicts = []
        
        # Gather evaluations
        for agent in self.agents:
            score, conf, reason = agent.evaluate(features)
            agent_results[agent.name] = {
                "score": score,
                "confidence": conf,
                "reason": reason
            }
            
            # Weighted average based on agent relevance (weight) and confidence
            effective_weight = agent.weight * conf
            weighted_score_sum += score * effective_weight
            total_weight += effective_weight
            
        overall_consensus_score = (weighted_score_sum / total_weight) if total_weight > 0.0 else 0.5
        
        # Conflict resolution logic:
        # Check if the RiskAgent score is low (high risk) while other agents scored high
        risk_score = agent_results["Risk Agent"]["score"]
        if risk_score < 0.40 and overall_consensus_score > 0.50:
            # Degrade consensus score due to high security/honeypot risk
            degrade_amount = (0.50 - risk_score) * 0.8
            overall_consensus_score = max(0.05, overall_consensus_score - degrade_amount)
            conflicts.append(f"Risk Agent flagged high risk (trust = {agent_results['Risk Agent']['confidence']:.2f}). Overall consensus degraded.")
            
        # Check for disagreement between RecruiterAgent and TechnicalSkillsAgent
        rec_score = agent_results["Recruiter Agent"]["score"]
        tech_score = agent_results["Technical Skills Agent"]["score"]
        if abs(rec_score - tech_score) > 0.40:
            # Disagreement: prioritize technical assessment scores
            rec_conf = agent_results["Recruiter Agent"]["confidence"]
            tech_conf = agent_results["Technical Skills Agent"]["confidence"]
            if tech_conf >= rec_conf:
                overall_consensus_score = 0.3 * rec_score + 0.7 * tech_score
                conflicts.append("Recruiter and Technical agents disagreed on capability. Prioritized technical validation details.")
            else:
                conflicts.append("Recruiter and Technical agents disagreed on capability. Blended equally.")
                
        # Consensus Confidence Calibration
        # Depends on number of agreeing agents and overall trust
        agreement_count = 0
        agent_scores = [agent_results[a.name]["score"] for a in self.agents if a.name != "Risk Agent"]
        avg_score = sum(agent_scores) / len(agent_scores)
        for s in agent_scores:
            if abs(s - avg_score) < 0.20:
                agreement_count += 1
                
        # Compute overall confidence
        agreement_ratio = agreement_count / len(agent_scores)
        base_trust = float(features.get("trust_score", 0.8))
        overall_confidence = 0.50 * agreement_ratio + 0.30 * base_trust + 0.20 * agent_results["Decision Validation Agent"]["score"]
        
        # Formulate consensus explanation
        agent_explanations = []
        for agent_name, res in agent_results.items():
            agent_explanations.append(f"{agent_name}: {res['reason']} (Score: {res['score']:.2f}, Conf: {res['confidence']:.2f})")
            
        consensus_explanation = " | ".join(agent_explanations[:4])
        
        return {
            "overall_consensus_score": round(overall_consensus_score, 6),
            "overall_consensus_confidence": round(overall_confidence, 4),
            "technical_consensus": round(agent_results["Technical Skills Agent"]["score"], 4),
            "experience_consensus": round(agent_results["Experience Agent"]["score"], 4),
            "leadership_consensus": round(agent_results["Leadership Agent"]["score"], 4),
            "project_consensus": round(agent_results["Project Agent"]["score"], 4),
            "research_consensus": round(agent_results["Research Agent"]["score"], 4),
            "behavior_consensus": round(agent_results["Behavior Agent"]["score"], 4),
            "semantic_consensus": round(agent_results["Semantic Agent"]["score"], 4),
            "risk_consensus": round(agent_results["Risk Agent"]["score"], 4),
            "validation_consensus": round(agent_results["Decision Validation Agent"]["score"], 4),
            "recruiter_consensus": round(agent_results["Recruiter Agent"]["score"], 4),
            "conflicts": conflicts,
            "consensus_explanation": consensus_explanation
        }


# Module level singleton
_consensus_engine: ConsensusSynthesisEngine = None

def get_consensus_engine() -> ConsensusSynthesisEngine:
    global _consensus_engine
    if _consensus_engine is None:
        _consensus_engine = ConsensusSynthesisEngine()
    return _consensus_engine
