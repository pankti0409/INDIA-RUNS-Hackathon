import Sidebar from "@/components/Sidebar";

const FEATURES = [
  {
    name: "title_score",
    label: "Title Score",
    weight: 0.26,
    description: "How well current title matches 'Senior AI/ML Engineer' JD",
    sensitivity: "Very High",
    justification: "JD explicitly states title is the single most decisive signal",
  },
  {
    name: "core_skill_score",
    label: "Core Skill Match",
    weight: 0.18,
    description: "Coverage of required AI/retrieval skills weighted by proficiency",
    sensitivity: "Very High",
    justification: "Required skills are a hard filter per JD (FAISS, ES, LTR, embeddings)",
  },
  {
    name: "experience_score",
    label: "Experience (YoE + Product Co.)",
    weight: 0.12,
    description: "Years of experience fit (5-9yr ideal) + product company background",
    sensitivity: "High",
    justification: "JD specifies 5-9yr senior engineers from product-focused companies",
  },
  {
    name: "behavioral_score",
    label: "Behavioral Intelligence",
    weight: 0.10,
    description: "Availability, responsiveness, trust, reliability composites",
    sensitivity: "High",
    justification: "Recruiter realism: high-scoring unavailable candidates rank lower",
  },
  {
    name: "skill_ontology",
    label: "Skill Ontology Match",
    weight: 0.09,
    description: "Related skills via semantic graph (FAISS↔ANN, ES↔BM25)",
    sensitivity: "Medium",
    justification: "Avoids false negatives from terminological variation in skill naming",
  },
  {
    name: "hireability_score",
    label: "Hireability",
    weight: 0.08,
    description: "Realistic hiring probability: open_to_work + notice + response + acceptance",
    sensitivity: "Medium",
    justification: "A great candidate who won't respond is worthless to a recruiter",
  },
  {
    name: "semantic_similarity",
    label: "Semantic Similarity (JD embed)",
    weight: 0.06,
    description: "BAAI/bge-small-en-v1.5 cosine similarity to JD embedding",
    sensitivity: "Medium",
    justification: "Catches semantic overlap not captured by keyword matching",
  },
  {
    name: "education_score",
    label: "Education",
    weight: 0.05,
    description: "Institution tier × degree level × field relevance",
    sensitivity: "Low",
    justification: "Useful tiebreaker; PhD/IIT candidates preferred but not mandatory",
  },
  {
    name: "assessment_score",
    label: "Platform Assessment",
    weight: 0.04,
    description: "AI-specific assessment scores (NLP, ML, RAG) on Redrob platform",
    sensitivity: "Medium",
    justification: "Independently validated skills trump self-reported proficiency",
  },
  {
    name: "location_score",
    label: "Location",
    weight: 0.02,
    description: "India preferred; Noida/Pune bonus; abroad penalized",
    sensitivity: "Low",
    justification: "Role is hybrid and India-based per JD",
  },
  {
    name: "honeypot_penalty",
    label: "Honeypot Penalty (multiplier)",
    weight: -1.0,
    description: "Multiplicative penalty applied for synthetic/manipulated profiles",
    sensitivity: "Critical",
    justification: "Competition explicitly contains honeypots that must not rank in top-100",
  },
];

function SensitivityBadge({ level }: { level: string }) {
  const cfg: Record<string, { bg: string; color: string }> = {
    "Very High": { bg: "#fee2e2", color: "#991b1b" },
    "High": { bg: "#fef3c7", color: "#92400e" },
    "Medium": { bg: "#dbeafe", color: "#1e40af" },
    "Low": { bg: "#f3f4f6", color: "#374151" },
    "Critical": { bg: "#dc2626", color: "#fff" },
  };
  const c = cfg[level] || cfg["Low"];
  return (
    <span style={{ padding: "2px 8px", borderRadius: 10, fontSize: 11, fontWeight: 600, background: c.bg, color: c.color }}>
      {level}
    </span>
  );
}

export default function FeatureImportance() {
  const positiveFeatures = FEATURES.filter((f) => f.weight > 0);
  const maxWeight = Math.max(...positiveFeatures.map((f) => f.weight));

  return (
    <div style={{ display: "flex", minHeight: "100vh", background: "var(--bg)" }}>
      <Sidebar />
      <main style={{ flex: 1, padding: "32px 40px", overflow: "auto" }}>
        <div style={{ marginBottom: 28 }}>
          <h1 style={{ fontSize: 22, fontWeight: 700, letterSpacing: "-0.03em" }}>
            Feature Importance
          </h1>
          <p style={{ color: "var(--text-secondary)", marginTop: 4, fontSize: 13 }}>
            Ranking signal weights and sensitivity analysis — each weight is defensible against JD requirements
          </p>
        </div>

        {/* Summary cards */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16, marginBottom: 28 }}>
          <div className="card stat-card">
            <div style={{ fontSize: 26, fontWeight: 700 }}>75+</div>
            <div style={{ fontSize: 11, letterSpacing: "0.06em", color: "var(--text-muted)", textTransform: "uppercase", marginTop: 4 }}>Total Features</div>
          </div>
          <div className="card stat-card">
            <div style={{ fontSize: 26, fontWeight: 700 }}>5</div>
            <div style={{ fontSize: 11, letterSpacing: "0.06em", color: "var(--text-muted)", textTransform: "uppercase", marginTop: 4 }}>Sub-Models (RRF)</div>
          </div>
          <div className="card stat-card">
            <div style={{ fontSize: 26, fontWeight: 700 }}>60/40</div>
            <div style={{ fontSize: 11, letterSpacing: "0.06em", color: "var(--text-muted)", textTransform: "uppercase", marginTop: 4 }}>Weighted/RRF Blend</div>
          </div>
        </div>

        {/* Weight chart */}
        <div className="card" style={{ marginBottom: 24 }}>
          <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 20 }}>Feature Weights — Horizontal Bar Chart</h2>
          {positiveFeatures.map((feat) => (
            <div key={feat.name} style={{ marginBottom: 14 }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 5 }}>
                <span style={{ fontSize: 12, color: "var(--text-primary)", fontWeight: 500 }}>{feat.label}</span>
                <span style={{ fontSize: 12, fontWeight: 700, color: "var(--text-primary)" }}>{(feat.weight * 100).toFixed(0)}%</span>
              </div>
              <div className="progress-bar" style={{ height: 10 }}>
                <div
                  className="progress-fill"
                  style={{ width: `${(feat.weight / maxWeight) * 100}%`, height: 10, borderRadius: 5, background: "var(--accent-light)" }}
                />
              </div>
            </div>
          ))}
        </div>

        {/* Full table */}
        <div className="card">
          <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>Feature Justification Table</h2>
          <table className="data-table">
            <thead>
              <tr>
                <th>Feature</th>
                <th style={{ width: 70 }}>Weight</th>
                <th style={{ width: 110 }}>Sensitivity</th>
                <th>Description</th>
                <th>JD Justification</th>
              </tr>
            </thead>
            <tbody>
              {FEATURES.map((feat) => (
                <tr key={feat.name}>
                  <td style={{ fontWeight: 600, fontSize: 12 }}>{feat.label}</td>
                  <td style={{ fontSize: 12, fontWeight: 700, color: feat.weight < 0 ? "#dc2626" : "var(--text-primary)" }}>
                    {feat.weight < 0 ? "PENALTY" : `${(feat.weight * 100).toFixed(0)}%`}
                  </td>
                  <td><SensitivityBadge level={feat.sensitivity} /></td>
                  <td style={{ fontSize: 11, color: "var(--text-secondary)", lineHeight: 1.5 }}>{feat.description}</td>
                  <td style={{ fontSize: 11, color: "var(--text-secondary)", lineHeight: 1.5 }}>{feat.justification}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}
