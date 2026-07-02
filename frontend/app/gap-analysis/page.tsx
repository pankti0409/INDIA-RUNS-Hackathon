"use client";

import Sidebar from "@/components/Sidebar";
import { useState, useEffect } from "react";
import Link from "next/link";

// This page uses server component for the initial candidate list,
// then client component for interactive gap analysis via API.

type GapAnalysis = {
  candidate_id: string;
  rank: number;
  final_score: number;
  overall_assessment: string;
  dimension_scores: {
    skill_match: number;
    experience_match: number;
    product_company_match: number;
    behavioral_match: number;
    education_match: number;
  };
  strengths: string[];
  missing_required_skills: string[];
  matched_skills: string[];
  experience_gaps: string[];
  behavioral_risks: string[];
  skill_coverage_pct: number;
};

function AssessmentBadge({ level }: { level: string }) {
  const cfg: Record<string, { bg: string; color: string }> = {
    "Strong Fit": { bg: "#d1fae5", color: "#065f46" },
    "Good Fit": { bg: "#dbeafe", color: "#1e40af" },
    "Partial Fit": { bg: "#fef3c7", color: "#92400e" },
    "Weak Fit": { bg: "#fee2e2", color: "#991b1b" },
  };
  const c = cfg[level] || cfg["Partial Fit"];
  return (
    <span style={{ padding: "3px 10px", borderRadius: 20, fontSize: 12, fontWeight: 600, background: c.bg, color: c.color }}>
      {level}
    </span>
  );
}

function DimBar({ label, value }: { label: string; value: number }) {
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
        <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>{label}</span>
        <span style={{ fontSize: 12, fontWeight: 600 }}>{(value * 100).toFixed(0)}%</span>
      </div>
      <div className="progress-bar" style={{ height: 6 }}>
        <div className="progress-fill" style={{ width: `${value * 100}%`, height: 6, borderRadius: 3 }} />
      </div>
    </div>
  );
}

export default function GapAnalysisPage() {
  const [candidateId, setCandidateId] = useState("CAND_0018499");
  const [gap, setGap] = useState<GapAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function runAnalysis() {
    if (!candidateId.trim()) return;
    setLoading(true);
    setError("");
    setGap(null);
    try {
      const res = await fetch(`/api/gap-analysis/${candidateId}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Not found");
      setGap(data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ display: "flex", minHeight: "100vh", background: "var(--bg)" }}>
      <Sidebar />
      <main style={{ flex: 1, padding: "32px 40px", overflow: "auto" }}>
        <div style={{ marginBottom: 28 }}>
          <h1 style={{ fontSize: 22, fontWeight: 700, letterSpacing: "-0.03em" }}>
            Candidate Gap Analysis
          </h1>
          <p style={{ color: "var(--text-secondary)", marginTop: 4, fontSize: 13 }}>
            Detailed per-candidate gap analysis: match scores, strengths, missing skills, and risks
          </p>
        </div>

        {/* Search */}
        <div className="card" style={{ marginBottom: 24 }}>
          <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
            <input
              id="gap-candidate-input"
              type="text"
              value={candidateId}
              onChange={(e) => setCandidateId(e.target.value)}
              placeholder="Enter Candidate ID (e.g. CAND_0018499)"
              onKeyDown={(e) => e.key === "Enter" && runAnalysis()}
              style={{
                flex: 1, padding: "10px 16px", fontSize: 13, borderRadius: 8,
                border: "1px solid var(--border)", background: "var(--bg)",
                color: "var(--text-primary)", outline: "none",
              }}
            />
            <button
              id="gap-analyze-btn"
              onClick={runAnalysis}
              disabled={loading}
              style={{
                padding: "10px 24px", borderRadius: 8, fontSize: 13, fontWeight: 600,
                background: "var(--accent-dark)", color: "#fff", border: "none",
                cursor: "pointer", opacity: loading ? 0.6 : 1,
              }}
            >
              {loading ? "Analyzing..." : "Analyze"}
            </button>
          </div>
          <p style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 8 }}>
            Must be a candidate from the top-100 ranking. Try CAND_0018499 (rank #1) or CAND_0081846 (rank #2).
          </p>
        </div>

        {error && (
          <div style={{ padding: 16, background: "#fee2e2", borderRadius: 10, color: "#991b1b", fontSize: 13, marginBottom: 20 }}>
            ⚠️ {error}
          </div>
        )}

        {gap && (
          <>
            {/* Summary header */}
            <div className="card" style={{ marginBottom: 20 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <div>
                  <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 4 }}>{gap.candidate_id}</div>
                  <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                    <AssessmentBadge level={gap.overall_assessment} />
                    <span style={{ fontSize: 12, color: "var(--text-muted)" }}>Rank #{gap.rank}</span>
                    <span style={{ fontSize: 12, color: "var(--text-muted)" }}>Score: {(gap.final_score * 100).toFixed(1)}%</span>
                    <span style={{ fontSize: 12, color: "var(--text-muted)" }}>Skill Coverage: {gap.skill_coverage_pct}%</span>
                  </div>
                </div>
                <Link href={`/candidate/${gap.candidate_id}`}
                  style={{ fontSize: 12, color: "var(--accent-dark)", textDecoration: "none" }}>
                  View Full Profile →
                </Link>
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
              {/* Dimension scores */}
              <div className="card">
                <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 16 }}>Match Scores by Dimension</h3>
                <DimBar label="Skill Match" value={gap.dimension_scores.skill_match} />
                <DimBar label="Experience Match" value={gap.dimension_scores.experience_match} />
                <DimBar label="Product Company" value={gap.dimension_scores.product_company_match} />
                <DimBar label="Behavioral / Availability" value={gap.dimension_scores.behavioral_match} />
                <DimBar label="Education" value={gap.dimension_scores.education_match} />
              </div>

              {/* Strengths */}
              <div className="card">
                <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 12, color: "#16a34a" }}>✓ Strengths</h3>
                {gap.strengths.length === 0
                  ? <p style={{ fontSize: 12, color: "var(--text-muted)" }}>No major strengths identified</p>
                  : gap.strengths.map((s, i) => (
                    <div key={i} style={{ fontSize: 12, color: "var(--text-secondary)", padding: "6px 0", borderBottom: "1px solid var(--border)" }}>
                      {s}
                    </div>
                  ))
                }
              </div>

              {/* Missing skills */}
              <div className="card">
                <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 12, color: "#dc2626" }}>⚠ Missing Required Skills</h3>
                {gap.missing_required_skills.length === 0
                  ? <div style={{ fontSize: 12, color: "#16a34a" }}>✓ All required skills matched</div>
                  : (
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                      {gap.missing_required_skills.map((s) => (
                        <span key={s} style={{ padding: "3px 10px", borderRadius: 20, fontSize: 11, background: "#fee2e2", color: "#991b1b" }}>
                          {s}
                        </span>
                      ))}
                    </div>
                  )
                }
                <div style={{ marginTop: 16 }}>
                  <h4 style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, color: "#16a34a" }}>✓ Matched Skills</h4>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                    {gap.matched_skills.map((s) => (
                      <span key={s} style={{ padding: "3px 10px", borderRadius: 20, fontSize: 11, background: "#d1fae5", color: "#065f46" }}>
                        {s}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Risks & Gaps */}
              <div className="card">
                <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 12, color: "#d97706" }}>Experience Gaps</h3>
                {gap.experience_gaps.length === 0
                  ? <div style={{ fontSize: 12, color: "#16a34a" }}>✓ No significant experience gaps</div>
                  : gap.experience_gaps.map((g, i) => (
                    <div key={i} style={{ fontSize: 12, color: "var(--text-secondary)", padding: "6px 0", borderBottom: "1px solid var(--border)" }}>
                      • {g}
                    </div>
                  ))
                }

                <h3 style={{ fontSize: 13, fontWeight: 600, margin: "16px 0 12px", color: "#dc2626" }}>Behavioral Risks</h3>
                {gap.behavioral_risks.length === 0
                  ? <div style={{ fontSize: 12, color: "#16a34a" }}>✓ No behavioral risks detected</div>
                  : gap.behavioral_risks.map((r, i) => (
                    <div key={i} style={{ fontSize: 12, color: "var(--text-secondary)", padding: "6px 0", borderBottom: "1px solid var(--border)" }}>
                      ⚑ {r}
                    </div>
                  ))
                }
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
