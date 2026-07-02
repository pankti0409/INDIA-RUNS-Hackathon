"use client";

import Sidebar from "@/components/Sidebar";
import { useState, useRef } from "react";

type QualityResult = {
  candidate_id: string;
  quality_score: number;
  completeness_score: number;
  platform_completeness: number;
  quality_grade: string;
  present_sections: string[];
  missing_sections: string[];
  weak_areas: string[];
  improvement_suggestions: string[];
  has_github: boolean;
  has_assessments: boolean;
  is_open_to_work: boolean;
  extracted_profile?: {
    name: string;
    current_title: string;
  };
};

function GradeCircle({ score, grade }: { score: number; grade: string }) {
  const color =
    score >= 85 ? "#16a34a" : score >= 70 ? "#2563eb" : score >= 55 ? "#d97706" : "#dc2626";
  const bg =
    score >= 85 ? "#d1fae5" : score >= 70 ? "#dbeafe" : score >= 55 ? "#fef3c7" : "#fee2e2";
  return (
    <div style={{
      width: 120, height: 120, borderRadius: "50%", background: bg,
      display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
      border: `3px solid ${color}`,
    }}>
      <div style={{ fontSize: 28, fontWeight: 800, color }}>{score.toFixed(0)}</div>
      <div style={{ fontSize: 11, fontWeight: 600, color }}>{grade}</div>
    </div>
  );
}

function PriorityIcon({ suggestion }: { suggestion: string }) {
  if (suggestion.startsWith("🔴")) return <span style={{ color: "#dc2626" }}>🔴</span>;
  if (suggestion.startsWith("🟠")) return <span style={{ color: "#ea580c" }}>🟠</span>;
  if (suggestion.startsWith("🟡")) return <span style={{ color: "#d97706" }}>🟡</span>;
  return <span>🟢</span>;
}

export default function ResumeQualityPage() {
  const [mode, setMode] = useState<"id" | "upload">("id");
  const [candidateId, setCandidateId] = useState("CAND_0018499");
  const [result, setResult] = useState<QualityResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  async function analyzeById() {
    setLoading(true); setError(""); setResult(null);
    try {
      const res = await fetch(`/api/resume-quality/${candidateId}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      setResult(data);
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  }

  async function analyzeFile(file: File) {
    setLoading(true); setError(""); setResult(null);
    const form = new FormData();
    form.append("file", file);
    try {
      const res = await fetch("/api/resume-quality/upload", { method: "POST", body: form });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      setResult(data);
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  }

  return (
    <div style={{ display: "flex", minHeight: "100vh", background: "var(--bg)" }}>
      <Sidebar />
      <main style={{ flex: 1, padding: "32px 40px", overflow: "auto" }}>
        <div style={{ marginBottom: 28 }}>
          <h1 style={{ fontSize: 22, fontWeight: 700, letterSpacing: "-0.03em" }}>
            Resume Quality Analysis
          </h1>
          <p style={{ color: "var(--text-secondary)", marginTop: 4, fontSize: 13 }}>
            Quality score, completeness check, weak areas, and prioritized improvement suggestions
          </p>
        </div>

        {/* Mode select */}
        <div style={{ display: "flex", gap: 8, marginBottom: 20 }}>
          {[{ k: "id", label: "By Candidate ID" }, { k: "upload", label: "Upload Resume" }].map((m) => (
            <button key={m.k} onClick={() => setMode(m.k as any)}
              style={{
                padding: "8px 18px", borderRadius: 8, fontSize: 13, fontWeight: 500,
                cursor: "pointer", border: "none",
                background: mode === m.k ? "var(--accent-dark)" : "var(--surface)",
                color: mode === m.k ? "#fff" : "var(--text-primary)",
              }}>
              {m.label}
            </button>
          ))}
        </div>

        <div className="card" style={{ marginBottom: 24 }}>
          {mode === "id" ? (
            <div style={{ display: "flex", gap: 12 }}>
              <input
                id="quality-candidate-id"
                type="text"
                value={candidateId}
                onChange={(e) => setCandidateId(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && analyzeById()}
                placeholder="Enter Candidate ID..."
                style={{
                  flex: 1, padding: "10px 16px", fontSize: 13, borderRadius: 8,
                  border: "1px solid var(--border)", background: "var(--bg)",
                  color: "var(--text-primary)", outline: "none",
                }}
              />
              <button id="quality-analyze-btn" onClick={analyzeById} disabled={loading}
                style={{
                  padding: "10px 24px", borderRadius: 8, fontSize: 13, fontWeight: 600,
                  background: "var(--accent-dark)", color: "#fff", border: "none",
                  cursor: "pointer", opacity: loading ? 0.6 : 1,
                }}>
                {loading ? "Analyzing..." : "Analyze"}
              </button>
            </div>
          ) : (
            <div onClick={() => fileRef.current?.click()}
              style={{
                border: "2px dashed var(--border)", borderRadius: 10, padding: "32px",
                textAlign: "center", cursor: "pointer",
              }}>
              <div style={{ fontSize: 32, marginBottom: 8 }}>📋</div>
              <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 4 }}>Upload resume for quality check</div>
              <div style={{ fontSize: 12, color: "var(--text-muted)" }}>PDF, DOCX, TXT</div>
              {loading && <div style={{ marginTop: 10, fontSize: 13, color: "var(--accent-dark)" }}>Analyzing...</div>}
              <input ref={fileRef} type="file" accept=".pdf,.docx,.txt" style={{ display: "none" }}
                onChange={(e) => { const f = e.target.files?.[0]; if (f) analyzeFile(f); }} />
            </div>
          )}
        </div>

        {error && (
          <div style={{ padding: 16, background: "#fee2e2", borderRadius: 10, color: "#991b1b", fontSize: 13, marginBottom: 20 }}>
            ⚠️ {error}
          </div>
        )}

        {result && (
          <>
            {/* Score summary */}
            <div className="card" style={{ marginBottom: 20 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 32 }}>
                <GradeCircle score={result.quality_score} grade={result.quality_grade} />
                <div style={{ flex: 1 }}>
                  {result.extracted_profile && (
                    <div style={{ fontSize: 15, fontWeight: 700, marginBottom: 4 }}>{result.extracted_profile.name}</div>
                  )}
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12, marginTop: 8 }}>
                    {[
                      { label: "Schema Completeness", val: `${result.completeness_score}%` },
                      { label: "Platform Completeness", val: `${result.platform_completeness}%` },
                      { label: "Sections Present", val: result.present_sections.length },
                    ].map((item) => (
                      <div key={item.label}>
                        <div style={{ fontSize: 18, fontWeight: 700 }}>{item.val}</div>
                        <div style={{ fontSize: 11, color: "var(--text-muted)" }}>{item.label}</div>
                      </div>
                    ))}
                  </div>
                  <div style={{ display: "flex", gap: 12, marginTop: 12 }}>
                    {[
                      { icon: "🐙", label: "GitHub", val: result.has_github },
                      { icon: "📊", label: "Assessments", val: result.has_assessments },
                      { icon: "✋", label: "Open to Work", val: result.is_open_to_work },
                    ].map((item) => (
                      <span key={item.label} style={{ fontSize: 11, padding: "3px 10px", borderRadius: 20,
                        background: item.val ? "#d1fae5" : "#fee2e2", color: item.val ? "#065f46" : "#991b1b" }}>
                        {item.icon} {item.label}: {item.val ? "✓" : "✗"}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
              {/* Improvement suggestions */}
              <div className="card">
                <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 16 }}>Improvement Suggestions</h3>
                {result.improvement_suggestions.length === 0
                  ? <div style={{ fontSize: 12, color: "#16a34a" }}>✓ Profile is excellent!</div>
                  : result.improvement_suggestions.map((s, i) => {
                    const cleanText = s.replace(/^[🔴🟠🟡🟢]\s*(?:HIGH|MEDIUM|LOW):\s*/u, "");
                    return (
                      <div key={i} style={{ padding: "8px 0", borderBottom: "1px solid var(--border)", display: "flex", gap: 8 }}>
                        <PriorityIcon suggestion={s} />
                        <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>{cleanText}</span>
                      </div>
                    );
                  })
                }
              </div>

              {/* Weak areas + missing sections */}
              <div>
                <div className="card" style={{ marginBottom: 16 }}>
                  <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 12, color: "#d97706" }}>Weak Areas</h3>
                  {result.weak_areas.length === 0
                    ? <div style={{ fontSize: 12, color: "#16a34a" }}>✓ No weak areas found</div>
                    : result.weak_areas.map((w, i) => (
                      <div key={i} style={{ fontSize: 12, color: "var(--text-secondary)", padding: "6px 0", borderBottom: "1px solid var(--border)" }}>
                        • {w}
                      </div>
                    ))
                  }
                </div>
                <div className="card">
                  <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 12 }}>Missing Sections</h3>
                  {result.missing_sections.filter(s => s.includes("❌")).map((s, i) => (
                    <div key={i} style={{ fontSize: 12, color: "#dc2626", padding: "4px 0" }}>{s.replace("❌ ", "")}</div>
                  ))}
                  {result.missing_sections.filter(s => s.includes("○")).map((s, i) => (
                    <div key={i} style={{ fontSize: 12, color: "var(--text-muted)", padding: "4px 0" }}>{s.replace("○ ", "")}</div>
                  ))}
                </div>
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
